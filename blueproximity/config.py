"""ConfigObj specs, defaults, and config loading."""
from __future__ import annotations

import os
import sys

from blueproximity.i18n import _
from blueproximity.paths import conf_dir

try:
    from configobj import ConfigObj
    from validate import Validator
except ImportError:
    print(_("The program cannot import the module ConfigObj or Validator."))
    print(_("Please make sure the ConfigObject package for python is installed."))
    print(_("e.g. with Ubuntu Linux, type"))
    print(_(" sudo apt-get install python3-configobj"))
    sys.exit(1)


def get_default_commands():
    """Return lock/unlock/proximity shell commands suited to the current desktop."""
    desktop = os.environ.get('XDG_CURRENT_DESKTOP', '').upper()
    if 'KDE' in desktop:
        return (
            'loginctl lock-session',
            'loginctl unlock-session',
            'qdbus6 org.freedesktop.ScreenSaver /ScreenSaver SimulateUserActivity',
        )
    return (
        'loginctl lock-session',
        'loginctl unlock-session',
        '',
    )


def _conf_string_default(value: str) -> str:
    return "string(default=''" + value.replace("'", "''") + "'')"


_default_lock, _default_unlock, _default_proximity = get_default_commands()
_default_log_file = os.path.join(conf_dir(), 'blueproximity.log')

CONF_SPECS = [
    'device_mac=string(max=17,default="")',
    'device_channel=integer(1,30,default=7)',
    'lock_distance=integer(0,127,default=7)',
    'lock_duration=integer(0,120,default=6)',
    'unlock_distance=integer(0,127,default=4)',
    'unlock_duration=integer(0,120,default=1)',
    'lock_command=' + _conf_string_default(_default_lock),
    'unlock_command=' + _conf_string_default(_default_unlock),
    'proximity_command=' + _conf_string_default(_default_proximity),
    'proximity_interval=integer(5,600,default=60)',
    'scan_period=integer(1,60,default=1)',
    'buffer_size=integer(1,255,default=1)',
    'debug_log=boolean(default=True)',
    'log_to_syslog=boolean(default=True)',
    "log_syslog_facility=string(default=''local7'')",
    'log_to_file=boolean(default=True)',
    'log_filelog_filename=' + _conf_string_default(_default_log_file),
]

LOCK_COMMAND_SUGGESTIONS = [
    'loginctl lock-session',
    'qdbus6 org.freedesktop.ScreenSaver /ScreenSaver Lock',
]
UNLOCK_COMMAND_SUGGESTIONS = [
    'loginctl unlock-session',
]
PROXIMITY_COMMAND_SUGGESTIONS = [
    'qdbus6 org.freedesktop.ScreenSaver /ScreenSaver SimulateUserActivity',
    'xset dpms force on',
]
SYSLOG_FACILITIES = [
    'local0', 'local1', 'local2', 'local3',
    'local4', 'local5', 'local6', 'local7', 'user',
]


def ensure_conf_dir() -> str:
    path = conf_dir()
    try:
        os.mkdir(path)
        print(_("Creating new config directory '%s'.") % path)
        try:
            os.rename(
                os.path.join(os.getenv('HOME', ''), '.blueproximityrc'),
                os.path.join(path, _('standard') + '.conf'),
            )
            print(_("Moved old configuration to the new config directory."))
        except OSError:
            pass
    except FileExistsError:
        pass
    except OSError:
        pass
    return path


def load_configs():
    """Load all *.conf files. Returns (configs, is_new) where configs is
    a list of [name, ConfigObj] (Proximity thread appended later)."""
    directory = ensure_conf_dir()
    vdt = Validator()
    configs = []
    new_config = True

    for filename in os.listdir(directory):
        if not filename.endswith('.conf'):
            continue
        if filename == 'behavior.conf':
            continue
        try:
            config = ConfigObj(
                os.path.join(directory, filename),
                {'create_empty': False, 'file_error': True, 'configspec': CONF_SPECS},
            )
            config.validate(vdt, copy=True)
            config.write()
            configs.append([filename[:-5], config])
            new_config = False
            print(_("Using config file '%s'.") % filename)
        except Exception:
            print(_("'%s' is not a valid config file.") % filename)

    if new_config:
        config = ConfigObj(
            os.path.join(directory, _('standard') + '.conf'),
            {'create_empty': True, 'file_error': False, 'configspec': CONF_SPECS},
        )
        config['device_mac'] = ''
        config.validate(vdt, copy=True)
        config.write()
        configs.append([_('standard'), config])
        print(_("Creating new configuration."))
        print(_("Using config file '%s'.") % _('standard'))

    configs.sort()
    return configs, new_config
