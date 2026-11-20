# tests/test_memory_isolation.py
"""Tests for the two‑phase commit memory hardening layer."""

import os
import json
import shutil
from pathlib import Path

# Import the modules under test
from memory_layer import hardening, commit, rollback

# Use a temporary WAL path to avoid interfering with production WAL
TEST_WAL = Path("/tmp/memory_wal_test.jsonl")

# Patch the WAL_PATH used in the modules via monkeypatching the module globals
hardening.WAL_PATH = TEST_WAL
commit.WAL_PATH = TEST_WAL
rollback.WAL_PATH = TEST_WAL


def setup_function(func):
    """Ensure a clean WAL before each test."""
    if TEST_WAL.exists():
        TEST_WAL.unlink()
    TEST_WAL.parent.mkdir(parents=True, exist_ok=True)


def teardown_function(func):
    """Remove the temporary WAL after each test."""
    if TEST_WAL.exists():
        TEST_WAL.unlink()


def test_prepare_and_commit_success(tmp_path):
    project_id = "proj123"
    task_id = "taskA"
    insight_type = "test_insight"
    insight_text = "sample insight"
    metadata = {"key": "value"}

    uid = hardening.prepare_write(project_id, task_id, insight_type, insight_text, metadata)
    # Verify the WAL entry exists and is PREPARED
    with TEST_WAL.open("r", encoding="utf-8") as f:
        entry = json.loads(f.readline())
    assert entry["uid"] == uid
    assert entry["status"] == "PREPARED"

    # Commit the write – should succeed and mark COMMITTED
    assert commit.commit_write(uid) is True
    with TEST_WAL.open("r", encoding="utf-8") as f:
        committed_entry = json.loads(f.readline())
    assert committed_entry["status"] == "COMMITTED"

    # Verify SQLite file was created under the temporary project dir
    sqlite_path = Path(f"~/.agent_system/projects/{project_id}/store.db").expanduser()
    assert sqlite_path.exists()
    # Clean up the created SQLite DB for isolation
    if sqlite_path.exists():
        sqlite_path.unlink()
        sqlite_path.parent.rmdir()


def test_prepare_and_rollback_failure(tmp_path):
    project_id = "proj_fail"
    task_id = "taskB"
    insight_type = "test_insight"
    insight_text = "insight that will fail"
    metadata = {"key": "value"}

    uid = hardening.prepare_write(project_id, task_id, insight_type, insight_text, metadata)
    # Inject a failure by monkey‑patching commit._load_prepared to raise
    original_load = commit._load_prepared
    def broken_load(uid_: str):
        raise RuntimeError("Simulated failure")
    commit._load_prepared = broken_load

    try:
        result = commit.commit_write(uid)
        assert result is False
    finally:
        # Restore original function
        commit._load_prepared = original_load

    # After failure, rollback should mark TOMBSTONE
    assert rollback.rollback_write(uid) is True
    with TEST_WAL.open("r", encoding="utf-8") as f:
        final_entry = json.loads(f.readline())
    assert final_entry["status"] == "TOMBSTONE"
