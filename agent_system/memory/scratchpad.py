"""Working Scratchpad for isolated runtime session state and short-term reasoning."""

from __future__ import annotations

import threading
from contextlib import contextmanager
from typing import Any, Dict, Generator, Optional


class WorkingScratchpad:
    """Session-isolated, thread-safe short-term memory scratchpad."""

    def __init__(self):
        self._lock = threading.RLock()
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._default_session = "default"
        self._sessions[self._default_session] = {}

    def _get_bucket(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        sid = session_id or self._default_session
        with self._lock:
            if sid not in self._sessions:
                self._sessions[sid] = {}
            return self._sessions[sid]

    def set(self, key: str, value: Any, session_id: Optional[str] = None) -> None:
        """Store a key-value pair in scratchpad."""
        with self._lock:
            bucket = self._get_bucket(session_id)
            bucket[key] = value

    def get(self, key: str, default: Any = None, session_id: Optional[str] = None) -> Any:
        """Retrieve a value from scratchpad."""
        with self._lock:
            bucket = self._get_bucket(session_id)
            return bucket.get(key, default)

    def has(self, key: str, session_id: Optional[str] = None) -> bool:
        """Check if key exists in scratchpad."""
        with self._lock:
            bucket = self._get_bucket(session_id)
            return key in bucket

    def delete(self, key: str, session_id: Optional[str] = None) -> bool:
        """Delete key from scratchpad."""
        with self._lock:
            bucket = self._get_bucket(session_id)
            if key in bucket:
                del bucket[key]
                return True
            return False

    def clear(self, session_id: Optional[str] = None) -> None:
        """Clear scratchpad contents."""
        with self._lock:
            if session_id:
                if session_id in self._sessions:
                    self._sessions[session_id].clear()
            else:
                self._sessions[self._default_session].clear()

    def export_dict(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Export a copy of current scratchpad state."""
        with self._lock:
            bucket = self._get_bucket(session_id)
            return dict(bucket)

    @contextmanager
    def session(self, session_id: str) -> Generator[Dict[str, Any], None, None]:
        """Context manager scoping mutations to a specific session."""
        with self._lock:
            bucket = self._get_bucket(session_id)
            try:
                yield bucket
            finally:
                pass
