"""Module entrypoint for python -m agent_system.cli."""

from __future__ import annotations

import sys
from agent_system.cli.main import main

if __name__ == "__main__":
    sys.exit(main())
