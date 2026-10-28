"""Tests for SQLiteStore (WAL mode, concurrency) and SessionManager."""

import concurrent.futures
import tempfile
from pathlib import Path
import pytest

from agent_system.core.session import SessionManager
from agent_system.storage.sqlite_store import SQLiteStore


@pytest.fixture
def temp_db():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        yield db_path


def test_sqlite_store_wal_mode(temp_db):
    store = SQLiteStore(temp_db)
    conn = store.get_connection()
    cur = conn.cursor()
    cur.execute("PRAGMA journal_mode;")
    mode = cur.fetchone()[0]
    conn.close()
    assert mode.lower() == "wal"


def test_session_manager_lifecycle(temp_db):
    store = SQLiteStore(temp_db)
    mgr = SessionManager(store)

    session = mgr.create_session("sess-1", {"user": "tester", "step": 1})
    assert session.session_id == "sess-1"
    assert session.get("user") == "tester"

    # Fetch back
    fetched = mgr.get_session("sess-1")
    assert fetched is not None
    assert fetched.get("step") == 1

    # Update
    fetched.set("step", 2)
    fetched.set("status", "running")
    mgr.save_session(fetched)

    updated = mgr.get_session("sess-1")
    assert updated.get("step") == 2
    assert updated.get("status") == "running"

    # List & Delete
    sessions = mgr.list_sessions()
    assert "sess-1" in sessions

    mgr.delete_session("sess-1")
    assert mgr.get_session("sess-1") is None


def test_concurrent_writes(temp_db):
    store = SQLiteStore(temp_db)
    mgr = SessionManager(store)

    num_threads = 8
    num_writes_per_thread = 20

    def worker(worker_id):
        for i in range(num_writes_per_thread):
            sid = f"worker-{worker_id}-sess-{i}"
            sess = mgr.create_session(sid, {"data": i * 10})
            sess.set("updated", True)
            mgr.save_session(sess)
        return True

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(worker, w) for w in range(num_threads)]
        results = [f.result() for f in futures]

    assert all(results)
    all_sessions = mgr.list_sessions()
    assert len(all_sessions) == num_threads * num_writes_per_thread


def test_concurrent_store_init(temp_db):
    num_threads = 6

    def init_worker():
        s = SQLiteStore(temp_db)
        return s.db_path.exists()

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(init_worker) for _ in range(num_threads)]
        results = [f.result() for f in futures]

    assert all(results)
