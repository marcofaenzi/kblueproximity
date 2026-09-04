"""Entry point: python3 -m kblueproximity"""
from __future__ import annotations

import signal
import sys


def main():
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    from kblueproximity.ui.app import run_app
    raise SystemExit(run_app())


if __name__ == '__main__':
    main()
