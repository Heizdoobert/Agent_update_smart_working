"""Configuration for CLI agents.

Defines default model identifiers for each supported agent and provides a helper
function to retrieve the appropriate model considering the optional environment
variable ``SMALL_MODEL``.
"""

import os

# Default (full‑size) model identifiers – these correspond to the official model
# names used by each provider.  They can be overridden by setting the environment
# variable ``SMALL_MODEL=true`` which forces the use of a lightweight variant.
DEFAULT_MODELS = {
    "claude": "claude-2.0",
    "opencode": "gpt-3.5-turbo",
    "hermes": "openhermes-7b",
    "antigravity": "flash_lite",
}

# Mapping to the lightweight versions of the above models.  The names are chosen
# to be compatible with the respective SDKs; they can be adjusted if the
# provider uses a different naming scheme.
LITE_MODELS = {
    "claude": "claude-2.0-lite",
    "opencode": "gpt-3.5-turbo-lite",
    "hermes": "openhermes-7b-lite",
    "antigravity": "flash",
}

def get_model(agent_name: str) -> str:
    """Return the model identifier for *agent_name*.

    If the environment variable ``SMALL_MODEL`` is set to a truthy value (e.g.
    ``"1"``, ``"true"``), the function returns the lightweight variant; otherwise
    it returns the default full‑size model.
    """
    name = agent_name.lower()
    if name not in DEFAULT_MODELS:
        raise ValueError(f"Unsupported agent: {agent_name!r}")
    use_small = os.getenv("SMALL_MODEL", "").lower() in {"1", "true", "yes"}
    return LITE_MODELS[name] if use_small else DEFAULT_MODELS[name]
