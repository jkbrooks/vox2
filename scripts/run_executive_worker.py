from __future__ import annotations

import os
import sys

# Ensure repository root is on sys.path when running from scripts/
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, os.pardir))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from executive_worker.cli import main


if __name__ == "__main__":
    raise SystemExit(main())


