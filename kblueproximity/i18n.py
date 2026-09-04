"""gettext helpers."""
from __future__ import annotations

import gettext
import locale
import os

from kblueproximity import APP_NAME
from kblueproximity.paths import DIST_PATH


def _(message: str) -> str:
    return gettext.gettext(message)


def _language_candidates() -> list[str]:
    """Build language preference list from the environment / locale."""
    langs: list[str] = []

    def add(code: str | None) -> None:
        if not code:
            return
        code = code.replace('-', '_')
        if code not in langs:
            langs.append(code)
        # Also try the short language code (it_IT -> it), matching LANG/<code>/.
        if '_' in code:
            short = code.split('_', 1)[0]
            if short and short not in langs:
                langs.append(short)

    language = os.environ.get('LANGUAGE')
    if language:
        for part in language.split(':'):
            add(part.strip() or None)

    for key in ('LC_ALL', 'LC_MESSAGES', 'LANG'):
        value = os.environ.get(key)
        if value:
            add(value.split('.')[0].split('@')[0])
            break

    try:
        loc = locale.setlocale(locale.LC_MESSAGES, '')
        if loc and loc not in ('C', 'POSIX'):
            add(loc.split('.')[0].split('@')[0])
    except locale.Error:
        pass

    try:
        lc, _enc = locale.getlocale(locale.LC_MESSAGES)
        add(lc)
    except Exception:
        pass

    # Last-resort English catalog if present (untranslated msgids stay English anyway).
    add('en')
    return langs


def setup_i18n() -> None:
    local_path = os.path.join(DIST_PATH, 'LANG')
    langs = _language_candidates()
    gettext.bindtextdomain(APP_NAME, local_path)
    gettext.textdomain(APP_NAME)
    translation = gettext.translation(
        APP_NAME, local_path, languages=langs, fallback=True)
    translation.install()
