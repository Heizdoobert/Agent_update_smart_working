"""Concurrency-hardened SQLite store with WAL mode and exponential backoff retries."""

from __future__ import annotations

import os
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Generator, List, Optional, Tuple, TypeVar, Union

T = TypeVar("T")


class SQLiteStore:
    """Thread-safe and multi-process friendly SQLite store configured with WAL mode."""

    def __init__(self, db_path: Optional[Union[str, Path]] = None) -> None:
        if db_path is None:
            default_dir = Path.home() / ".agent_system"
            default_dir.mkdir(parents=True, exist_ok=True)
            self.db_path = default_dir / "agent_system.db"
        else:
            self.db_path = Path(db_path)
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._init_db()

    def get_connection(self) -> sqlite3.Connection:
        """Create and configure a connection with WAL and busy timeout."""
        conn = sqlite3.connect(
            str(self.db_path),
            timeout=10.0,
            check_same_thread=False,
        )
        conn.row_factory = sqlite3.Row
        # Enforce WAL mode and 5000ms busy timeout
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA busy_timeout=5000;")
        return conn

    @contextmanager
    def transaction(self) -> Generator[sqlite3.Cursor, None, None]:
        """Context manager for atomic transaction with auto-commit and rollback."""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def execute_with_retry(
        self,
        func: Callable[[sqlite3.Cursor], T],
        max_retries: int = 5,
        base_delay: float = 0.05,
    ) -> T:
        """Execute a database function with exponential backoff on lock contention."""
        last_error = None
        for attempt in range(max_retries):
            try:
                with self.transaction() as cursor:
                    return func(cursor)
            except sqlite3.OperationalError as e:
                if "locked" in str(e).lower() or "busy" in str(e).lower():
                    last_error = e
                    time.sleep(base_delay * (2**attempt))
                    continue
                raise
        raise sqlite3.OperationalError(f"Database locked after {max_retries} retries: {last_error}")

    def _init_db(self) -> None:
        """Initialize database schema tables."""
        def _init(cur: sqlite3.Cursor) -> None:
            # Sessions table
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    data_json TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                );
                """
            )
            # Traces (Episodic) table
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS traces (
                    trace_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    step_index INTEGER NOT NULL,
                    action TEXT NOT NULL,
                    observation TEXT NOT NULL,
                    reward REAL DEFAULT 0.0,
                    done INTEGER DEFAULT 0,
                    timestamp REAL NOT NULL,
                    metadata_json TEXT DEFAULT '{}'
                );
                """
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_traces_task ON traces(task_id);"
            )
            # Memories table
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS memories (
                    item_id TEXT PRIMARY KEY,
                    category TEXT NOT NULL,
                    content TEXT NOT NULL,
                    score REAL DEFAULT 1.0,
                    timestamp REAL NOT NULL,
                    metadata_json TEXT DEFAULT '{}'
                );
                """
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_memories_cat ON memories(category);"
            )

        self.execute_with_retry(_init)
