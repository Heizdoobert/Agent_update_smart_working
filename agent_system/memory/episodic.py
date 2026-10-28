"""Episodic Memory for storing and retrieving past execution traces and healing recipes."""

from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional

from agent_system.core.contracts import TraceRecord
from agent_system.storage.sqlite_store import SQLiteStore


class EpisodicMemory:
    """Manages sequential execution traces and successful recovery formulas."""

    def __init__(self, store: Optional[SQLiteStore] = None):
        self.store = store or SQLiteStore()
        self._init_recipes_table()

    def _init_recipes_table(self) -> None:
        def _init(cur):
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS recovery_recipes (
                    issue_key TEXT PRIMARY KEY,
                    recipe TEXT NOT NULL,
                    tags_json TEXT DEFAULT '[]',
                    success_count INTEGER DEFAULT 1,
                    last_used REAL NOT NULL
                );
                """
            )
        self.store.execute_with_retry(_init)

    def record_trace(self, trace: TraceRecord) -> None:
        """Record an execution step into episodic memory."""
        ts = trace.timestamp or time.time()
        metadata_json = json.dumps(trace.metadata, ensure_ascii=False)

        def _insert(cur):
            cur.execute(
                """
                INSERT INTO traces (task_id, step_index, action, observation, reward, done, timestamp, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    trace.task_id,
                    trace.step_index,
                    trace.action,
                    trace.observation,
                    trace.reward,
                    1 if trace.done else 0,
                    ts,
                    metadata_json,
                ),
            )

        self.store.execute_with_retry(_insert)

    def get_traces(self, task_id: str) -> List[TraceRecord]:
        """Retrieve all recorded trace steps for a given task ID."""
        def _fetch(cur):
            cur.execute(
                """
                SELECT task_id, step_index, action, observation, reward, done, timestamp, metadata_json
                FROM traces WHERE task_id = ? ORDER BY step_index ASC;
                """,
                (task_id,),
            )
            rows = cur.fetchall()
            return [
                TraceRecord(
                    task_id=r["task_id"],
                    step_index=r["step_index"],
                    action=r["action"],
                    observation=r["observation"],
                    reward=r["reward"],
                    done=bool(r["done"]),
                    timestamp=r["timestamp"],
                    metadata=json.loads(r["metadata_json"] or "{}"),
                )
                for r in rows
            ]

        return self.store.execute_with_retry(_fetch)

    def record_recipe(
        self, issue_key: str, recipe: str, tags: Optional[List[str]] = None
    ) -> None:
        """Record or reinforce a successful recovery formula / recipe."""
        tags_json = json.dumps(tags or [], ensure_ascii=False)
        now = time.time()

        def _upsert(cur):
            cur.execute(
                """
                INSERT INTO recovery_recipes (issue_key, recipe, tags_json, success_count, last_used)
                VALUES (?, ?, ?, 1, ?)
                ON CONFLICT(issue_key) DO UPDATE SET
                    recipe = excluded.recipe,
                    tags_json = excluded.tags_json,
                    success_count = recovery_recipes.success_count + 1,
                    last_used = excluded.last_used;
                """,
                (issue_key, recipe, tags_json, now),
            )

        self.store.execute_with_retry(_upsert)

    def lookup_recipe(self, issue_key: str) -> Optional[Dict[str, Any]]:
        """Find a recovery recipe by its issue key or error signature."""
        def _get(cur):
            cur.execute(
                """
                SELECT issue_key, recipe, tags_json, success_count, last_used
                FROM recovery_recipes WHERE issue_key = ?;
                """,
                (issue_key,),
            )
            row = cur.fetchone()
            if not row:
                return None
            return {
                "issue_key": row["issue_key"],
                "recipe": row["recipe"],
                "tags": json.loads(row["tags_json"] or "[]"),
                "success_count": row["success_count"],
                "last_used": row["last_used"],
            }

        return self.store.execute_with_retry(_get)
