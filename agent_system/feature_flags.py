# Feature flag utilities for Agent System
"""Utility module to load and query feature flags.

The flags are read from a JSON file whose location can be overridden by the
environment variable ``FEATURE_FLAGS_PATH``.  By default the file is
``~/.gemini/config/feature_flags.json`` which is a user‑specific location that
is not checked into version control.

Example ``feature_flags.json``:
```json
{
  "agent_system_installer": false,
  "new_api_endpoint": true
}
```

The module loads the flags on import so they are available globally via
``is_enabled`` or ``get_feature_flags``.
"""

import json
import os
from typing import Dict

# Internal storage for flags
_FEATURE_FLAGS: Dict[str, bool] = {}


def _load_feature_flags() -> None:
    """Load flags from the JSON file into ``_FEATURE_FLAGS``.

    The path is resolved in the following order:
    1. ``FEATURE_FLAGS_PATH`` environment variable.
    2. ``~/.gemini/config/feature_flags.json`` (expanded to the user home).
    If the file does not exist or cannot be parsed, the function silently
    leaves the flag dictionary empty.
    """
    path = os.getenv(
        "FEATURE_FLAGS_PATH",
        os.path.expanduser("~/.gemini/config/feature_flags.json"),
    )
    try:
        with open(path, "r", encoding="utf-8") as fp:
            data = json.load(fp)
        if isinstance(data, dict):
            for key, value in data.items():
                _FEATURE_FLAGS[key] = bool(value)
    except FileNotFoundError:
        pass
    except Exception as exc:
        raise RuntimeError(f"Failed to load feature flags from {path}: {exc}")

# Load at import time
_load_feature_flags()


def is_enabled(flag: str) -> bool:
    """Return ``True`` if ``flag`` is enabled, ``False`` otherwise."""
    return _FEATURE_FLAGS.get(flag, False)


def get_feature_flags() -> Dict[str, bool]:
    """Return a copy of the current flag dictionary."""
    return dict(_FEATURE_FLAGS)
