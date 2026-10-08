from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

DOT_IDLE = "#888888"
DOT_OK = "#4CAF50"
DOT_WARN = "#FF9800"
DOT_ERROR = "#FF5252"

MIC_IDLE_BG = "#2a2a2a"
MIC_IDLE_FG = "#8a8a8a"
MIC_ON_BG = "#4285F4"
MIC_ON_FG = "#ffffff"
MIC_MUTED_BG = "#FFB3AE"
MIC_MUTED_FG = "#4a0005"


class MainWindow(QMainWindow):
    connectRequested = Signal()
    disconnectRequested = Signal()
    muteToggled = Signal()
    gainChanged = Signal(float)
    deviceChanged = Signal(int)
    installDriverRequested = Signal()
    uninstallDriverRequested = Signal()
    aboutRequested = Signal()
    languageToggled = Signal()
    installReminderAcknowledged = Signal()

    def __init__(self, t, version, language="en_us"):
        super().__init__()
        self._t = t
        self._version = version
        self._language = language
        self._link_up = False
        self._presence = False
        self._rtc_state = "new"
        self._muted = False
        self._active = False
        self._level_provider = None
        self._build()

        self._level_timer = QTimer(self)
        self._level_timer.setInterval(40)
        self._level_timer.timeout.connect(self._tick_level)
        self._level_timer.start()

    # ------------------------------------------------------------------
    # construction
    # ------------------------------------------------------------------
    def _build(self):
        self.setWindowTitle("ZeroMic Desktop")
        self.resize(420, 800)

        central = QWidget()
        central.setObjectName("centralWidget")
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(16)

        header = QHBoxLayout()
        title = QLabel("\U0001F399  ZeroMic")
        title.setObjectName("headerTitle")
        header.addWidget(title)

        self._version_label = QLabel(self._version)
        self._version_label.setObjectName("versionLabel")
        header.addWidget(self._version_label)
        header.addStretch(1)

        self._lang_button = QPushButton("")
        self._lang_button.setObjectName("flatButton")
        self._lang_button.setFixedWidth(44)
        self._lang_button.clicked.connect(lambda: self.languageToggled.emit())
        header.addWidget(self._lang_button)

        self._about_button = QPushButton(self._t("header_about", "About"))
        self._about_button.setObjectName("flatButton")
        self._about_button.clicked.connect(lambda: self.aboutRequested.emit())
        header.addWidget(self._about_button)

        self._uninstall_button = QPushButton(self._t("header_uninstall", "Uninstall Driver"))
        self._uninstall_button.setObjectName("flatButton")
        self._uninstall_button.clicked.connect(lambda: self.uninstallDriverRequested.emit())
        self._uninstall_button.setVisible(False)
        header.addWidget(self._uninstall_button)

        root.addLayout(header)

        # ---- status card ------------------------------------------------
        card = QFrame()
        card.setObjectName("card")
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(20, 14, 20, 14)

        status_box = QVBoxLayout()
        status_box.setSpacing(6)
        self._status_title = QLabel(self._t("status_label", "Mobile Connection"))
        self._status_title.setObjectName("statusTitle")
        status_box.addWidget(self._status_title)

        status_row = QHBoxLayout()
        status_row.setSpacing(8)
        self._dot = QLabel()
        self._dot.setFixedSize(10, 10)
        status_row.addWidget(self._dot)
        self._status_text = QLabel("")
        self._status_text.setObjectName("statusText")
        status_row.addWidget(self._status_text)
        status_row.addStretch(1)
        status_box.addLayout(status_row)

        card_layout.addLayout(status_box)
        card_layout.addStretch(1)
        root.addWidget(card)

        # ---- tutorial (shown while no phone is connected) ---------------
        self._tutorial_card = QFrame()
        self._tutorial_card.setObjectName("tutorialCard")
        tutorial = QVBoxLayout(self._tutorial_card)
        tutorial.setContentsMargins(20, 20, 20, 20)
        tutorial.setSpacing(10)

        self._qr_label = QLabel()
        self._qr_label.setAlignment(Qt.AlignCenter)
        tutorial.addWidget(self._qr_label)

        self._tutorial_title = QLabel(self._t("tutorial_title", "Waiting for Mobile"))
        self._tutorial_title.setAlignment(Qt.AlignCenter)
        tutorial.addWidget(self._tutorial_title)

        self._url_label = QLabel("...")
        self._url_label.setObjectName("urlLabel")
        self._url_label.setAlignment(Qt.AlignCenter)
        self._url_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        tutorial.addWidget(self._url_label)

        self._tutorial_warn = QLabel(self._t("tutorial_warn", "The \u201cNot Secure\u201d warning is normal."))
        self._tutorial_warn.setObjectName("warnLabel")
        self._tutorial_warn.setAlignment(Qt.AlignCenter)
        self._tutorial_warn.setWordWrap(True)
        tutorial.addWidget(self._tutorial_warn)

        root.addWidget(self._tutorial_card)

        # ---- control area ----------------------------------------------
        self._control_area = QWidget()
        control = QVBoxLayout(self._control_area)
        control.setContentsMargins(0, 0, 0, 0)
        control.setSpacing(16)

        self._device_combo = QComboBox()
        self._device_combo.currentIndexChanged.connect(self._on_device_index_changed)
        control.addWidget(self._device_combo)

        gain_row = QHBoxLayout()
        self._gain_label = QLabel(self._t("desktop_gain", "Volume"))
        gain_row.addWidget(self._gain_label)
        gain_row.addStretch(1)
        self._gain_value_label = QLabel("1.0x")
        self._gain_value_label.setObjectName("gainValue")
        gain_row.addWidget(self._gain_value_label)
        control.addLayout(gain_row)

        self._gain_slider = QSlider(Qt.Horizontal)
        self._gain_slider.setRange(0, 30)
        self._gain_slider.setValue(10)
        self._gain_slider.valueChanged.connect(self._on_gain_slider)
        control.addWidget(self._gain_slider)

        mic_row = QHBoxLayout()
        mic_row.addStretch(1)
        self._mic_button = QPushButton("\U0001F3A4")
        self._mic_button.setObjectName("micButton")
        self._mic_button.setFixedSize(140, 140)
        self._mic_button.setCursor(Qt.PointingHandCursor)
        self._mic_button.clicked.connect(lambda: self.muteToggled.emit())
        mic_row.addWidget(self._mic_button)
        mic_row.addStretch(1)
        control.addLayout(mic_row)

        root.addWidget(self._control_area)
        self._control_area.setVisible(False)

        root.addStretch(1)

        self._connect_button = QPushButton("")
        self._connect_button.setObjectName("primaryButton")
        self._connect_button.clicked.connect(self._on_connect_clicked)
        root.addWidget(self._connect_button)

        self.set_language(self._language)
        self._apply_mic_style()

    # ------------------------------------------------------------------
    # slots
    # ------------------------------------------------------------------
    def _on_connect_clicked(self):
        if self._active:
            self.disconnectRequested.emit()
        else:
            self.connectRequested.emit()

    def _on_gain_slider(self, raw):
        gain = raw / 10.0
        self._gain_value_label.setText(f"{gain:.1f}x")
        self.gainChanged.emit(gain)

    def _on_device_index_changed(self, index):
        if index < 0:
            return
        device = self._device_combo.itemData(index)
        if device is not None:
            self.deviceChanged.emit(int(device))

    def _tick_level(self):
        if self._level_provider is None or not self._presence:
            return
        try:
            level = float(self._level_provider())
        except Exception:
            return
        size = int(140 + min(max(level, 0.0) * 6.0, 1.0) * 46)
        self._mic_button.setFixedSize(size, size)
        self._apply_mic_style(size)

    # ------------------------------------------------------------------
    # language
    # ------------------------------------------------------------------
    def set_language(self, language):
        self._language = language
        # Show the language you would switch to, like the web UI does.
        self._lang_button.setText("EN" if language == "zh_cn" else "\u4e2d")
        self.retranslate()

    def retranslate(self):
        self._about_button.setText(self._t("header_about", "About"))
        self._uninstall_button.setText(self._t("header_uninstall", "Uninstall Driver"))
        self._status_title.setText(self._t("status_label", "Mobile Connection"))
        self._gain_label.setText(self._t("desktop_gain", "Volume"))
        self._tutorial_title.setText(self._t("tutorial_title", "Waiting for Mobile"))
        self._tutorial_warn.setText(
            self._t("tutorial_warn", "The \u201cNot Secure\u201d warning is normal.")
        )
        self.set_active(self._active)
        self._refresh_status()

    # ------------------------------------------------------------------
    # updates coming from the session
    # ------------------------------------------------------------------
    def set_level_provider(self, provider):
        self._level_provider = provider

    def set_devices(self, devices, current_index=None):
        self._device_combo.blockSignals(True)
        self._device_combo.clear()
        for index, name in devices:
            self._device_combo.addItem(name, index)
        if current_index is not None:
            position = self._device_combo.findData(current_index)
            if position >= 0:
                self._device_combo.setCurrentIndex(position)
        self._device_combo.blockSignals(False)

    def set_gain(self, gain):
        self._gain_slider.blockSignals(True)
        self._gain_slider.setValue(int(round(gain * 10)))
        self._gain_value_label.setText(f"{gain:.1f}x")
        self._gain_slider.blockSignals(False)

    def set_url(self, url):
        self._url_label.setText(url)

    def set_qr(self, png_bytes):
        pixmap = QPixmap()
        if pixmap.loadFromData(png_bytes, "PNG"):
            self._qr_label.setPixmap(pixmap)
            self._qr_label.setVisible(True)

    def set_active(self, active):
        self._active = active
        self._connect_button.setText(
            self._t("desktop_disconnect", "Disconnect")
            if active
            else self._t("desktop_connect", "Connect")
        )
        self._connect_button.setObjectName("dangerButton" if active else "primaryButton")
        self._connect_button.style().unpolish(self._connect_button)
        self._connect_button.style().polish(self._connect_button)

    def set_driver_installed(self, installed):
        self._uninstall_button.setVisible(installed)

    def set_link_state(self, state):
        self._link_up = state == "connected"
        self._refresh_status()

    def set_presence(self, connected):
        self._presence = connected
        self._tutorial_card.setVisible(not connected)
        self._control_area.setVisible(connected)
        if not connected:
            self._mic_button.setFixedSize(140, 140)
            self._apply_mic_style(140)
        self._refresh_status()

    def set_rtc_state(self, state):
        self._rtc_state = state or "new"
        self._refresh_status()

    def set_muted(self, muted):
        self._muted = muted
        self._mic_button.setText("\U0001F507" if muted else "\U0001F3A4")
        self._apply_mic_style()
        self._refresh_status()

    def _refresh_status(self):
        if not self._link_up:
            color, text = DOT_IDLE, self._t("status_offline", "Not connected to service")
        elif not self._presence:
            color, text = DOT_IDLE, self._t("status_wait", "Waiting for device...")
        elif self._rtc_state in ("connected", "completed"):
            if self._muted:
                color, text = DOT_WARN, self._t("state_muted", "Desktop Muted")
            else:
                color, text = DOT_OK, self._t("status_connected", "Mobile Connected")
        elif self._rtc_state in ("failed", "closed"):
            color, text = DOT_ERROR, self._t("status_error", "Connection Failed")
        else:
            color, text = DOT_WARN, self._t("status_connecting", "Connecting...")

        self._dot.setStyleSheet(f"background-color: {color}; border-radius: 5px;")
        self._status_text.setText(text)
        self._status_text.setStyleSheet(f"color: {color};")

    def _apply_mic_style(self, size=None):
        if size is None:
            size = self._mic_button.width()
        radius = size // 2

        if self._muted:
            bg, fg = MIC_MUTED_BG, MIC_MUTED_FG
        elif self._presence:
            bg, fg = MIC_ON_BG, MIC_ON_FG
        else:
            bg, fg = MIC_IDLE_BG, MIC_IDLE_FG

        self._mic_button.setStyleSheet(
            f"background-color: {bg}; color: {fg}; border: none; border-radius: {radius}px;"
        )

    def closeEvent(self, event):
        if getattr(self, "allow_close", False):
            event.accept()
            return
        event.ignore()
        self.hide()
        on_hidden = getattr(self, "on_hidden", None)
        if on_hidden is not None:
            on_hidden()
