"""
API utilities for managing insight lifecycle and cache interactions.
"""

import re
import logging
from typing import List, Dict, Any

from ._client import get_client
from .cache import vector_cache
import blake3

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

_SAFE_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_\-\.]+$")


def compute_blake3_uid(tenant_id: str, task_id: str, insight_type: str, content: str) -> str:
    """Generate a deterministic content-addressable UID for idempotent upsert."""
    norm = content.strip().lower()
    raw = f"{tenant_id}::{task_id}::{insight_type}::{norm}".encode("utf-8")
    return blake3.blake3(raw).hexdigest()[:16]


def _validate_id(identifier: str, name: str = "id") -> str:
    """Validate that identifier contains only alphanumeric, hyphen, underscore, and dot characters."""
    val = str(identifier).strip()
    if not val or not _SAFE_ID_PATTERN.match(val):
        raise ValueError(f"Invalid {name}: {identifier!r} contains disallowed characters")
    return val


def mark_insight(insight_id: str, status: str) -> bool:
    """Update the lifecycle status of an insight.

    Args:
        insight_id: The primary key (auto_id) of the insight in Milvus.
        status: New status flag (e.g., 'shortterm', 'longterm', 'trash', 'kb_*').
    Returns:
        True if the update succeeded, False otherwise.
    """
    safe_id = _validate_id(insight_id, "insight_id")
    safe_status = _validate_id(status, "status")

    client, coll, _ = get_client()
    try:
        # Retrieve existing payload with all scalar fields and vector embedding
        pk_filter = f"id == {safe_id}" if str(safe_id).isdigit() else f"id == '{safe_id}'"
        results = client.query(
            collection_name=coll,
            filter=pk_filter,
            output_fields=["*"],
            limit=1,
        )
        if not results:
            results = client.query(
                collection_name=coll,
                filter=f"insight_id == {safe_id}" if str(safe_id).isdigit() else f"insight_id == '{safe_id}'",
                output_fields=["*"],
                limit=1,
            )
        if not results:
            log.warning(f"mark_insight: insight_id {safe_id} not found")
            return False
        existing = results[0]

        # Prepare updated payload before deleting old record to avoid data loss
        existing["status"] = safe_status
        vector = existing.pop("vector", None)
        new_data = {**existing, "vector": vector} if vector is not None else existing

        # Remove old entry and re-insert updated entry
        del_filter = pk_filter if "id" in existing else (f"insight_id == {safe_id}" if str(safe_id).isdigit() else f"insight_id == '{safe_id}'")
        client.delete(collection_name=coll, filter=del_filter)
        client.insert(collection_name=coll, data=[new_data])
        client.flush(collection_name=coll)

        # Invalidate cache if present
        vector_cache.remove_by_insight_id(safe_id)
        return True
    except Exception as e:
        log.error(f"mark_insight failed for {safe_id}: {e}")
        return False


def set_status_for_task(task_id: str, new_status: str) -> int:
    """Update the status of all insights belonging to a given task.

    Milvus Lite does not support in‑place field updates, so we retrieve the
    matching rows, delete them, and re‑insert with the updated ``status``.
    Returns the number of updated entries.
    """
    safe_task = _validate_id(task_id, "task_id")
    safe_status = _validate_id(new_status, "status")

    client, coll, _ = get_client()
    try:
        # Fetch all fields for the task
        results = client.query(
            collection_name=coll,
            filter=f"task_id == '{safe_task}'",
            output_fields=["*"],
            limit=1000,
        )
        if not results:
            log.info(f"set_status_for_task: no entries for task {safe_task}")
            return 0

        # Prepare all updated items prior to deletion to minimize failure window
        updated = []
        for r in results:
            vector = r.pop("vector", None)
            r["status"] = safe_status
            if vector is not None:
                updated.append({**r, "vector": vector})
            else:
                updated.append(r)

        # Delete existing entries and re-insert updated batch
        client.delete(collection_name=coll, filter=f"task_id == '{safe_task}'")
        client.insert(collection_name=coll, data=updated)
        client.flush(collection_name=coll)

        # Invalidate / update cache entries
        for r in updated:
            iid = r.get("insight_id") or r.get("id")
            if iid is not None:
                vector_cache.remove_by_insight_id(str(iid))

        log.info(f"set_status_for_task: updated {len(updated)} entries to status '{safe_status}' for task {safe_task}")
        return len(updated)
    except Exception as e:
        log.error(f"set_status_for_task failed for task {safe_task}: {e}")
        return 0


def get_ready_vectors(k: int = 10) -> List[Dict[str, Any]]:
    """Return up to *k* short‑term vectors ready for immediate use.

    Deduplicates results between LRU cache and persistent storage.

    Args:
        k: Maximum number of vectors to return.

    Returns:
        List of dictionaries containing ``insight_id``, ``vector``, ``content``, and ``task_id``.
    """
    if not isinstance(k, int) or k <= 0:
        raise ValueError(f"Parameter k must be a positive integer, got {k}")
    k = min(k, 500)  # safety upper bound

    # Attempt cache‑aside retrieval
    cached = [
        {
            "insight_id": str(iid),
            "vector": vec,
            "content": payload.get("content", ""),
            "task_id": payload.get("task_id", ""),
        }
        for iid, (vec, payload) in vector_cache.items()
        if payload.get("status") == "shortterm"
    ]
    if len(cached) >= k:
        return cached[:k]

    cached_ids = {item["insight_id"] for item in cached}
    need = k - len(cached)

    client, coll, _ = get_client()
    try:
        # Request slightly more than need to allow for excluding cached IDs
        fetch_limit = need + len(cached_ids)
        results = client.query(
            collection_name=coll,
            filter="status == 'shortterm'",
            output_fields=["insight_id", "vector", "content", "status", "task_id"],
            limit=fetch_limit,
        )

        milvus_items = []
        for r in results:
            iid = str(r.get("insight_id") or r.get("id") or "")
            # Deduplication: do not duplicate items already in cached
            if iid in cached_ids:
                continue

            try:
                vector_cache.add(iid, r.get("vector"), r)
            except Exception as err:
                log.warning(f"Failed to populate vector_cache for insight {iid}: {err}")

            milvus_items.append({
                "insight_id": iid,
                "vector": r.get("vector"),
                "content": r.get("content", ""),
                "task_id": r.get("task_id", ""),
            })
            cached_ids.add(iid)
            if len(milvus_items) >= need:
                break

        return (cached + milvus_items)[:k]
    except Exception as e:
        log.exception(f"get_ready_vectors error: {e}")
        return cached


def get_kb_vectors(k: int = 10) -> List[Dict[str, Any]]:
    """Retrieve vectors flagged as knowledge‑base entries (status starts with 'kb_')."""
    if not isinstance(k, int) or k <= 0:
        raise ValueError(f"Parameter k must be a positive integer, got {k}")
    k = min(k, 500)

    client, coll, _ = get_client()
    try:
        results = client.query(
            collection_name=coll,
            filter="status like 'kb_%'",
            output_fields=["insight_id", "vector", "content"],
            limit=k,
        )
        formatted = []
        for r in results:
            iid = str(r.get("insight_id") or r.get("id") or "")
            formatted.append({
                "insight_id": iid,
                "vector": r.get("vector"),
                "content": r.get("content", ""),
            })
        return formatted
    except Exception as e:
        log.error(f"get_kb_vectors error: {e}")
        return []


def purge_shortterm() -> int:
    """Delete all short‑term insights and clear them from cache.

    Returns the number of deleted entries.
    """
    client, coll, _ = get_client()
    try:
        res = client.delete(collection_name=coll, filter="status == 'shortterm'")
        deleted_count = 0
        if isinstance(res, dict):
            deleted_count = res.get("delete_count", 0)
        elif isinstance(res, list):
            deleted_count = len(res)

        cache_deleted = 0
        for insight_id, (_, payload) in list(vector_cache.items()):
            if payload.get("status") == "shortterm":
                vector_cache.remove_by_insight_id(insight_id)
                cache_deleted += 1

        total_deleted = max(deleted_count, cache_deleted, 0)
        log.info(f"purged {total_deleted} shortterm insights")
        return total_deleted
    except Exception as e:
        log.error(f"purge_shortterm error: {e}")
        return 0


# Knowledge‑base and trash management utilities

def mark_insight_as_kb(insight_id: str, kb_type: str) -> bool:
    """Mark an insight as a knowledge‑base entry.

    The status will be set to ``kb_<kb_type>`` (e.g., ``kb_faq``).
    Returns ``True`` on success.
    """
    safe_type = _validate_id(kb_type, "kb_type")
    status = f"kb_{safe_type}"
    return mark_insight(insight_id, status)


def mark_insight_as_trash(insight_id: str) -> bool:
    """Mark an insight as trash (to be purged later)."""
    return mark_insight(insight_id, "trash")


def purge_trash() -> int:
    """Delete all insights marked as ``trash``.

    Returns the number of deleted entries.
    """
    client, coll, _ = get_client()
    try:
        res = client.delete(collection_name=coll, filter="status == 'trash'")
        deleted_count = 0
        if isinstance(res, dict):
            deleted_count = res.get("delete_count", 0)
        elif isinstance(res, list):
            deleted_count = len(res)

        cache_deleted = 0
        for insight_id, (_, payload) in list(vector_cache.items()):
            if payload.get("status") == "trash":
                vector_cache.remove_by_insight_id(insight_id)
                cache_deleted += 1

        total_deleted = max(deleted_count, cache_deleted, 0)
        log.info(f"purged {total_deleted} trash insights")
        return total_deleted
    except Exception as e:
        log.error(f"purge_trash error: {e}")
        return 0
