#!/usr/bin/env python3
# Thin compatibility launcher for the Qt6 package.
# Prefer: python3 -m blueproximity
import os
import sys

_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from blueproximity.__main__ import main

if __name__ == '__main__':
    main()
