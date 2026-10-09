import math
import os
import sys

from PySide6.QtCore import (
    QEasingCurve,
    QPointF,
    QPropertyAnimation,
    QRect,
    QSize,
    Qt,
    QTimer,
    Signal,
)
from PySide6.QtGui import QColor, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

DOT_IDLE = "#888888"
DOT_OK = "#4CAF50"
DOT_WARN = "#FF9800"
DOT_ERROR = "#FF5252"

ICON_FILE_OFF = "icon-volume-off.png"
ICON_FILE_UP = "icon-volume-up.png"

BUTTON_DIAMETER = 124
BUTTON_WIDGET_SIZE = 216
RING_MAX_SCALE = 1.55
ICON_PIXEL_SIZE = 46

BUTTON_IDLE_BG = QColor(0x2A, 0x2A, 0x2A)
BUTTON_IDLE_FG = QColor(0x8A, 0x8A, 0x8A)
BUTTON_ACTIVE_BG = QColor(0x42, 0x85, 0xF4)
BUTTON_ACTIVE_FG = QColor(0xFF, 0xFF, 0xFF)
BUTTON_MUTED_BG = QColor(0xFF, 0xB3, 0xAE)
BUTTON_MUTED_FG = QColor(0x4A, 0x00, 0x05)

SETTINGS_PANEL_WIDTH = 300

_pixmap_cache = {}
_tinted_cache = {}


def _load_pixmap(filename):
    if filename in _pixmap_cache:
        return _pixmap_cache[filename]

    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(here, filename),
        os.path.join(getattr(sys, "_MEIPASS", ""), "desktop", filename),
    ]

    pixmap = None
    for path in candidates:
        if path and os.path.exists(path):
            candidate = QPixmap(path)
            if not candidate.isNull():
                pixmap = candidate
                break

    _pixmap_cache[filename] = pixmap
    return pixmap


def _tinted_pixmap(filename, color):
    """Recolour a white glyph on a transparent background by keeping its alpha."""
    key = (filename, color.rgba())
    if key in _tinted_cache:
        return _tinted_cache[key]

    source = _load_pixmap(filename)
    tinted = None
    if source is not None:
        tinted = QPixmap(source.size())
        tinted.fill(Qt.transparent)
        painter = QPainter(tinted)
        painter.drawPixmap(0, 0, source)
        painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
        painter.fillRect(tinted.rect(), color)
        painter.end()

    _tinted_cache[key] = tinted
    return tinted


def _normalise_level(rms):
    """Map a linear RMS value onto 0..1 using a dB curve, so it does not saturate."""
    if rms <= 0.0:
        return 0.0
    db = 20.0 * math.log10(rms)
    return max(0.0, min(1.0, (db + 54.0) / 44.0))


class _Scrim(QWidget):
    """Semi-transparent overlay that closes the settings panel when clicked."""

    clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background: rgba(0, 0, 0, 150);")

    def mousePressEvent(self, event):
        self.clicked.emit()


class MicButton(QWidget):
    """Round toggle that mirrors the web UI's speaker button."""

    clicked = Signal()

    def __init__(self, level_provider=None, parent=None):
        super().__init__(parent)
        self.setFixedSize(BUTTON_WIDGET_SIZE, BUTTON_WIDGET_SIZE)
        self.setCursor(Qt.PointingHandCursor)

        self._level_provider = level_provider
        self._state = "idle"
        self._display = 0.0

        self._timer = QTimer(self)
        self._timer.setInterval(16)  # ~60 fps, like requestAnimationFrame
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    def set_state(self, state):
        if state != self._state:
            self._state = state
            if state != "active":
                self._display = 0.0
            self.update()

    def set_level_provider(self, provider):
        self._level_provider = provider

    def _tick(self):
        if self._state != "active" and self._display <= 0.002:
            return

        target = 0.0
        if self._state == "active" and self._level_provider is not None:
            try:
                target = _normalise_level(float(self._level_provider()))
            except Exception:
                target = 0.0

        # Fast attack, slow release: glides instead of snapping to full size.
        rate = 0.26 if target > self._display else 0.06
        self._display += (target - self._display) * rate
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.TextAntialiasing, True)

        if self._state == "muted":
            button_bg, icon_fg, icon_file = BUTTON_MUTED_BG, BUTTON_MUTED_FG, ICON_FILE_OFF
        elif self._state == "active":
            button_bg, icon_fg, icon_file = BUTTON_ACTIVE_BG, BUTTON_ACTIVE_FG, ICON_FILE_UP
        else:
            button_bg, icon_fg, icon_file = BUTTON_IDLE_BG, BUTTON_IDLE_FG, ICON_FILE_OFF

        centre = QPointF(self.width() / 2.0, self.height() / 2.0)
        button_radius = BUTTON_DIAMETER / 2.0

        # Ring first, so it sits behind the button and grows evenly outwards.
        if self._display > 0.002:
            ring = QColor(button_bg)
            ring.setAlphaF(min(0.30, 0.08 + self._display * 0.24))
            ring_radius = button_radius * (1.0 + self._display * (RING_MAX_SCALE - 1.0))
            painter.setPen(Qt.NoPen)
            painter.setBrush(ring)
            painter.drawEllipse(centre, ring_radius, ring_radius)

        painter.setPen(Qt.NoPen)
        painter.setBrush(button_bg)
        painter.drawEllipse(centre, button_radius, button_radius)

        pixmap = _tinted_pixmap(icon_file, icon_fg)
        if pixmap is not None:
            ratio = self.devicePixelRatioF() or 1.0
            target = QSize(int(ICON_PIXEL_SIZE * ratio), int(ICON_PIXEL_SIZE * ratio))
            scaled = pixmap.scaled(target, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            scaled.setDevicePixelRatio(ratio)
            width = scaled.width() / ratio
            height = scaled.height() / ratio
            painter.drawPixmap(
                QPointF(centre.x() - width / 2.0, centre.y() - height / 2.0), scaled
            )


class MainWindow(QMainWindow):
    connectRequested = Signal()
    disconnectRequested = Signal()
    muteToggled = Signal()
    gainChanged = Signal(float)
    deviceChanged = Signal(int)
    installDriverRequested = Signal()
    uninstallDriverRequested = Signal()
    aboutRequested = Signal()
    languageChanged = Signal(str)
    requirePinChanged = Signal(bool)
    regeneratePinRequested = Signal()
    installReminderAcknowledged = Signal()
    addressSelected = Signal(str)
    portChangeRequested = Signal(int)

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
        self._settings_open = False
        self._pin = ""
        self._pin_required = True
        self._build()

    # ------------------------------------------------------------------
    # construction
    # ------------------------------------------------------------------
    def _build(self):
        self.setWindowTitle("ZeroMic Desktop")
        self.resize(520, 820)
        self.setWindowIcon(QApplication.windowIcon())

        content = QWidget()
        content.setObjectName("centralWidget")
        root = QVBoxLayout(content)
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

        self._settings_button = QPushButton("\u2630")
        self._settings_button.setObjectName("flatButton")
        self._settings_button.setFixedWidth(44)
        self._settings_button.setToolTip(self._t("settings_title", "Settings"))
        self._settings_button.clicked.connect(
            lambda: self._set_settings_open(not self._settings_open)
        )
        header.addWidget(self._settings_button)

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
        # Grows with the status wording otherwise, which also pushed the
        # window wider than its default size.
        self._status_text.setWordWrap(True)
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

        # one button per network address, so a PC with several interfaces
        # (Wi-Fi, Ethernet, Tailscale, ...) can be reached on any of them
        self._address_box = QVBoxLayout()
        self._address_box.setSpacing(4)
        self._address_buttons = []
        self._copy_buttons = []
        self._selected_address = None
        tutorial.addLayout(self._address_box)

        self._tutorial_pin = QLabel("")
        self._tutorial_pin.setAlignment(Qt.AlignCenter)
        self._tutorial_pin.setStyleSheet(
            "font-family: monospace; font-size: 18px; font-weight: bold;"
            " color: #4285F4;"
        )
        self._tutorial_pin.setVisible(False)
        tutorial.addWidget(self._tutorial_pin)

        port_row = QHBoxLayout()
        self._port_label = QLabel(self._t("host_port", "Port"))
        port_row.addWidget(self._port_label)

        self._port_input = QSpinBox()
        self._port_input.setRange(1024, 65535)
        self._port_input.setValue(5000)
        port_row.addWidget(self._port_input)

        self._apply_port_button = QPushButton(self._t("host_apply", "Apply"))
        self._apply_port_button.setObjectName("flatButton")
        self._apply_port_button.clicked.connect(self._on_apply_port)
        port_row.addWidget(self._apply_port_button)
        port_row.addStretch(1)
        tutorial.addLayout(port_row)

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
        # Without this the combo demands room for the longest device name it
        # is given - "CABLE Input (VB-Audio Virtual Cable)" alone forced the
        # whole window wider than its default size.
        self._device_combo.setSizeAdjustPolicy(
            QComboBox.AdjustToMinimumContentsLengthWithIcon
        )
        self._device_combo.setMinimumContentsLength(16)
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
        self._mic_button = MicButton()
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

        # Everything lives in a scroll area so the layout minimum stays small.
        # Otherwise showing the address list or the microphone pad raises the
        # window's minimum height and Qt forces the window taller than the
        # user sized it, every time the connection state changes.
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { border: none; background: #121212; }")
        scroll.setWidget(content)

        # The settings panel and its scrim are children of the container but
        # stay out of the layout, so they sit above the scroll area as an
        # overlay that slides in from the right edge.
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.addWidget(scroll)
        self._container = container

        self._scrim = _Scrim(container)
        self._scrim.clicked.connect(lambda: self._set_settings_open(False))
        self._scrim.hide()

        self._settings_panel = self._build_settings_panel(container)
        self._settings_panel.hide()

        self._settings_anim = QPropertyAnimation(self._settings_panel, b"geometry", self)
        self._settings_anim.setDuration(220)
        self._settings_anim.setEasingCurve(QEasingCurve.OutCubic)
        self._settings_anim.finished.connect(self._on_settings_anim_finished)

        self.setCentralWidget(container)
        self._layout_settings()

        self.setMinimumSize(360, 420)
        self.set_language(self._language)

    # ------------------------------------------------------------------
    # settings sidebar
    # ------------------------------------------------------------------
    def _build_settings_panel(self, parent):
        panel = QFrame(parent)
        panel.setObjectName("settingsPanel")
        panel.setStyleSheet(
            "QFrame#settingsPanel { background: #1a1a1a;"
            " border-left: 1px solid #2a2a2a; }"
        )
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 16, 20, 20)
        layout.setSpacing(14)

        head = QHBoxLayout()
        self._settings_title = QLabel(self._t("settings_title", "Settings"))
        self._settings_title.setObjectName("headerTitle")
        head.addWidget(self._settings_title)
        head.addStretch(1)
        close_button = QPushButton("\u2715")
        close_button.setObjectName("flatButton")
        close_button.setFixedWidth(40)
        close_button.clicked.connect(lambda: self._set_settings_open(False))
        head.addWidget(close_button)
        layout.addLayout(head)

        self._settings_lang_label = QLabel(self._t("settings_language", "Language"))
        self._settings_lang_label.setObjectName("statusTitle")
        layout.addWidget(self._settings_lang_label)

        self._language_combo = QComboBox()
        for code, key, fallback in (
            ("en_us", "lang_en", "English"),
            ("zh_cn", "lang_zh", "\u4e2d\u6587"),
            ("vi_vn", "lang_vi", "Ti\u1ebfng Vi\u1ec7t"),
        ):
            self._language_combo.addItem(self._t(key, fallback), code)
        self._language_combo.currentIndexChanged.connect(
            self._on_language_index_changed
        )
        layout.addWidget(self._language_combo)

        self._require_pin_check = QCheckBox(
            self._t("settings_require_pin", "Require PIN")
        )
        self._require_pin_check.toggled.connect(self.requirePinChanged.emit)
        layout.addWidget(self._require_pin_check)

        pin_row = QHBoxLayout()
        self._settings_pin_value = QLabel("------")
        self._settings_pin_value.setStyleSheet(
            "font-family: monospace; font-size: 20px; font-weight: bold;"
            " color: #4285F4;"
        )
        pin_row.addWidget(self._settings_pin_value)
        pin_row.addStretch(1)
        self._new_pin_button = QPushButton(self._t("settings_new_pin", "New PIN"))
        self._new_pin_button.setObjectName("flatButton")
        self._new_pin_button.clicked.connect(
            lambda: self.regeneratePinRequested.emit()
        )
        pin_row.addWidget(self._new_pin_button)
        layout.addLayout(pin_row)

        self._settings_more_label = QLabel(self._t("settings_more", "More"))
        self._settings_more_label.setObjectName("statusTitle")
        layout.addWidget(self._settings_more_label)

        self._about_button = QPushButton(self._t("header_about", "About"))
        self._about_button.setObjectName("flatButton")
        self._about_button.clicked.connect(lambda: self.aboutRequested.emit())
        layout.addWidget(self._about_button)

        self._uninstall_button = QPushButton(self._t("header_uninstall", "Uninstall Driver"))
        self._uninstall_button.setObjectName("flatButton")
        self._uninstall_button.clicked.connect(
            lambda: self.uninstallDriverRequested.emit()
        )
        self._uninstall_button.setVisible(False)
        layout.addWidget(self._uninstall_button)

        layout.addStretch(1)

        self._settings_version = QLabel(self._version)
        self._settings_version.setObjectName("versionLabel")
        layout.addWidget(self._settings_version)

        return panel

    def _on_language_index_changed(self, index):
        code = self._language_combo.itemData(index)
        if code and code != self._language:
            self.languageChanged.emit(code)

    def set_pin(self, pin, required):
        self._pin = pin or ""
        self._pin_required = bool(required)
        self._require_pin_check.blockSignals(True)
        self._require_pin_check.setChecked(self._pin_required)
        self._require_pin_check.blockSignals(False)
        self._refresh_pin_labels()

    def _refresh_pin_labels(self):
        self._settings_pin_value.setText(self._pin or "------")
        if self._pin_required and self._pin:
            self._tutorial_pin.setText(f'{self._t("settings_pin", "PIN")}: {self._pin}')
            self._tutorial_pin.setVisible(True)
        else:
            self._tutorial_pin.setText("")
            self._tutorial_pin.setVisible(False)

    def _layout_settings(self):
        width = self._container.width()
        height = self._container.height()
        panel_width = min(SETTINGS_PANEL_WIDTH, max(0, width))
        x = width - panel_width if self._settings_open else width
        self._settings_panel.setGeometry(x, 0, panel_width, height)
        self._scrim.setGeometry(0, 0, width, height)

    def _set_settings_open(self, open_):
        if open_ == self._settings_open:
            return
        self._settings_open = open_

        width = self._container.width()
        height = self._container.height()
        panel_width = min(SETTINGS_PANEL_WIDTH, max(0, width))
        end_x = width - panel_width if open_ else width

        if open_:
            self._scrim.setGeometry(0, 0, width, height)
            self._scrim.show()
            self._scrim.raise_()
            self._settings_panel.show()
            self._settings_panel.raise_()
        else:
            self._scrim.raise_()

        self._settings_anim.stop()
        self._settings_anim.setStartValue(
            QRect(self._settings_panel.x(), 0, panel_width, height)
        )
        self._settings_anim.setEndValue(QRect(end_x, 0, panel_width, height))
        self._settings_anim.start()

    def _on_settings_anim_finished(self):
        if not self._settings_open:
            self._settings_panel.hide()
            self._scrim.hide()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if getattr(self, "_container", None) is not None:
            self._layout_settings()

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

    # ------------------------------------------------------------------
    # language
    # ------------------------------------------------------------------
    def set_language(self, language):
        self._language = language
        position = self._language_combo.findData(language)
        if position >= 0 and position != self._language_combo.currentIndex():
            self._language_combo.blockSignals(True)
            self._language_combo.setCurrentIndex(position)
            self._language_combo.blockSignals(False)
        self.retranslate()

    def retranslate(self):
        self._settings_title.setText(self._t("settings_title", "Settings"))
        self._settings_lang_label.setText(self._t("settings_language", "Language"))
        self._settings_more_label.setText(self._t("settings_more", "More"))
        self._require_pin_check.setText(self._t("settings_require_pin", "Require PIN"))
        self._new_pin_button.setText(self._t("settings_new_pin", "New PIN"))
        self._refresh_pin_labels()
        self._settings_button.setToolTip(self._t("settings_title", "Settings"))
        self._about_button.setText(self._t("header_about", "About"))
        self._uninstall_button.setText(self._t("header_uninstall", "Uninstall Driver"))
        self._status_title.setText(self._t("status_label", "Mobile Connection"))
        self._gain_label.setText(self._t("desktop_gain", "Volume"))
        self._port_label.setText(self._t("host_port", "Port"))
        self._apply_port_button.setText(self._t("host_apply", "Apply"))
        self._tutorial_title.setText(self._t("tutorial_title", "Waiting for Mobile"))
        self._tutorial_warn.setText(
            self._t("tutorial_warn", "The \u201cNot Secure\u201d warning is normal.")
        )
        for button in self._copy_buttons:
            button.setText(self._t("host_copy", "Copy"))
        self.set_active(self._active)
        self._refresh_status()

    # ------------------------------------------------------------------
    # updates coming from the session
    # ------------------------------------------------------------------
    def set_level_provider(self, provider):
        self._level_provider = provider
        self._mic_button.set_level_provider(provider)

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

    def set_addresses(self, addresses):
        while self._address_box.count():
            item = self._address_box.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
            nested = item.layout()
            if nested is not None:
                while nested.count():
                    sub_item = nested.takeAt(0)
                    sub_widget = sub_item.widget()
                    if sub_widget is not None:
                        sub_widget.deleteLater()

        self._address_buttons = []
        self._copy_buttons = []

        for url in addresses:
            row = QHBoxLayout()
            row.setSpacing(6)

            button = QPushButton(url)
            button.setObjectName("addressButton")
            button.setCursor(Qt.PointingHandCursor)
            button.clicked.connect(lambda _=False, target=url: self.addressSelected.emit(target))
            row.addWidget(button, 1)

            copy_button = QPushButton(self._t("host_copy", "Copy"))
            copy_button.setObjectName("copyButton")
            copy_button.setCursor(Qt.PointingHandCursor)
            copy_button.clicked.connect(
                lambda _=False, target=url, btn=copy_button: self._copy_address(target, btn)
            )
            row.addWidget(copy_button, 0)

            self._address_box.addLayout(row)
            self._address_buttons.append(button)
            self._copy_buttons.append(copy_button)

        if addresses:
            self.addressSelected.emit(addresses[0])

    def _copy_address(self, url, button):
        clipboard = QApplication.clipboard()
        if clipboard is not None:
            clipboard.setText(url)
        button.setText(self._t("host_copied", "Copied"))
        QTimer.singleShot(1200, lambda: self._reset_copy_button(button))

    def _reset_copy_button(self, button):
        # The row may have been rebuilt while the timer was pending.
        try:
            button.setText(self._t("host_copy", "Copy"))
        except RuntimeError:
            pass

    def set_selected_address(self, url):
        self._selected_address = url
        for button in self._address_buttons:
            name = "addressButtonSelected" if button.text() == url else "addressButton"
            if button.objectName() != name:
                button.setObjectName(name)
                button.style().unpolish(button)
                button.style().polish(button)

    def set_port(self, port):
        self._port_input.blockSignals(True)
        self._port_input.setValue(int(port))
        self._port_input.blockSignals(False)

    def _on_apply_port(self):
        self.portChangeRequested.emit(self._port_input.value())

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
        self._update_mic_state()
        self._refresh_status()

    def set_rtc_state(self, state):
        self._rtc_state = state or "new"
        self._refresh_status()

    def set_muted(self, muted):
        self._muted = muted
        self._update_mic_state()
        self._refresh_status()

    def _update_mic_state(self):
        if not self._presence:
            self._mic_button.set_state("idle")
        elif self._muted:
            self._mic_button.set_state("muted")
        else:
            self._mic_button.set_state("active")

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

    def closeEvent(self, event):
        if getattr(self, "allow_close", False):
            event.accept()
            return
        event.ignore()
        self.hide()
        on_hidden = getattr(self, "on_hidden", None)
        if on_hidden is not None:
            on_hidden()
