"""Preferences window (Qt Widgets)."""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QSlider,
    QSpinBox,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from blueproximity.config import (
    LOCK_COMMAND_SUGGESTIONS,
    PROXIMITY_COMMAND_SUGGESTIONS,
    SYSLOG_FACILITIES,
    UNLOCK_COMMAND_SUGGESTIONS,
)
from blueproximity.i18n import _


class NameDialog(QDialog):
    def __init__(self, title: str, prompt: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(prompt))
        self.entry = QLineEdit()
        layout.addWidget(self.entry)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def name(self) -> str:
        return self.entry.text().strip()


class PreferencesWindow(QMainWindow):
    settings_changed = Signal()
    settings_changed_reconnect = Signal()
    scan_devices_requested = Signal()
    scan_channels_requested = Signal(bool)
    config_selected = Signal(str)
    new_config_requested = Signal(str)
    rename_config_requested = Signal(str)
    delete_config_requested = Signal()
    reset_minmax_requested = Signal()
    about_requested = Signal()
    closed = Signal()

    def __init__(self, parent=None):
        super().__init__()
        self.setWindowTitle(_('BlueProximity Preferences'))
        self.resize(720, 560)
        self._gone_live = False
        self._scanning_channels = False
        self._block_signals = False

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)

        # Config selector row
        cfg_row = QHBoxLayout()
        cfg_row.addWidget(QLabel(_('Configuration:')))
        self.combo_config = QComboBox()
        self.combo_config.currentTextChanged.connect(self._on_config_changed)
        cfg_row.addWidget(self.combo_config, stretch=1)
        self.btn_new = QPushButton(_('New'))
        self.btn_new.clicked.connect(self._on_new)
        cfg_row.addWidget(self.btn_new)
        self.btn_rename = QPushButton(_('Rename'))
        self.btn_rename.clicked.connect(self._on_rename)
        cfg_row.addWidget(self.btn_rename)
        self.btn_delete = QPushButton(_('Delete'))
        self.btn_delete.clicked.connect(lambda: self.delete_config_requested.emit())
        cfg_row.addWidget(self.btn_delete)
        root.addLayout(cfg_row)

        tabs = QTabWidget()
        root.addWidget(tabs, stretch=1)
        tabs.addTab(self._build_device_tab(), _('Bluetooth Device'))
        tabs.addTab(self._build_proximity_tab(), _('Proximity Details'))
        tabs.addTab(self._build_locking_tab(), _('Locking'))

        bottom = QHBoxLayout()
        btn_about = QPushButton(_('About'))
        btn_about.clicked.connect(lambda: self.about_requested.emit())
        bottom.addWidget(btn_about)
        bottom.addStretch(1)
        btn_close = QPushButton(_('Close'))
        btn_close.clicked.connect(self.close)
        bottom.addWidget(btn_close)
        root.addLayout(bottom)

    def _build_device_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        self.table_devices = QTableWidget(0, 2)
        self.table_devices.setHorizontalHeaderLabels([_('MAC'), _('Name')])
        self.table_devices.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch)
        self.table_devices.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table_devices.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        layout.addWidget(self.table_devices)

        btn_row = QHBoxLayout()
        self.btn_scan = QPushButton(_('Scan for devices'))
        self.btn_scan.clicked.connect(lambda: self.scan_devices_requested.emit())
        btn_row.addWidget(self.btn_scan)
        self.btn_use = QPushButton(_('Use selected device'))
        self.btn_use.clicked.connect(self._use_selected_device)
        btn_row.addWidget(self.btn_use)
        layout.addLayout(btn_row)

        form = QFormLayout()
        self.entry_mac = QLineEdit()
        self.entry_mac.editingFinished.connect(self._emit_settings)
        form.addRow(_('MAC address:'), self.entry_mac)

        self.spin_channel = QSpinBox()
        self.spin_channel.setRange(1, 30)
        self.spin_channel.valueChanged.connect(self._emit_settings_reconnect)
        form.addRow(_('RFCOMM channel:'), self.spin_channel)
        layout.addLayout(form)

        self.btn_scan_channel = QPushButton(_('Scan channels on device'))
        self.btn_scan_channel.clicked.connect(self._toggle_channel_scan)
        layout.addWidget(self.btn_scan_channel)

        self.table_channels = QTableWidget(0, 2)
        self.table_channels.setHorizontalHeaderLabels([_('Channel'), _('State')])
        self.table_channels.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch)
        self.table_channels.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table_channels.itemSelectionChanged.connect(self._channel_selected)
        self.table_channels.hide()
        layout.addWidget(self.table_channels)
        return w

    def _build_proximity_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        self.slider_lock_dist, self.spin_lock_dist = self._make_slider_spin(0, 127)
        self.slider_lock_dur, self.spin_lock_dur = self._make_slider_spin(0, 120)
        self.slider_unlock_dist, self.spin_unlock_dist = self._make_slider_spin(0, 127)
        self.slider_unlock_dur, self.spin_unlock_dur = self._make_slider_spin(0, 120)

        form = QFormLayout()
        form.addRow(_('Lock distance:'), self._slider_spin_row(
            self.slider_lock_dist, self.spin_lock_dist))
        form.addRow(_('Lock duration (s):'), self._slider_spin_row(
            self.slider_lock_dur, self.spin_lock_dur))
        form.addRow(_('Unlock distance:'), self._slider_spin_row(
            self.slider_unlock_dist, self.spin_unlock_dist))
        form.addRow(_('Unlock duration (s):'), self._slider_spin_row(
            self.slider_unlock_dur, self.spin_unlock_dur))
        layout.addLayout(form)

        self.lab_state = QLabel(_('min: 0 max: 0 state: -'))
        layout.addWidget(self.lab_state)
        self.slider_act = QSlider()
        self.slider_act.setOrientation(self.slider_lock_dist.orientation())
        self.slider_act.setRange(0, 127)
        self.slider_act.setEnabled(False)
        layout.addWidget(self.slider_act)

        btn_reset = QPushButton(_('Reset Min/Max'))
        btn_reset.clicked.connect(lambda: self.reset_minmax_requested.emit())
        layout.addWidget(btn_reset)
        layout.addStretch(1)
        return w

    def _build_locking_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        self.combo_lock = QComboBox()
        self.combo_lock.setEditable(True)
        self.combo_lock.addItems(LOCK_COMMAND_SUGGESTIONS)
        self.combo_lock.editTextChanged.connect(self._emit_settings)

        self.combo_unlock = QComboBox()
        self.combo_unlock.setEditable(True)
        self.combo_unlock.addItems(UNLOCK_COMMAND_SUGGESTIONS)
        self.combo_unlock.editTextChanged.connect(self._emit_settings)

        self.combo_proxi = QComboBox()
        self.combo_proxi.setEditable(True)
        self.combo_proxi.addItems(PROXIMITY_COMMAND_SUGGESTIONS)
        self.combo_proxi.editTextChanged.connect(self._emit_settings)

        self.slider_proxi = self._make_slider(5, 600)

        form = QFormLayout()
        form.addRow(_('Lock command:'), self.combo_lock)
        form.addRow(_('Unlock command:'), self.combo_unlock)
        form.addRow(_('Proximity command:'), self.combo_proxi)
        form.addRow(_('Proximity interval (s):'), self.slider_proxi)
        layout.addLayout(form)

        log_box = QGroupBox(_('Logging'))
        log_layout = QFormLayout(log_box)
        self.check_syslog = QCheckBox(_('Log to syslog'))
        self.check_syslog.stateChanged.connect(self._emit_settings)
        log_layout.addRow(self.check_syslog)
        self.combo_facility = QComboBox()
        self.combo_facility.addItems(SYSLOG_FACILITIES)
        self.combo_facility.currentTextChanged.connect(self._emit_settings)
        log_layout.addRow(_('Syslog facility:'), self.combo_facility)
        self.check_file = QCheckBox(_('Log to file'))
        self.check_file.stateChanged.connect(self._emit_settings)
        log_layout.addRow(self.check_file)
        self.entry_file = QLineEdit()
        self.entry_file.editingFinished.connect(self._emit_settings)
        log_layout.addRow(_('Log file:'), self.entry_file)
        layout.addWidget(log_box)
        layout.addStretch(1)
        return w

    def _make_slider(self, minimum: int, maximum: int) -> QSlider:
        from PySide6.QtCore import Qt
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(minimum, maximum)
        slider.valueChanged.connect(self._emit_settings)
        return slider

    def _make_slider_spin(self, minimum: int, maximum: int):
        """Horizontal slider synced with an editable numeric spin box."""
        from PySide6.QtCore import Qt
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(minimum, maximum)
        spin = QSpinBox()
        spin.setRange(minimum, maximum)
        spin.setKeyboardTracking(True)
        slider.valueChanged.connect(spin.setValue)
        spin.valueChanged.connect(slider.setValue)
        slider.valueChanged.connect(self._emit_settings)
        return slider, spin

    @staticmethod
    def _slider_spin_row(slider: QSlider, spin: QSpinBox) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(slider, stretch=1)
        spin.setFixedWidth(72)
        layout.addWidget(spin)
        return row

    def set_gone_live(self, value: bool):
        self._gone_live = value

    def _emit_settings(self, *_args):
        if self._gone_live and not self._block_signals:
            self.settings_changed.emit()

    def _emit_settings_reconnect(self, *_args):
        if self._gone_live and not self._block_signals:
            self.settings_changed_reconnect.emit()

    def fill_config_combo(self, configs, active_name: str):
        self._block_signals = True
        self.combo_config.blockSignals(True)
        self.combo_config.clear()
        for conf in configs:
            self.combo_config.addItem(conf[0])
        idx = self.combo_config.findText(active_name)
        if idx >= 0:
            self.combo_config.setCurrentIndex(idx)
        self.combo_config.blockSignals(False)
        self._block_signals = False

    def read_settings(self, config):
        self._block_signals = True
        self.entry_mac.setText(config['device_mac'])
        self.spin_channel.setValue(int(config['device_channel']))
        self.slider_lock_dist.setValue(int(config['lock_distance']))
        self.slider_lock_dur.setValue(int(config['lock_duration']))
        self.slider_unlock_dist.setValue(int(config['unlock_distance']))
        self.slider_unlock_dur.setValue(int(config['unlock_duration']))
        self._set_combo_text(self.combo_lock, config['lock_command'])
        self._set_combo_text(self.combo_unlock, config['unlock_command'])
        self._set_combo_text(self.combo_proxi, config['proximity_command'])
        self.slider_proxi.setValue(int(config['proximity_interval']))
        self.check_syslog.setChecked(bool(config['log_to_syslog']))
        idx = self.combo_facility.findText(config['log_syslog_facility'])
        if idx >= 0:
            self.combo_facility.setCurrentIndex(idx)
        self.check_file.setChecked(bool(config['log_to_file']))
        self.entry_file.setText(config['log_filelog_filename'])
        self._block_signals = False

    def _set_combo_text(self, combo: QComboBox, text: str):
        idx = combo.findText(text)
        if idx >= 0:
            combo.setCurrentIndex(idx)
        else:
            combo.insertItem(0, text)
            combo.setCurrentIndex(0)

    def collect_settings(self) -> dict:
        return {
            'device_mac': self.entry_mac.text().strip(),
            'device_channel': int(self.spin_channel.value()),
            'lock_distance': int(self.slider_lock_dist.value()),
            'lock_duration': int(self.slider_lock_dur.value()),
            'unlock_distance': int(self.slider_unlock_dist.value()),
            'unlock_duration': int(self.slider_unlock_dur.value()),
            'lock_command': self.combo_lock.currentText(),
            'unlock_command': self.combo_unlock.currentText(),
            'proximity_command': self.combo_proxi.currentText(),
            'proximity_interval': int(self.slider_proxi.value()),
            'log_to_syslog': self.check_syslog.isChecked(),
            'log_syslog_facility': self.combo_facility.currentText(),
            'log_to_file': self.check_file.isChecked(),
            'log_filelog_filename': self.entry_file.text(),
        }

    def update_distance_display(self, min_d, max_d, state, current):
        self.lab_state.setText(
            _('min: ') + str(min_d) + _(' max: ') + str(max_d) + _(' state: ') + state)
        self.slider_act.setValue(int(current))

    def set_config_management_enabled(self, enabled: bool):
        for w in (self.combo_config, self.btn_new, self.btn_rename, self.btn_delete):
            w.setEnabled(enabled)

    def set_device_scan_busy(self, busy: bool):
        self.btn_scan.setEnabled(not busy)
        if busy:
            self.table_devices.setRowCount(0)
            self.table_devices.insertRow(0)
            self.table_devices.setItem(0, 0, QTableWidgetItem('...'))
            self.table_devices.setItem(0, 1, QTableWidgetItem(_('Now scanning...')))

    def set_device_list(self, macs):
        self.table_devices.setRowCount(0)
        if not macs:
            macs = [[
                '',
                _('No Bluetooth devices found. Check that Bluetooth is enabled '
                  'and your phone is paired.'),
            ]]
        for mac, name in macs:
            row = self.table_devices.rowCount()
            self.table_devices.insertRow(row)
            self.table_devices.setItem(row, 0, QTableWidgetItem(mac))
            self.table_devices.setItem(row, 1, QTableWidgetItem(name))

    def _use_selected_device(self):
        rows = self.table_devices.selectionModel().selectedRows()
        if not rows:
            return
        mac_item = self.table_devices.item(rows[0].row(), 0)
        if mac_item and mac_item.text():
            self.entry_mac.setText(mac_item.text())
            self._emit_settings()

    def _toggle_channel_scan(self):
        if self._scanning_channels:
            self.scan_channels_requested.emit(False)
            self.set_channel_scan_active(False)
        else:
            self.scan_channels_requested.emit(True)

    def set_channel_scan_active(self, active: bool):
        self._scanning_channels = active
        if active:
            self.btn_scan_channel.setText(_('Stop scanning'))
            self.table_channels.show()
        else:
            self.btn_scan_channel.setText(_('Scan channels on device'))

    def clear_channel_scan(self):
        self.table_channels.setRowCount(0)

    def add_channel_result(self, channel: str, state: str):
        row = self.table_channels.rowCount()
        self.table_channels.insertRow(row)
        self.table_channels.setItem(row, 0, QTableWidgetItem(channel))
        self.table_channels.setItem(row, 1, QTableWidgetItem(state))

    def _channel_selected(self):
        rows = self.table_channels.selectionModel().selectedRows()
        if not rows:
            return
        item = self.table_channels.item(rows[0].row(), 0)
        if item:
            self.spin_channel.setValue(int(item.text()))
            self._emit_settings_reconnect()

    def _on_config_changed(self, name: str):
        if self._block_signals or not name:
            return
        self.config_selected.emit(name)

    def _on_new(self):
        dlg = NameDialog(_('New configuration'), _('Name:'), self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.new_config_requested.emit(dlg.name())

    def _on_rename(self):
        dlg = NameDialog(_('Rename configuration'), _('New name:'), self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.rename_config_requested.emit(dlg.name())

    def closeEvent(self, event):
        self.closed.emit()
        self.hide()
        event.ignore()
