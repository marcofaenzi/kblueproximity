"""Application controller: tray + preferences + workers."""
from __future__ import annotations

import os
import socket
import sys
import time

from PySide6.QtCore import QObject, QSocketNotifier, QTimer, Signal, Slot
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QMessageBox,
    QSystemTrayIcon,
)

from blueproximity import SW_VERSION
from blueproximity.behavior import load_behavior, save_behavior
from blueproximity.config import load_configs
from blueproximity.core import Proximity
from blueproximity.i18n import _
from blueproximity.paths import (
    ICON_ATT,
    ICON_AWAY,
    ICON_BASE,
    ICON_ERROR,
    ICON_PAUSE,
    icon_path,
)
from blueproximity.ui.preferences import PreferencesWindow


class ChannelScanWorker(QObject):
    port_result = Signal(str, str)
    finished = Signal(bool)

    def __init__(self, mac: str, was_paused: bool):
        super().__init__()
        self.mac = mac
        self.was_paused = was_paused
        self._stop = False

    def stop(self):
        self._stop = True

    @Slot()
    def run(self):
        from blueproximity.bluetooth import scan_rfcomm_port

        for port in range(1, 31):
            if self._stop:
                break
            result = scan_rfcomm_port(self.mac, port)
            self.port_result.emit(str(port), result)
            time.sleep(0.5)
        self.finished.emit(self.was_paused)


class DeviceScanWorker(QObject):
    finished = Signal(object)

    def __init__(self, proxi: Proximity):
        super().__init__()
        self.proxi = proxi

    @Slot()
    def run(self):
        tmp_mac = self.proxi.dev_mac
        self.proxi.dev_mac = ''
        self.proxi.kill_connection()
        try:
            macs = self.proxi.get_device_list()
        except Exception as exc:
            macs = [['', _('Scan failed: %s') % exc]]
        self.proxi.dev_mac = tmp_mac
        self.finished.emit(macs)


class BlueProximityApp(QObject):
    def __init__(self, configs, show_window_on_start: bool):
        super().__init__()
        self.configs = configs
        self.pause_mode = False
        self.configname = configs[0][0]
        self.config = configs[0][1]
        self.proxi = configs[0][2]
        self.min_dist = -255
        self.max_dist = 0
        self._scan_thread = None
        self._scan_worker = None
        self._channel_thread = None
        self._channel_worker = None
        self.behavior = load_behavior()

        self.prefs = PreferencesWindow(self)
        self.prefs.settings_changed.connect(self.write_settings)
        self.prefs.settings_changed_reconnect.connect(self.write_settings_reconnect)
        self.prefs.behavior_changed.connect(self.write_behavior)
        self.prefs.scan_devices_requested.connect(self.scan_devices)
        self.prefs.scan_channels_requested.connect(self.scan_channels)
        self.prefs.config_selected.connect(self.select_config)
        self.prefs.new_config_requested.connect(self.create_config)
        self.prefs.rename_config_requested.connect(self.rename_config)
        self.prefs.delete_config_requested.connect(self.delete_config)
        self.prefs.reset_minmax_requested.connect(self.reset_minmax)
        self.prefs.about_requested.connect(self.show_about)
        self.prefs.closed.connect(self.on_prefs_closed)

        self._app_icon = QIcon(icon_path(ICON_BASE))
        self.prefs.setWindowIcon(self._app_icon)

        self._build_tray()
        self.prefs.fill_config_combo(self.configs, self.configname)
        self.prefs.read_settings(self.config)
        self.prefs.read_behavior(self.behavior)
        self.prefs.set_gone_live(True)
        self._apply_behavior()

        self.state_timer = QTimer(self)
        self.state_timer.timeout.connect(self.update_state)
        self.state_timer.start(1000)

        if show_window_on_start:
            self.show_preferences()

    def _build_tray(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            QMessageBox.critical(
                None,
                'BlueProximity',
                _('System tray is not available on this desktop.'),
            )
            sys.exit(1)

        self.tray = QSystemTrayIcon(self)
        self.tray.setIcon(QIcon(icon_path(ICON_ERROR)))
        self.tray.setToolTip('BlueProximity')
        self.tray.activated.connect(self._tray_activated)

        from PySide6.QtWidgets import QMenu
        menu = QMenu()
        self.act_prefs = QAction(_('Preferences'), menu)
        self.act_prefs.triggered.connect(self.show_preferences)
        menu.addAction(self.act_prefs)

        self.act_pause = QAction(_('Pause'), menu)
        self.act_pause.triggered.connect(self.toggle_pause)
        menu.addAction(self.act_pause)

        self.act_about = QAction(_('About'), menu)
        self.act_about.triggered.connect(self.show_about)
        menu.addAction(self.act_about)
        menu.addSeparator()

        self.act_quit = QAction(_('Quit'), menu)
        self.act_quit.triggered.connect(self.quit)
        menu.addAction(self.act_quit)

        self.tray.setContextMenu(menu)
        self._update_pause_action()

    def _apply_behavior(self):
        hide_tray = bool(self.behavior.get('hide_systray'))
        if hide_tray:
            self.tray.hide()
        else:
            self.tray.show()
        if bool(self.behavior.get('start_paused')) and not self.pause_mode:
            self.toggle_pause()

    def write_behavior(self):
        data = self.prefs.collect_behavior()
        was_hidden = bool(self.behavior.get('hide_systray'))
        for key, value in data.items():
            self.behavior[key] = value
        save_behavior(self.behavior)
        self.prefs.read_behavior(self.behavior)
        hide_tray = bool(self.behavior.get('hide_systray'))
        if hide_tray:
            self.tray.hide()
        else:
            self.tray.show()
        if hide_tray and not was_hidden:
            QMessageBox.information(
                self.prefs,
                'BlueProximity',
                'The tray icon is now hidden. Open BlueProximity from the '
                'application menu to show this window again.',
            )

    def _tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            if self.prefs.isVisible():
                self.prefs.hide()
            else:
                self.show_preferences()
        elif reason == QSystemTrayIcon.ActivationReason.MiddleClick:
            self.toggle_pause()

    def _update_pause_action(self):
        if self.pause_mode:
            self.act_pause.setText(_('Resume'))
        else:
            self.act_pause.setText(_('Pause'))

    def show_preferences(self):
        self.prefs.show()
        self.prefs.raise_()
        self.prefs.activateWindow()
        for config in self.configs:
            config[2].Simulate = True

    def on_prefs_closed(self):
        for config in self.configs:
            config[2].Simulate = False

    def toggle_pause(self):
        if self.pause_mode:
            self.pause_mode = False
            for config in self.configs:
                config[2].dev_mac = getattr(config[2], 'lastMAC', config[2].dev_mac)
                config[2].Simulate = False
        else:
            self.pause_mode = True
            for config in self.configs:
                config[2].lastMAC = config[2].dev_mac
                config[2].dev_mac = ''
                config[2].Simulate = True
                config[2].kill_connection()
        self._update_pause_action()

    def reset_minmax(self):
        self.min_dist = -255
        self.max_dist = 0

    def write_settings(self):
        data = self.prefs.collect_settings()
        self.proxi.dev_mac = data['device_mac']
        self.proxi.dev_channel = data['device_channel']
        self.proxi.gone_limit = -data['lock_distance']
        self.proxi.gone_duration = data['lock_duration']
        self.proxi.active_limit = -data['unlock_distance']
        self.proxi.active_duration = data['unlock_duration']
        for key, value in data.items():
            self.config[key] = value
        self.proxi.logger.configureFromConfig(self.config)
        self.config.write()

    def write_settings_reconnect(self):
        self.proxi.kill_connection()
        self.write_settings()

    def select_config(self, name: str):
        if name == self.configname or not name:
            return
        for conf in self.configs:
            if conf[0] == name:
                self.config = conf[1]
                self.configname = conf[0]
                self.proxi = conf[2]
                self.prefs.read_settings(self.config)
                break

    def create_config(self, newconfig: str):
        if not newconfig:
            QMessageBox.warning(
                self.prefs,
                'BlueProximity',
                _('You must enter a name for the new configuration.'),
            )
            return
        newname = os.path.join(
            os.getenv('HOME', ''), '.blueproximity', newconfig + '.conf')
        if os.path.exists(newname):
            QMessageBox.warning(
                self.prefs,
                'BlueProximity',
                _("A configuration file with the name '%s' already exists.") % newname,
            )
            return
        from configobj import ConfigObj
        newconf = ConfigObj(self.config.dict())
        newconf.filename = newname
        newconf.write()
        p = Proximity(newconf)
        p.Simulate = True
        p.start()
        self.configs.append([newconfig, newconf, p])
        self.config = newconf
        self.configname = newconfig
        self.proxi = p
        self.configs.sort()
        self.prefs.fill_config_combo(self.configs, self.configname)
        self.prefs.read_settings(self.config)

    def rename_config(self, newconfig: str):
        if not newconfig:
            QMessageBox.warning(
                self.prefs,
                'BlueProximity',
                _('You must enter a name for the configuration.'),
            )
            return
        newname = os.path.join(
            os.getenv('HOME', ''), '.blueproximity', newconfig + '.conf')
        if os.path.exists(newname):
            QMessageBox.warning(
                self.prefs,
                'BlueProximity',
                _("A configuration file with the name '%s' already exists.") % newname,
            )
            return
        config_entry = None
        for conf in self.configs:
            if conf[0] == self.configname:
                config_entry = conf
                break
        oldfile = self.config.filename
        self.config.filename = newname
        self.config.write()
        try:
            os.remove(oldfile)
        except OSError:
            print(_("The configfile '%s' could not be deleted.") % oldfile)
        self.configname = newconfig
        if config_entry is not None:
            config_entry[0] = newconfig
        self.prefs.fill_config_combo(self.configs, self.configname)

    def delete_config(self):
        if len(self.configs) == 1:
            QMessageBox.warning(
                self.prefs,
                'BlueProximity',
                _('The last configuration file cannot be deleted.'),
            )
            return
        reply = QMessageBox.question(
            self.prefs,
            'BlueProximity',
            _("Do you really want to delete the configuration '%s'.") % self.configname,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        oldfile = self.config.filename
        self.proxi.Stop = True
        self.configs = [c for c in self.configs if c[0] != self.configname]
        try:
            os.remove(oldfile)
        except OSError:
            pass
        self.configname = self.configs[0][0]
        self.config = self.configs[0][1]
        self.proxi = self.configs[0][2]
        self.prefs.fill_config_combo(self.configs, self.configname)
        self.prefs.read_settings(self.config)

    def scan_devices(self):
        from PySide6.QtCore import QThread
        self.prefs.set_config_management_enabled(False)
        self.prefs.set_device_scan_busy(True)
        self._scan_thread = QThread()
        self._scan_worker = DeviceScanWorker(self.proxi)
        self._scan_worker.moveToThread(self._scan_thread)
        self._scan_thread.started.connect(self._scan_worker.run)
        self._scan_worker.finished.connect(self._on_device_scan_done)
        self._scan_worker.finished.connect(self._scan_thread.quit)
        self._scan_thread.start()

    def _on_device_scan_done(self, macs):
        self.prefs.set_device_list(macs)
        self.prefs.set_device_scan_busy(False)
        self.prefs.set_config_management_enabled(True)

    def scan_channels(self, start: bool):
        from PySide6.QtCore import QThread

        if not start:
            if self._channel_worker:
                self._channel_worker.stop()
            return

        mac = self.proxi.dev_mac
        if self.pause_mode:
            mac = getattr(self.proxi, 'lastMAC', mac)
            was_paused = True
        else:
            self.toggle_pause()
            was_paused = False

        if not mac:
            QMessageBox.warning(
                self.prefs,
                'BlueProximity',
                _('No bluetooth device configured...'),
            )
            if not was_paused:
                self.toggle_pause()
            return

        QMessageBox.information(
            self.prefs,
            'BlueProximity',
            _(
                'The scanning process tries to connect to each of '
                'the 30 possible ports. This will take some time and '
                'you should watch your bluetooth device for any actions '
                'to be taken. If possible click on accept/connect. If you '
                'are asked for a pin your device was not paired properly before, '
                'see the manual on how to fix this.',
            ),
        )
        self.prefs.set_config_management_enabled(False)
        self.prefs.set_channel_scan_active(True)
        self.prefs.clear_channel_scan()
        self._channel_thread = QThread()
        self._channel_worker = ChannelScanWorker(mac, was_paused)
        self._channel_worker.moveToThread(self._channel_thread)
        self._channel_thread.started.connect(self._channel_worker.run)
        self._channel_worker.port_result.connect(self.prefs.add_channel_result)
        self._channel_worker.finished.connect(self._on_channel_scan_done)
        self._channel_worker.finished.connect(self._channel_thread.quit)
        self._channel_thread.start()

    def _on_channel_scan_done(self, was_paused: bool):
        self.prefs.set_channel_scan_active(False)
        self.prefs.set_config_management_enabled(True)
        if not was_paused:
            self.toggle_pause()
            self.proxi.Simulate = True

    def update_state(self):
        new_val = int(self.proxi.Dist)
        if new_val > self.min_dist:
            self.min_dist = new_val
        if new_val < self.max_dist:
            self.max_dist = new_val
        self.prefs.update_distance_display(
            -self.min_dist, -self.max_dist, self.proxi.State, -new_val)

        if self.pause_mode:
            self.tray.setIcon(QIcon(icon_path(ICON_PAUSE)))
            self.tray.setToolTip('BlueProximity\n-- PAUSED --')
            return

        distance = -new_val
        tooltip = 'BlueProximity\nDistance: %d' % distance

        connection_state = 0
        con_icons = [ICON_BASE, ICON_ATT, ICON_AWAY, ICON_ERROR]
        for config in self.configs:
            if config[2].ErrorMsg == 'No connection found, trying to establish one...':
                connection_state = 3
            else:
                if config[2].State != _('active'):
                    if connection_state < 2:
                        connection_state = 2
                else:
                    if new_val < config[2].active_limit:
                        if connection_state < 1:
                            connection_state = 1
        self.tray.setIcon(QIcon(icon_path(con_icons[connection_state])))
        self.tray.setToolTip(tooltip)

    def show_about(self):
        about = QMessageBox(
            QMessageBox.Icon.NoIcon,
            _('About BlueProximity'),
            _(
                '<h3>BlueProximity {version}</h3>'
                '<p>Locks and unlocks your desktop based on Bluetooth proximity.</p>'
                '<p>Qt6 / KDE edition.</p>'
                '<p>Copyright Lars Friedrichs and contributors.<br/>'
                'Licensed under the GPL.</p>'
                '<p><a href="https://github.com/marcofaenzi/blueproximity">'
                'https://github.com/marcofaenzi/blueproximity</a></p>'
            ).format(version=SW_VERSION),
            parent=self.prefs if self.prefs.isVisible() else None,
        )
        about.setWindowIcon(self._app_icon)
        about.setIconPixmap(self._app_icon.pixmap(64, 64))
        about.exec()

    def quit(self):
        for config in self.configs:
            config[2].logger.log_line(_('stopped.'))
            config[2].Stop = True
        self.state_timer.stop()
        self.tray.hide()
        QApplication.instance().quit()


INSTANCE_SOCKET = os.path.join(
    os.getenv('XDG_RUNTIME_DIR', '/tmp'), 'blueproximity.sock')


def _try_activate_existing() -> bool:
    client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        client.settimeout(0.3)
        client.connect(INSTANCE_SOCKET)
        client.sendall(b'show')
        return True
    except OSError:
        return False
    finally:
        client.close()


def _listen_for_second_instance(on_show):
    try:
        os.unlink(INSTANCE_SOCKET)
    except FileNotFoundError:
        pass
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.setblocking(False)
    server.bind(INSTANCE_SOCKET)
    server.listen(4)
    notifier = QSocketNotifier(server.fileno(), QSocketNotifier.Type.Read)

    def _accept(_socket=None):
        try:
            conn, _addr = server.accept()
        except BlockingIOError:
            return
        try:
            conn.close()
        except OSError:
            pass
        on_show()

    notifier.activated.connect(_accept)
    return server, notifier


def run_app():
    from blueproximity.i18n import setup_i18n
    setup_i18n()

    app = QApplication(sys.argv)
    app.setApplicationName('BlueProximity')
    app.setDesktopFileName('blueproximity')
    app.setWindowIcon(QIcon(icon_path(ICON_BASE)))
    app.setQuitOnLastWindowClosed(False)

    if _try_activate_existing():
        return 0

    configs, is_new = load_configs()
    for config in configs:
        p = Proximity(config[1])
        p.start()
        config.append(p)
    configs.sort()

    controller = BlueProximityApp(configs, is_new)
    app._blueproximity = controller
    app._instance_server = _listen_for_second_instance(controller.show_preferences)
    return app.exec()
