"""gettext helpers."""
from __future__ import annotations

import gettext
import locale
import os

from blueproximity import APP_NAME
from blueproximity.paths import DIST_PATH


def _(message: str) -> str:
    return gettext.gettext(message)


def setup_i18n() -> None:
    local_path = os.path.join(DIST_PATH, 'LANG')
    langs = []
    lc, _enc = locale.getdefaultlocale()
    if lc:
        langs = [lc]
    language = os.environ.get('LANGUAGE')
    if language:
        langs += language.split(':')
    langs += ['en']
    gettext.bindtextdomain(APP_NAME, local_path)
    gettext.textdomain(APP_NAME)
    translation = gettext.translation(
        APP_NAME, local_path, languages=langs, fallback=True)
    translation.install()
