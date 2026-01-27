"""Conftest module."""

import sys
from pathlib import Path

# Add vibeshare/src to sys.path to resolve imports in tests
vibeshare_src = Path(__file__).parent.parent / "src"
if str(vibeshare_src) not in sys.path:
    sys.path.insert(0, str(vibeshare_src))
