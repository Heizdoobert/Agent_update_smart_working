"""Session management for persistent state across CLI and multi-agent processes."""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from agent_system.storage.sqlite_store import SQLiteStore


@dataclass
class Session:
    session_id: str
    data: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.data[key] = value
        self.updated_at = time.time()


class SessionManager:
    """Manages persistent sessions backed by SQLiteStore."""

    def __init__(self, store: Optional[SQLiteStore] = None):
        self.store = store or SQLiteStore()

    def create_session(
        self,
        session_id: Optional[str] = None,
        initial_data: Optional[Dict[str, Any]] = None,
    ) -> Session:
        sid = session_id or str(uuid.uuid4())[:8]
        now = time.time()
        session = Session(
            session_id=sid,
            data=initial_data or {},
            created_at=now,
            updated_at=now,
        )
        self.save_session(session)
        return session

    def get_session(self, session_id: str) -> Optional[Session]:
        def _fetch(cur):
            cur.execute(
                "SELECT session_id, data_json, created_at, updated_at FROM sessions WHERE session_id = ?;",
                (session_id,),
            )
            row = cur.fetchone()
            if not row:
                return None
            return Session(
                session_id=row["session_id"],
                data=json.loads(row["data_json"]),
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )

        return self.store.execute_with_retry(_fetch)

    def get_or_create(self, session_id: str) -> Session:
        existing = self.get_session(session_id)
        if existing:
            return existing
        return self.create_session(session_id=session_id)

    def save_session(self, session: Session) -> None:
        session.updated_at = time.time()
        data_json = json.dumps(session.data, ensure_ascii=False)

        def _save(cur):
            cur.execute(
                """
                INSERT INTO sessions (session_id, data_json, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    data_json = excluded.data_json,
                    updated_at = excluded.updated_at;
                """,
                (session.session_id, data_json, session.created_at, session.updated_at),
            )

        self.store.execute_with_retry(_save)

    def delete_session(self, session_id: str) -> bool:
        def _delete(cur):
            cur.execute("DELETE FROM sessions WHERE session_id = ?;", (session_id,))
            return cur.rowcount > 0

        return self.store.execute_with_retry(_delete)

    def list_sessions(self) -> List[str]:
        def _list(cur):
            cur.execute("SELECT session_id FROM sessions ORDER BY updated_at DESC;")
            return [row["session_id"] for row in cur.fetchall()]

        return self.store.execute_with_retry(_list)
