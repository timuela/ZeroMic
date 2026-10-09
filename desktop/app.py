import asyncio
import io
import json
import logging
import os
import sys
import threading

from PySide6.QtCore import QObject, QSettings, Qt, Signal
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QApplication, QMenu, QMessageBox, QSystemTrayIcon

from desktop.devices import default_output_index, find_output_index, list_output_devices
from desktop.session import DesktopSession
from desktop.ui import MainWindow

log = logging.getLogger(__name__)


def _detect_language():
    tag = ""
    try:
        import locale

        tag = locale.getlocale()[0] or ""
    except Exception:
        tag = ""
    if not tag:
        tag = os.environ.get("LANG") or os.environ.get("LC_ALL") or ""
    return "zh_cn" if str(tag).lower().startswith("zh") else "en_us"


class Translator:
    """Loads the same webui/lang/*.json files the browser UI uses."""

    def __init__(self, webui_dir, language=None):
        self._dir = webui_dir
        self.lang = language or _detect_language()
        self._data = {}
        self.load(self.lang)

    def load(self, language):
        self.lang = language
        self._data = {}
        try:
            path = os.path.join(self._dir, "lang", f"{language}.json")
            with open(path, "r", encoding="utf-8") as handle:
                self._data = json.load(handle)
        except Exception:
            log.debug("could not load language file for %s", language)

    def __call__(self, key, fallback=""):
        return self._data.get(key, fallback)


def _style_path():
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(here, "style.qss"),
        os.path.join(getattr(sys, "_MEIPASS", ""), "desktop", "style.qss"),
    ]
    for path in candidates:
        if path and os.path.exists(path):
            return path
    return None


def _make_qr_png(url):
    try:
        import segno

        buffer = io.BytesIO()
        segno.make(url, error="h").save(buffer, kind="png", scale=4, border=2)
        return buffer.getvalue()
    except Exception as exc:
        log.debug("QR generation failed: %s", exc)
        return None


class Feedback(QObject):
    """Thread-safe bridge: emitted from the asyncio thread, delivered on the UI thread."""

    presenceChanged = Signal(bool)
    linkStateChanged = Signal(str)
    rtcStateChanged = Signal(str)
    mutedChanged = Signal(bool)
    errorRaised = Signal(str)
    driverStateChanged = Signal(bool)
    driverFinished = Signal(bool, str)
    uninstallFinished = Signal(bool, str)

    def set_presence(self, connected):
        self.presenceChanged.emit(bool(connected))

    def set_link_state(self, state):
        self.linkStateChanged.emit(str(state))

    def set_rtc_state(self, state):
        self.rtcStateChanged.emit(str(state))

    def set_muted(self, muted):
        self.mutedChanged.emit(bool(muted))

    def report_error(self, message):
        self.errorRaised.emit(str(message))


class AsyncRunner:
    """Runs the asyncio event loop (signalling + WebRTC) on a background thread."""

    def __init__(self):
        self.loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run, name="zeromic-async", daemon=True)
        self._thread.start()

    def _run(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def schedule(self, coro):
        return asyncio.run_coroutine_threadsafe(coro, self.loop)

    def stop(self):
        try:
            self.loop.call_soon_threadsafe(self.loop.stop)
        except Exception:
            pass


def _settings_path():
    """Keep settings next to the executable so the build stays portable."""
    if getattr(sys, "frozen", False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "zeromic-host.ini")


class DesktopApp:
    def __init__(self, qapp, platform, version, webui_dir, icon_path, server):
        self._qapp = qapp
        self._platform = platform
        self._version = version
        self._server = server
        self._settings = QSettings(_settings_path(), QSettings.IniFormat)
        self._translator = Translator(webui_dir)
        self._t = self._translator

        self._runner = AsyncRunner()
        self._feedback = Feedback()
        self._session = DesktopSession(self._feedback, platform)
        self._session.set_scheduler(self._runner.schedule)

        self._current_device = None
        self._hint_shown = False
        self._muted = False
        self._active = False

        self._window = MainWindow(self._t, version, self._translator.lang)
        self._window.set_level_provider(self._session.level)
        self._window.set_gain(1.0)
        self._window.on_hidden = self._on_window_hidden

        self._connect_signals()
        self._tray = self._build_tray(icon_path)

    # ------------------------------------------------------------------
    # wiring
    # ------------------------------------------------------------------
    def _connect_signals(self):
        self._window.connectRequested.connect(self._on_connect)
        self._window.disconnectRequested.connect(self._on_disconnect)
        self._window.muteToggled.connect(lambda: self._session.toggle_mute(broadcast=False))
        self._window.gainChanged.connect(self._session.set_gain)
        self._window.deviceChanged.connect(self._on_device_changed)
        self._window.uninstallDriverRequested.connect(self._on_uninstall_driver)
        self._window.aboutRequested.connect(self._on_about)
        self._window.languageToggled.connect(self._on_language_toggled)
        self._window.addressSelected.connect(self._on_address_selected)
        self._window.portChangeRequested.connect(self._on_port_requested)

        self._feedback.presenceChanged.connect(self._window.set_presence)
        self._feedback.linkStateChanged.connect(self._window.set_link_state)
        self._feedback.rtcStateChanged.connect(self._window.set_rtc_state)
        self._feedback.mutedChanged.connect(self._on_muted_changed)
        self._feedback.errorRaised.connect(self._on_error)
        self._feedback.driverStateChanged.connect(self._window.set_driver_installed)
        self._feedback.driverFinished.connect(self._on_driver_finished)
        self._feedback.uninstallFinished.connect(self._on_uninstall_finished)

    def _build_tray(self, icon_path):
        tray = QSystemTrayIcon(QIcon(icon_path) if icon_path else QIcon(), self._window)

        menu = QMenu()
        self._show_action = QAction(self._t("tray_show", "Show Window"), menu)
        self._show_action.triggered.connect(self._show_window)
        menu.addAction(self._show_action)

        self._mute_action = QAction(self._t("tray_mute", "Mute"), menu)
        self._mute_action.triggered.connect(lambda: self._session.toggle_mute(broadcast=True))
        menu.addAction(self._mute_action)

        menu.addSeparator()
        self._quit_action = QAction(self._t("tray_exit", "Quit"), menu)
        self._quit_action.triggered.connect(self._quit)
        menu.addAction(self._quit_action)

        tray.setContextMenu(menu)
        tray.setToolTip("ZeroMic")
        tray.activated.connect(self._on_tray_activated)
        tray.show()
        return tray

    # ------------------------------------------------------------------
    # startup
    # ------------------------------------------------------------------
    def start(self):
        self._window.show()
        self._apply_saved_port()
        self._refresh_addresses()
        self._refresh_devices()
        # Addresses are only known now, and they set how wide the window needs
        # to be, so size it once here rather than at construction.
        self._window.fit_to_content()
        threading.Thread(target=self._check_driver, daemon=True).start()

    def _apply_saved_port(self):
        saved = self._settings.value("port")
        if saved is None:
            return
        try:
            saved = int(saved)
        except (TypeError, ValueError):
            return
        if saved == self._server.port or not 1024 <= saved <= 65535:
            return
        ok, _ = self._server.restart(saved)
        if not ok:
            QMessageBox.information(
                self._window,
                "ZeroMic",
                self._t("host_port_failed", "Could not use the saved port"),
            )

    def _session_url(self):
        return f"https://127.0.0.1:{self._server.port}"

    def _refresh_addresses(self):
        port = self._server.port
        self._window.set_port(port)
        addresses = [f"https://{ip}:{port}" for ip in self._server.ips()]
        self._window.set_addresses(addresses)

    def _on_address_selected(self, url):
        self._window.set_selected_address(url)
        png = _make_qr_png(url)
        if png:
            self._window.set_qr(png)

    def _on_port_requested(self, port):
        if port == self._server.port:
            return

        if self._active:
            self._runner.schedule(self._session.stop())

        ok, message = self._server.restart(port)
        if not ok:
            QMessageBox.warning(
                self._window,
                "ZeroMic",
                f"{self._t('host_port_failed', 'Could not use that port')}\n{message}",
            )
            self._window.set_port(self._server.port)
        else:
            self._settings.setValue("port", port)
            self._settings.sync()
            self._refresh_addresses()

        if self._active:
            self._runner.schedule(
                self._session.start(self._session_url(), self._current_device)
            )

    def _refresh_devices(self):
        devices = list_output_devices()
        current = find_output_index(self._platform.driver_match_keyword, devices)
        if current is None:
            current = default_output_index()
        self._current_device = current
        self._window.set_devices(devices, current)

    def _check_driver(self):
        try:
            installed = bool(self._platform.is_driver_installed())
        except Exception:
            installed = False

        self._feedback.driverStateChanged.emit(installed)
        if installed:
            return

        try:
            success, message = self._platform.install_driver()
        except Exception as exc:
            success, message = False, str(exc)
        self._feedback.driverFinished.emit(success, message)

    # ------------------------------------------------------------------
    # actions
    # ------------------------------------------------------------------
    def _on_connect(self):
        self._window.set_rtc_state("new")
        self._window.set_active(True)
        self._active = True
        self._runner.schedule(
            self._session.start(self._session_url(), self._current_device)
        )

    def _on_disconnect(self):
        self._active = False
        self._window.set_active(False)
        self._window.set_presence(False)
        self._window.set_rtc_state("new")
        self._runner.schedule(self._session.stop())

    def _on_device_changed(self, index):
        self._current_device = index
        self._session.select_device(index)

    def _on_muted_changed(self, muted):
        self._muted = muted
        self._window.set_muted(muted)
        self._refresh_tray_texts()

    def _refresh_tray_texts(self):
        self._show_action.setText(self._t("tray_show", "Show Window"))
        self._mute_action.setText(
            self._t("tray_unmute", "Unmute") if self._muted else self._t("tray_mute", "Mute")
        )
        self._quit_action.setText(self._t("tray_exit", "Quit"))

    def _on_language_toggled(self):
        next_lang = "en_us" if self._translator.lang == "zh_cn" else "zh_cn"
        self._translator.load(next_lang)
        self._window.set_language(next_lang)
        self._refresh_tray_texts()

    def _on_error(self, message):
        QMessageBox.warning(self._window, "ZeroMic", message)

    def _on_driver_finished(self, success, message):
        if success:
            self._feedback.driverStateChanged.emit(True)
            warning = self._platform.get_post_install_warning()
            if warning:
                QMessageBox.information(
                    self._window, self._t("reminder_title", "配置完成"), warning
                )
        else:
            QMessageBox.warning(
                self._window, self._t("install_title_fail", "安装失败"), message or ""
            )

    def _on_uninstall_driver(self):
        answer = QMessageBox.question(
            self._window,
            self._t("dialog_uninstall_title", "确定要卸载驱动吗？"),
            self._t("uninstall_dialog_text", ""),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        threading.Thread(target=self._uninstall_worker, daemon=True).start()

    def _uninstall_worker(self):
        try:
            success, message = self._platform.uninstall_driver()
        except Exception as exc:
            success, message = False, str(exc)
        self._feedback.uninstallFinished.emit(success, message)

    def _on_uninstall_finished(self, success, message):
        if success:
            self._feedback.driverStateChanged.emit(False)
            QMessageBox.information(
                self._window,
                self._t("uninstall_title_success", "卸载成功"),
                self._t("uninstall_desc_success", ""),
            )
            self._quit()
        else:
            QMessageBox.warning(
                self._window, self._t("uninstall_title_fail", "卸载失败"), message or ""
            )

    def _on_about(self):
        QMessageBox.about(
            self._window,
            "ZeroMic",
            f"ZeroMic Desktop {self._version}\n\n"
            "WebRTC over LAN - no cloud, no account.",
        )

    # ------------------------------------------------------------------
    # tray / window
    # ------------------------------------------------------------------
    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            self._show_window()

    def _show_window(self):
        self._window.show()
        self._window.raise_()
        self._window.activateWindow()

    def _on_window_hidden(self):
        if not self._hint_shown:
            self._hint_shown = True
            self._tray.showMessage(
                "ZeroMic", self._t("tray_hint", "ZeroMic is still running in the tray")
            )

    def _quit(self):
        self._window.allow_close = True
        try:
            self._runner.schedule(self._session.stop())
        except Exception:
            pass
        self._runner.stop()
        self._tray.hide()
        self._qapp.quit()


def run_desktop(platform, version, webui_dir, icon_path=None, server=None):
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    app.setApplicationName("ZeroMic")
    app.setQuitOnLastWindowClosed(False)

    # Without an explicit AppUserModelID Windows groups the window under the
    # bootloader process and shows a generic taskbar icon.
    if sys.platform == "win32":
        try:
            import ctypes

            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("ZeroMic.Host")
        except Exception:
            pass

    if icon_path:
        icon = QIcon(icon_path)
        if not icon.isNull():
            app.setWindowIcon(icon)

    style = _style_path()
    if style:
        try:
            with open(style, "r", encoding="utf-8") as handle:
                app.setStyleSheet(handle.read())
        except Exception:
            log.debug("could not load stylesheet")

    controller = DesktopApp(
        app, platform, version, webui_dir, icon_path, server
    )
    controller.start()
    return app.exec()
