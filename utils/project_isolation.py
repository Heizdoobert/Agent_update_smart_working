# utils/project_isolation.py
"""Utility helpers for project‑level isolation.
Provides path resolution for the per‑project SQLite database and the
Milvus Lite namespace/collection name.
"""
from pathlib import Path
from typing import Tuple

BASE_PROJECT_DIR = Path("~/.agent_system/projects").expanduser()

def get_project_paths(project_id: str) -> Tuple[Path, str]:
    """Return the absolute path to the SQLite store and the Milvus namespace.

    Args:
        project_id: Immutable identifier for the project (e.g. UUID or repo slug).

    Returns:
        (sqlite_path, milvus_namespace)
    """
    sqlite_path = BASE_PROJECT_DIR / project_id / "store.db"
    milvus_namespace = f"insights_{project_id}"
    # Ensure the directory exists.
    sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    return sqlite_path, milvus_namespace
