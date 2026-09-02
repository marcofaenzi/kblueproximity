"""Bluetooth discovery and RFCOMM helpers."""
from __future__ import annotations

import sys

from blueproximity.i18n import _

IMPORT_BT = 0
bluetooth = None
bluez = None

try:
    import bluetooth as _bluetooth
    bluetooth = _bluetooth
    IMPORT_BT += 1
except ImportError:
    pass

try:
    import _bluetooth as _bluez
    bluez = _bluez
    IMPORT_BT += 1
except ImportError:
    try:
        import bluetooth._bluetooth as _bluez
        bluez = _bluez
        IMPORT_BT += 1
    except ImportError:
        pass

if IMPORT_BT != 2:
    print(_("The program cannot import the module bluetooth."))
    print(_("Please make sure the bluetooth bindings for python as well as bluez are installed."))
    print(_("e.g. with Ubuntu Linux, type"))
    print(_(" sudo apt-get install python3-bluez"))
    sys.exit(1)


def list_bluetooth_devices():
    """Return [[mac, name], ...] using BlueZ D-Bus, bluetoothctl, and inquiry scan."""
    ret_tab = []
    seen = set()

    def add_device(mac, name):
        mac = str(mac).strip()
        if not mac or mac in seen:
            return
        seen.add(mac)
        ret_tab.append([mac, str(name or '')])

    try:
        import dbus
        bus = dbus.SystemBus()
        manager = dbus.Interface(
            bus.get_object('org.bluez', '/'),
            'org.freedesktop.DBus.ObjectManager',
        )
        for interfaces in manager.GetManagedObjects().values():
            if 'org.bluez.Device1' not in interfaces:
                continue
            props = interfaces['org.bluez.Device1']
            add_device(
                props.get('Address', ''),
                props.get('Alias') or props.get('Name') or '',
            )
    except Exception:
        pass

    if not ret_tab:
        try:
            import subprocess
            result = subprocess.run(
                ['bluetoothctl', 'devices'],
                capture_output=True,
                text=True,
                timeout=10,
            )
            for line in result.stdout.splitlines():
                parts = line.split(' ', 2)
                if len(parts) >= 3 and parts[0] == 'Device':
                    add_device(parts[1], parts[2])
        except Exception:
            pass

    try:
        for bdaddr in bluetooth.discover_devices(
                duration=8, lookup_names=True, flush_cache=True):
            name = ''
            try:
                name = bluetooth.lookup_name(bdaddr) or ''
            except Exception:
                pass
            add_device(bdaddr, name)
    except Exception:
        pass

    ret_tab.sort(key=lambda entry: (entry[1] or entry[0]).lower())
    return ret_tab


def scan_rfcomm_port(mac: str, port: int) -> str:
    _sock = bluez.btsocket()
    sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM, _sock)
    try:
        sock.connect((mac, port))
        sock.close()
        return _('usable')
    except Exception:
        return _('closed or denied')
