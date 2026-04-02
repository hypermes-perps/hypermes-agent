"""Shared setup for quoting-engine-powered strategies.

Adds the quoting_engine package paths to sys.path so it is importable
without pip install.
"""
from __future__ import annotations

import os
import sys

_QE_PARENT = os.path.expanduser("~/Tee-work-")
_QE_ROOT = os.path.join(_QE_PARENT, "quoting_engine")

for p in [_QE_PARENT, _QE_ROOT]:
    if p not in sys.path:
        sys.path.insert(0, p)
