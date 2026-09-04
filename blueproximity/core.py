"""Proximity detection engine (no GUI dependencies)."""
from __future__ import annotations

import math
import shutil
import subprocess
import threading
import time

from blueproximity.bluetooth import bluetooth, bluez, list_bluetooth_devices
from blueproximity.i18n import _
from blueproximity.logger import Logger


class Proximity(threading.Thread):
    """Bluetooth proximity worker thread."""

    def __init__(self, config):
        threading.Thread.__init__(self, name='WorkerThread')
        self.daemon = True
        self.config = config
        self.Dist = -255
        self.State = _('gone')
        self.Simulate = False
        self.Stop = False
        self.procid = 0
        self.dev_mac = self.config['device_mac']
        self.dev_channel = self.config['device_channel']
        self.ringbuffer_size = self.config['buffer_size']
        self.ringbuffer = [-254] * self.ringbuffer_size
        self.ringbuffer_pos = 0
        self.gone_duration = self.config['lock_duration']
        self.gone_limit = -self.config['lock_distance']
        self.active_duration = self.config['unlock_duration']
        self.active_limit = -self.config['unlock_distance']
        self.ErrorMsg = _('Initialized...')
        self.sock = None
        self.ignoreFirstTransition = True
        self.logger = Logger()
        self.logger.configureFromConfig(self.config)
        self.timeAct = 0
        self.timeGone = 0
        self.timeProx = 0
        self.lastMAC = self.dev_mac

    def get_device_list(self):
        return list_bluetooth_devices()

    def kill_connection(self):
        if self.sock is not None:
            try:
                self.sock.close()
            except Exception:
                pass
        self.sock = None
        return 0

    def get_proximity_once(self, dev_mac):
        if shutil.which('hcitool'):
            try:
                result = subprocess.run(
                    ['hcitool', 'rssi', dev_mac],
                    capture_output=True,
                    text=True,
                    timeout=2,
                )
                if result.returncode == 0 and ':' in result.stdout:
                    return int(result.stdout.split(':')[1].strip())
            except (subprocess.TimeoutExpired, ValueError, IndexError):
                pass
        return -255

    def get_connection(self, dev_mac, dev_channel):
        try:
            self.procid = 1
            _sock = bluez.btsocket()
            self.sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM, _sock)
            self.sock.connect((dev_mac, dev_channel))
        except Exception:
            self.procid = 0
        return self.procid

    def run_cycle(self, dev_mac, dev_channel):
        self.ringbuffer_pos = (self.ringbuffer_pos + 1) % self.ringbuffer_size
        self.ringbuffer[self.ringbuffer_pos] = self.get_proximity_once(dev_mac)
        ret_val = sum(self.ringbuffer)
        if self.ringbuffer[self.ringbuffer_pos] == -255:
            self.ErrorMsg = _('No connection found, trying to establish one...')
            self.kill_connection()
            self.get_connection(dev_mac, dev_channel)
        return int(ret_val / self.ringbuffer_size)

    def _run_action_command(self, command, action_name):
        command = str(command or '').strip()
        if not command:
            self.logger.debug_line(
                self.config, _('Skipping %s: empty command') % action_name)
            return

        self.logger.debug_line(
            self.config, _('Running %s command: %s') % (action_name, command))
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=15,
            )
            output = (result.stdout + result.stderr).strip()
            self.logger.debug_line(
                self.config,
                _('%s finished with exit code %d%s') % (
                    action_name,
                    result.returncode,
                    (': ' + output) if output else '',
                ),
            )
            if result.returncode != 0:
                self.ErrorMsg = _('%s command failed (exit %d): %s') % (
                    action_name, result.returncode, output or command)
        except subprocess.TimeoutExpired:
            self.logger.debug_line(self.config, _('%s command timed out') % action_name)
            self.ErrorMsg = _('%s command timed out') % action_name
        except Exception as exc:
            self.logger.debug_line(
                self.config, _('%s command error: %s') % (action_name, exc))
            self.ErrorMsg = str(exc)

    def _async(self, target):
        threading.Thread(target=target, daemon=True).start()

    def go_active(self):
        if self.ignoreFirstTransition:
            self.ignoreFirstTransition = False
            return
        self.logger.log_line(_('screen is unlocked'))
        if self.timeAct == 0:
            self.timeAct = time.time()
            self._run_action_command(self.config['unlock_command'], _('unlock'))
            self.timeAct = 0
        else:
            msg = _(
                'A command for %s has been skipped because the former '
                'command did not finish yet.') % _('unlocking')
            self.logger.log_line(msg)
            self.ErrorMsg = msg

    def go_gone(self):
        if self.ignoreFirstTransition:
            self.ignoreFirstTransition = False
            return
        self.logger.log_line(_('screen is locked'))
        if self.timeGone == 0:
            self.timeGone = time.time()
            self._run_action_command(self.config['lock_command'], _('lock'))
            self.timeGone = 0
        else:
            msg = _(
                'A command for %s has been skipped because the former '
                'command did not finish yet.') % _('locking')
            self.logger.log_line(msg)
            self.ErrorMsg = msg

    def go_proximity(self):
        if self.timeProx == 0:
            self.timeProx = time.time()
            self._run_action_command(
                self.config['proximity_command'], _('proximity'))
            self.timeProx = 0
        else:
            msg = _(
                'A command for %s has been skipped because the former '
                'command did not finish yet.') % _('proximity')
            self.logger.log_line(msg)
            self.ErrorMsg = msg

    def run(self):
        duration_count = 0
        state = _('gone')
        proxi_cmd_counter = 0
        while not self.Stop:
            try:
                scan_period = max(1, int(self.config.get('scan_period', 1)))
                if self.dev_mac != '':
                    self.ErrorMsg = _('running...')
                    dist = self.run_cycle(self.dev_mac, self.dev_channel)
                else:
                    dist = -255
                    self.ErrorMsg = 'No bluetooth device configured...'
                lock_cycles = max(1, int(math.ceil(float(self.gone_duration) / scan_period)))
                unlock_cycles = max(
                    1, int(math.ceil(float(self.active_duration) / scan_period)))
                if state == _('gone'):
                    if dist >= self.active_limit:
                        duration_count += 1
                        if duration_count >= unlock_cycles:
                            state = _('active')
                            duration_count = 0
                            if not self.Simulate:
                                self._async(self.go_active)
                    else:
                        duration_count = 0
                else:
                    if dist <= self.gone_limit:
                        duration_count += 1
                        if duration_count >= lock_cycles:
                            state = _('gone')
                            proxi_cmd_counter = 0
                            duration_count = 0
                            if not self.Simulate:
                                self._async(self.go_gone)
                    else:
                        duration_count = 0
                        proxi_cmd_counter += 1
                if dist != self.Dist or state != self.State:
                    self.logger.debug_line(
                        self.config,
                        _('distance=%d state=%s limits lock<=%d unlock>=%d') % (
                            dist, state, self.gone_limit, self.active_limit),
                    )
                self.State = state
                self.Dist = dist
                prox_cycles = max(
                    1,
                    int(math.ceil(
                        float(self.config['proximity_interval']) / scan_period)),
                )
                if (
                    proxi_cmd_counter >= prox_cycles
                    and not self.Simulate
                    and self.config['proximity_command'] != ''
                ):
                    proxi_cmd_counter = 0
                    self._async(self.go_proximity)
                time.sleep(scan_period)
            except KeyboardInterrupt:
                break
        self.kill_connection()
