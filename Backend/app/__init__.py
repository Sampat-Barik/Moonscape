"""Moonscape Backend - Lunar South Pole Landing-Site Analysis Platform."""

import sys
from pathlib import Path

# Ensure Backend directory is in sys.path so app.* imports always resolve consistently
_backend_dir = Path(__file__).resolve().parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

__version__ = "1.0.0"
