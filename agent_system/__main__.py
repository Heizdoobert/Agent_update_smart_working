"""Top-level package entrypoint for python -m agent_system."""

from __future__ import annotations

import sys
from agent_system.cli.main import main

if __name__ == "__main__":
    sys.exit(main())
