# memory_layer/hardening.py
"""Hardening utilities for the memory layer.
Implements a Two‑Phase Commit (2PC) write preparation step that stores a
WAL entry with a deterministic BLAKE3 UID. The entry is written to a configurable
path (default via AGENT_WAL_PATH env) and marked ``PREPARED``.
"""

import json
import os
import hashlib
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

# Resolve WAL path dynamically; fallback to default location.
WAL_PATH = Path(os.getenv("AGENT_WAL_PATH", "/home/agent/.gemini/antigravity-cli/.agent/memory_wal.jsonl"))

# Ensure the directory exists only when needed (lazy creation).

def _ensure_wal_dir() -> None:
    WAL_PATH.parent.mkdir(parents=True, exist_ok=True)

# Try to import blake3 once; fallback to hashlib.blake2b.
try:
    import blake3  # type: ignore
    _has_blake3 = True
except Exception:
    _has_blake3 = False


def _blake3_uid(project_id: str, task_id: str, insight_type: str, insight_text: str) -> str:
    """Compute deterministic UID using a delimiter to avoid collisions.
    Delimiter ``::`` separates fields, ensuring unique byte sequences.
    """
    data = f"{project_id}::{task_id}::{insight_type}::{insight_text}".encode("utf-8")
    if _has_blake3:
        return blake3.blake3(data).hexdigest()
    # Fallback to blake2b (standard library) – still deterministic.
    return hashlib.blake2b(data, digest_size=32).hexdigest()


def _validate_id(id_: str) -> str:
    """Validate identifiers (project_id, task_id) contain only safe characters.
    Allows alphanumerics, underscore and hyphen.
    """
    import re
    if not re.fullmatch(r"[A-Za-z0-9_-]+", id_):
        raise ValueError(f"Invalid identifier '{id_}'. Must match [A-Za-z0-9_-]+")
    return id_


def prepare_write(project_id: str, task_id: str, insight_type: str, insight_text: str, metadata: Dict) -> str:
    """Create a WAL entry and return its UID.
    The entry is stored with status ``PREPARED`` and will later be committed
    by ``memory_layer.commit.commit_write``.
    """
    # Validate ids to prevent path traversal or injection.
    _validate_id(project_id)
    _validate_id(task_id)

    if len(insight_text) > 2048:
        raise ValueError("insight_text exceeds safe size (2048 bytes)")

    uid = _blake3_uid(project_id, task_id, insight_type, insight_text)
    entry = {
        "uid": uid,
        "project_id": project_id,
        "task_id": task_id,
        "insight_type": insight_type,
        "insight_text": insight_text,
        "metadata": metadata,
        "status": "PREPARED",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    _ensure_wal_dir()
    with WAL_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return uid

"""Hardening utilities for the memory layer.
Implements a Two‑Phase Commit (2PC) write preparation step that stores a
WAL entry with a deterministic BLAKE3 UID. The entry is written to
`.agent/memory_wal.jsonl` and marked ``PREPARED``.
"""
import json
import os
import hashlib
from pathlib import Path
from datetime import datetime

WAL_PATH = Path("/home/agent/.gemini/antigravity-cli/.agent/memory_wal.jsonl")
WAL_PATH.parent.mkdir(parents=True, exist_ok=True)

def _blake3_uid(project_id: str, task_id: str, insight_type: str, insight_text: str) -> str:
    """Compute deterministic UID using BLAKE3 (fallback to hashlib.blake2b if unavailable)."""
    try:
        import blake3
        data = f"{project_id}{task_id}{insight_type}{insight_text}".encode("utf-8")
        return blake3.blake3(data).hexdigest()
    except Exception:
        # Fallback to blake2b (standard library) – still deterministic.
        data = f"{project_id}{task_id}{insight_type}{insight_text}".encode("utf-8")
        return hashlib.blake2b(data, digest_size=32).hexdigest()

def prepare_write(project_id: str, task_id: str, insight_type: str, insight_text: str, metadata: dict) -> str:
    """Create a WAL entry and return its UID.
    The entry is stored with status ``PREPARED`` and will later be committed
    by ``memory_layer.commit.commit_write``.
    """
    uid = _blake3_uid(project_id, task_id, insight_type, insight_text)
    entry = {
        "uid": uid,
        "project_id": project_id,
        "task_id": task_id,
        "insight_type": insight_type,
        "insight_text": insight_text,
        "metadata": metadata,
        "status": "PREPARED",
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    # Append as a JSON line.
    with WAL_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return uid
