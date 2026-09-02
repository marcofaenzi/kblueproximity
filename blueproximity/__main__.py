"""Entry point: python3 -m blueproximity"""
from __future__ import annotations

import signal
import sys


def main():
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    from blueproximity.ui.app import run_app
    raise SystemExit(run_app())


if __name__ == '__main__':
    main()
