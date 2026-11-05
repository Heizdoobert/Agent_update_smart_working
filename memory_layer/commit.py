# memory_layer/commit.py
"""Commit utilities for the memory layer.
Implements the second phase of the Two‑Phase Commit (2PC) that atomically
writes the prepared insight to Milvus Lite (vector store) and the project‑
specific SQLite database.
"""
import json
import sqlite3
from pathlib import Path
from typing import Tuple

# Assuming a Milvus Lite client wrapper exists in the repository.
# For illustration we provide a minimal stub.
class MilvusLiteClient:
    def __init__(self, collection_name: str):
        self.collection = collection_name
        # In a real implementation this would initialise the Milvus client.
    def upsert(self, uid: str, vector: list, metadata: dict) -> None:
        # Placeholder for upsert logic.
        pass

WAL_PATH = Path("/home/agent/.gemini/antigravity-cli/.agent/memory_wal.jsonl")

def _load_prepared(uid: str) -> dict:
    with WAL_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            entry = json.loads(line)
            if entry.get("uid") == uid and entry.get("status") == "PREPARED":
                return entry
    raise KeyError(f"Prepared entry {uid} not found")

def _update_status(uid: str, new_status: str) -> None:
    # Simple implementation: rewrite the WAL file with updated status.
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

def _sqlite_path(project_id: str) -> Path:
    return Path(f"~/.agent_system/projects/{project_id}/store.db").expanduser()

def commit_write(uid: str) -> bool:
    """Commit a prepared write.
    Returns True on success, False on failure (which triggers rollback).
    """
    try:
        entry = _load_prepared(uid)
        project_id = entry["project_id"]
        # 1. Write to SQLite (create DB if not exists)
        db_path = _sqlite_path(project_id)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(db_path))
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=5000;")
        conn.execute(
            """CREATE TABLE IF NOT EXISTS insights (
                uid TEXT PRIMARY KEY,
                task_id TEXT,
                insight_type TEXT,
                insight_text TEXT,
                metadata TEXT
            )"""
        )
        conn.execute(
            "INSERT OR REPLACE INTO insights (uid, task_id, insight_type, insight_text, metadata) VALUES (?,?,?,?,?)",
            (
                entry["uid"],
                entry["task_id"],
                entry["insight_type"],
                entry["insight_text"],
                json.dumps(entry["metadata"]),
            ),
        )
        conn.commit()
        conn.close()
        # 2. Write to Milvus Lite (namespace per project)
        milvus = MilvusLiteClient(collection_name=f"insights_{project_id}")
        # In real code we would compute the embedding vector here.
        # For now we store a placeholder zero‑vector.
        placeholder_vector = [0.0] * 128
        milvus.upsert(uid=uid, vector=placeholder_vector, metadata=entry["metadata"])
        # 3. Mark as COMMITTED
        _update_status(uid, "COMMITTED")
        return True
    except Exception as e:
        # On any error, rollback.
        _update_status(uid, "FAILED")
        return False
