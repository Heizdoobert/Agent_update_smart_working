#!/usr/bin/env python3
"""
Agent Hooks Module
------------------
Provides hook functions that the agent can call automatically
before and after each task.
"""

import os
import time
import logging
import tempfile
import threading
from pathlib import Path
from typing import List, Dict, Any
import datetime

from ._client import get_client
from .cache import vector_cache
from .scripts.memory_reflection import dummy_embed, load_insights

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

lock = threading.Lock()


def _is_safe_path(file_path: str) -> bool:
    """Validate that the insight file path resides within safe designated directories."""
    try:
        resolved = Path(file_path).resolve()
        allowed_dirs = [
            Path(tempfile.gettempdir()).resolve(),
            Path("/tmp").resolve(),
            Path.cwd().resolve(),
        ]
        return any(
            str(resolved) == str(d) or str(resolved).startswith(str(d) + os.sep)
            for d in allowed_dirs
        )
    except Exception:
        return False


def pre_task_hook(task_id: str, user_id: str, query: str, k: int = 5) -> List[Dict[str, Any]]:
    """Retrieve top‑k past insights relevant to the upcoming task for a specific user.

    Args:
        task_id: Identifier of the current task (for logging only).
        user_id: Identifier of the user invoking the task (tenant isolation).
        query: Natural‑language description of the task.
        k: Number of insights to retrieve.
    Returns:
        List of insight dictionaries containing ``content``, ``user_id`` and ``task_id``.
    """
    try:
        client, coll, _ = get_client()
        with lock:
            results = client.query(coll, "", output_fields=["content", "user_id", "task_id", "source_pointer"], limit=1000)

        filtered = []
        query_lower = (query or "").lower()
        query_tokens = [t for t in query_lower.split() if t]
        for r in results:
            # Ensure tenant isolation: only retrieve insights belonging to user_id
            if user_id and r.get("user_id") and r.get("user_id") != user_id:
                continue

            content = (r.get("content") or "").lower()
            if not query_tokens:
                match = True
            else:
                match = any(tok in content for tok in query_tokens)
            if match:
                filtered.append({
                    "content": r.get("content", ""),
                    "user_id": r.get("user_id", ""),
                    "task_id": r.get("task_id", ""),
                    "source_pointer": r.get("source_pointer", {}),
                })
        filtered = filtered[:k]
        log.info(f"[pre_task_hook] Retrieved {len(filtered)} insights for task {task_id} (user={user_id})")
        return filtered
    except Exception as e:
        log.error(f"[pre_task_hook] Retrieval failed for task {task_id}: {e}")
        return []


def post_task_hook(task_id: str, user_id: str, insight_path: str) -> None:
    """Store newly generated insights after a task finishes.

    The function reads the JSON insight file produced by the agent,
    embeds each insight, determines its lifecycle status, upserts it into
    Milvus Lite, and cleans up the temporary file only on success.
    """
    if not insight_path or not Path(insight_path).exists():
        log.warning(f"[post_task_hook] Insight file missing for task {task_id}")
        return

    # Security check: prevent arbitrary file read/deletion via path traversal
    if not _is_safe_path(insight_path):
        log.error(f"[post_task_hook] Rejected insight file {insight_path}: path outside allowed temp directories")
        return

    insights = load_insights(insight_path)
    if not insights:
        log.info(f"[post_task_hook] No insights to store for task {task_id}")
        return

    client, collection_name, dim = get_client()
    vectors = []
    payload = []
    for item in insights:
        txt = item.get("insight") or item.get("text") or ""
        if not txt.strip():
            continue
        typ = item.get("type", "generic")
        vec = dummy_embed(txt, dim)
        vectors.append(vec)

        # Determine status: respect explicit status first, then priority, then timestamp
        status = item.get("status")
        timestamp = item.get("timestamp")
        if not timestamp:
            timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()

        if not status:
            priority = str(item.get("priority", "")).strip().lower()
            if priority == "high":
                status = "longterm"
            elif timestamp:
                try:
                    if isinstance(timestamp, (int, float)):
                        ts = int(timestamp)
                    else:
                        try:
                            ts = int(datetime.datetime.fromisoformat(str(timestamp).replace('Z', '+00:00')).timestamp())
                        except Exception:
                            ts = int(float(timestamp))
                    # If older than 7 days -> longterm, else shortterm
                    if ts < int(time.time()) - 7 * 24 * 3600:
                        status = "longterm"
                    else:
                        status = "shortterm"
                except (ValueError, TypeError):
                    status = "shortterm"
            else:
                status = "shortterm"

        source_pointer = item.get("source_pointer") or {
            "storage_uri": "",
            "file_path": str(insight_path),
            "chunk_id": "",
            "line_range": [],
            "git_commit_sha": os.getenv("GIT_COMMIT_SHA", "HEAD"),
        }

        payload.append({
            "user_id": user_id,
            "task_id": task_id,
            "timestamp": timestamp,
            "insight_type": typ,
            "source": "agent_hook",
            "content": txt,
            "status": status,
            "source_pointer": source_pointer,
        })

    if not payload:
        log.info(f"[post_task_hook] All insights were empty for task {task_id}")
        return

    data = []
    for p, v in zip(payload, vectors):
        entry = p.copy()
        entry["vector"] = v
        data.append(entry)

    # Insert under lock and only delete file on success
    try:
        with lock:
            client.insert(collection_name=collection_name, data=data)
            client.flush(collection_name=collection_name)
        log.info(f"Inserted {len(payload)} insights into Milvus collection {collection_name}.")

        # Clean‑up temporary file only after successful write
        Path(insight_path).unlink(missing_ok=True)
        log.info(f"[post_task_hook] Removed insight file {insight_path}")
    except Exception as e:
        log.error(f"Milvus insertion failed for task {task_id}: {e}")
        return
