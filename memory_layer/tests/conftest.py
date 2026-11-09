import sys
from pathlib import Path

# Ensure pymilvus and dependencies from memory_layer venv are discoverable
_venv_site = Path(__file__).resolve().parent.parent / "venv" / "lib" / "python3.11" / "site-packages"
if _venv_site.exists() and str(_venv_site) not in sys.path:
    sys.path.insert(0, str(_venv_site))
