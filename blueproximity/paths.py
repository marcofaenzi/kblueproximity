"""Resolve install and resource paths."""
from __future__ import annotations

import os

_PKG_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_PKG_DIR)


def resolve_dist_path() -> str:
    """Return directory containing icons, LANG, and shared assets."""
    candidates = [
        os.path.join(_PKG_DIR, 'resources'),
        _REPO_ROOT,
        '/usr/share/blueproximity',
        os.getcwd(),
    ]
    for path in candidates:
        if os.path.isfile(os.path.join(path, 'blueproximity_base.svg')):
            return path if path.endswith(os.sep) else path + os.sep
    return _REPO_ROOT if _REPO_ROOT.endswith(os.sep) else _REPO_ROOT + os.sep


DIST_PATH = resolve_dist_path()

ICON_BASE = 'blueproximity_base.svg'
ICON_ATT = 'blueproximity_attention.svg'
ICON_AWAY = 'blueproximity_nocon.svg'
ICON_ERROR = 'blueproximity_error.svg'
ICON_PAUSE = 'blueproximity_pause.svg'


def icon_path(name: str) -> str:
    return os.path.join(DIST_PATH, name)


def conf_dir() -> str:
    return os.path.join(os.getenv('HOME', ''), '.blueproximity')
