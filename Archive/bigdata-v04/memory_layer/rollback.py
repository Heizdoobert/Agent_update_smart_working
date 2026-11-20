# memory_layer/rollback.py
"""Rollback utilities for the memory layer.
Implements the compensation step of the Two‑Phase Commit (2PC) that
removes a prepared entry that failed to commit.
"""
import json
from pathlib import Path

WAL_PATH = Path("/home/agent/.gemini/antigravity-cli/.agent/memory_wal.jsonl")

def _update_status(uid: str, new_status: str) -> None:
    lines = []
    with WAL_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            entry = json.loads(line)
            if entry.get("uid") == uid:
                entry["status"] = new_status
            lines.append(entry)
    with WAL_PATH.open("w", encoding="utf-8") as f:
        for entry in lines:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

def rollback_write(uid: str) -> bool:
    """Mark the WAL entry as TOMBSTONE. In a real system this would also
    delete the vector from Milvus and the row from SQLite.
    """
    try:
        _update_status(uid, "TOMBSTONE")
        return True
    except Exception:
        return False
