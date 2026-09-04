"""Global behavior settings (autostart, tray) — not per-device."""
from __future__ import annotations

import os
import shutil

from kblueproximity.config import ConfigObj, Validator
from kblueproximity.paths import ICON_BASE, conf_dir, icon_path

BEHAVIOR_SPECS = [
    'autostart=boolean(default=False)',
    'hide_systray=boolean(default=False)',
    'start_paused=boolean(default=False)',
]

AUTOSTART_FILENAME = 'kblueproximity.desktop'


def autostart_dir() -> str:
    return os.path.join(os.getenv('HOME', ''), '.config', 'autostart')


def autostart_path() -> str:
    return os.path.join(autostart_dir(), AUTOSTART_FILENAME)


def behavior_path() -> str:
    return os.path.join(conf_dir(), 'behavior.conf')


def autostart_exec() -> str:
    if os.path.isfile('/usr/bin/kblueproximity'):
        return '/usr/bin/kblueproximity'
    return 'python3 -m kblueproximity'


def is_autostart_enabled() -> bool:
    path = autostart_path()
    if not os.path.isfile(path):
        return False
    try:
        with open(path, encoding='utf-8') as handle:
            for line in handle:
                if line.strip().lower() == 'hidden=true':
                    return False
    except OSError:
        return False
    return True


def set_autostart_enabled(enabled: bool) -> None:
    path = autostart_path()
    if not enabled:
        try:
            os.remove(path)
        except FileNotFoundError:
            pass
        return
    os.makedirs(autostart_dir(), exist_ok=True)
    icon = icon_path(ICON_BASE)
    contents = (
        '[Desktop Entry]\n'
        'Type=Application\n'
        'Version=1.0\n'
        'Name=KBlueProximity\n'
        'Comment=Bluetooth proximity lock for the desktop\n'
        f'Exec={autostart_exec()}\n'
        f'Icon={icon}\n'
        'Terminal=false\n'
        'Categories=Utility;Security;\n'
        'StartupNotify=false\n'
        'X-GNOME-Autostart-enabled=true\n'
        'X-KDE-autostart-after=panel\n'
        'Hidden=false\n'
    )
    with open(path, 'w', encoding='utf-8') as handle:
        handle.write(contents)
    try:
        shutil.copymode('/usr/share/applications/kblueproximity.desktop', path)
    except OSError:
        pass


def load_behavior():
    os.makedirs(conf_dir(), exist_ok=True)
    config = ConfigObj(
        behavior_path(),
        {
            'create_empty': True,
            'file_error': False,
            'configspec': BEHAVIOR_SPECS,
        },
    )
    config.validate(Validator(), copy=True)
    config['autostart'] = is_autostart_enabled()
    return config


def save_behavior(config) -> None:
    set_autostart_enabled(bool(config.get('autostart')))
    config['autostart'] = is_autostart_enabled()
    config.write()
