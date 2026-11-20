#!/usr/bin/env python3
"""
In‑process LRU cache for Milvus Lite insight vectors.
Keeps a limited number of recent vectors in RAM for fast retrieval.
Thread‑safe via a global lock.
"""

import threading
import logging
from collections import OrderedDict
from typing import Any, Dict, List, Tuple

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

# Global lock for all cache operations
_cache_lock = threading.Lock()


class VectorCache:
    """Thread‑safe LRU cache mapping insight_id -> (vector, payload)."""

    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self._store: OrderedDict[str, Tuple[List[float], Dict[str, Any]]] = OrderedDict()

    def _evict_if_needed(self):
        while len(self._store) > self.max_size:
            evicted_id, _ = self._store.popitem(last=False)
            log.debug(f"VectorCache evicted insight_id={evicted_id}")

    def add(self, insight_id: str, vector: List[float], payload: Dict[str, Any]):
        """Add or update a cached entry and mark it as most‑recent."""
        with _cache_lock:
            self._store[insight_id] = (vector, payload)
            self._store.move_to_end(insight_id, last=True)
            self._evict_if_needed()

    def get(self, insight_id: str) -> Tuple[List[float], Dict[str, Any]] | None:
        """Return (vector, payload) if present and promote to most‑recent."""
        with _cache_lock:
            entry = self._store.get(insight_id)
            if entry:
                self._store.move_to_end(insight_id, last=True)
            return entry

    def remove_by_insight_id(self, insight_id: str) -> bool:
        """Delete an entry from the cache. Returns True if removed."""
        with _cache_lock:
            if insight_id in self._store:
                del self._store[insight_id]
                return True
            return False

    def items(self):
        """Return a list of (insight_id, (vector, payload)) pairs.
        Provides compatibility with the pre‑refactor API that expected
        ``vector_cache.items()`` to be iterable.
        """
        with _cache_lock:
            return list(self._store.items())

    def get_by_status(self, status: str, limit: int) -> List[Dict[str, Any]]:
        """Return up to *limit* cached entries having the given *status*.
        Iterates over the underlying OrderedDict while holding the lock.
        """
        with _cache_lock:
            results: List[Dict[str, Any]] = []
            for iid, (vec, payload) in self._store.items():
                if payload.get("status") == status:
                    results.append({"insight_id": iid, "vector": vec, "content": payload.get("content", "")})
                    if len(results) >= limit:
                        break
            return results

    def set_max_size(self, max_size: int):
        """Adjust the cache capacity and evict if necessary."""
        with _cache_lock:
            self.max_size = max_size
            self._evict_if_needed()

    def clear(self):
        """Clear all entries from the cache."""
        with _cache_lock:
            self._store.clear()

# Singleton instance used throughout the package
vector_cache = VectorCache()
