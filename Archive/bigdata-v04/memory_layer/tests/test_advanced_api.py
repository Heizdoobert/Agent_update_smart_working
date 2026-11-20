# Advanced tests for memory_layer API
import os, json, tempfile, datetime, importlib, shutil
from pathlib import Path

# Ensure each test uses an isolated Milvus Lite DB

def _reset_memory_layer(db_path: str):
    p = Path(db_path)
    if p.exists():
        if p.is_dir():
            shutil.rmtree(p)
        else:
            p.unlink()
    os.environ["MEMORY_DB"] = db_path
    from memory_layer._client import reset_client
    reset_client()
    # Reset singleton client if exists
    import memory_layer
    if hasattr(memory_layer, "_client_instance"):
        memory_layer._client_instance = None
    importlib.reload(memory_layer)
    return memory_layer

def _store_insights(insight_items, task_id="t1", user_id="u1"):
    # Helper to write insights to temp file and invoke post_task_hook
    insight_file = Path(tempfile.gettempdir()) / "tmp_insights.json"
    insight_file.write_text(json.dumps(insight_items), encoding="utf-8")
    from memory_layer.agent_hooks import post_task_hook
    post_task_hook(task_id, user_id, str(insight_file))
    # file removed by hook
    assert not insight_file.exists()
    return task_id, user_id

def test_priority_high_status_longterm():
    db = str(Path(tempfile.gettempdir()) / "test_db_priority.db")
    ml = _reset_memory_layer(db)
    # Insight with high priority should be stored as longterm
    insights = [{"insight": "Critical insight", "type": "test", "priority": "high"}]
    _store_insights(insights)
    # Retrieve directly via client to check status
    client, coll, _ = ml.get_client()
    results = client.query(collection_name=coll, filter="insight_type == 'test'", output_fields=["status"], limit=10)
    assert results and results[0].get("status") == "longterm"

def test_iso_timestamp_ttl_logic():
    db = str(Path(tempfile.gettempdir()) / "test_db_timestamp.db")
    ml = _reset_memory_layer(db)
    old_ts = (datetime.datetime.utcnow() - datetime.timedelta(days=10)).isoformat() + "Z"
    recent_ts = datetime.datetime.utcnow().isoformat() + "Z"
    insights = [
        {"insight": "Old insight", "type": "test", "timestamp": old_ts},
        {"insight": "Recent insight", "type": "test", "timestamp": recent_ts},
    ]
    _store_insights(insights)
    client, coll, _ = ml.get_client()
    # Query all and verify statuses
    results = client.query(collection_name=coll, filter="insight_type == 'test'", output_fields=["status"], limit=10)
    statuses = {r.get("status") for r in results}
    assert "longterm" in statuses  # old insight should be longterm
    assert "shortterm" in statuses  # recent insight should be shortterm

def test_cache_hit_and_partial_hit():
    db = str(Path(tempfile.gettempdir()) / "test_db_cache.db")
    ml = _reset_memory_layer(db)
    # Insert 5 short‑term insights
    insights = [{"insight": f"Insight {i}", "type": "test"} for i in range(5)]
    _store_insights(insights)
    # First call populates cache (request 3)
    first = ml.get_ready_vectors(k=3)
    assert len(first) == 3
    # Delete all short‑term entries from Milvus (simulate DB loss)
    client, coll, _ = ml.get_client()
    client.delete(collection_name=coll, filter="status == 'shortterm'")
    # Second call should still return 3 items from cache (cache hit)
    second = ml.get_ready_vectors(k=3)
    assert len(second) == 3
    # Partial‑hit: request more than cached (k=5). Cache has 3, need 2 more (which will be missing)
    # Since DB is empty, we expect only cached items returned.
    third = ml.get_ready_vectors(k=5)
    assert len(third) == 3  # only cached ones available

def test_purge_trash_and_mark_insight_as_kb():
    db = str(Path(tempfile.gettempdir()) / "test_db_kb_trash.db")
    ml = _reset_memory_layer(db)
    insights = [
        {"insight": "To be trashed", "type": "test"},
        {"insight": "KB entry", "type": "test"},
    ]
    _store_insights(insights)
    client, coll, _ = ml.get_client()
    # Retrieve IDs
    all_items = client.query(collection_name=coll, filter="insight_type == 'test'", output_fields=["*"], limit=10)
    ids = [r.get("insight_id") or r.get("id") for r in all_items]
    trash_id, kb_id = ids[0], ids[1]
    # Mark first as trash, second as knowledge‑base
    assert ml.mark_insight_as_trash(str(trash_id))
    assert ml.mark_insight_as_kb(str(kb_id), "faq")
    # Purge trash
    purged = ml.purge_trash()
    assert purged == 1
    # Verify trash is gone and KB entry is present via get_kb_vectors
    remaining = client.query(collection_name=coll, filter="status == 'trash'", output_fields=["*"], limit=10)
    assert not remaining
    kb_items = ml.get_kb_vectors(k=10)
    assert any(item.get("insight_id") == str(kb_id) for item in kb_items)


def test_tenant_isolation_cross_user():
    db = str(Path(tempfile.gettempdir()) / "test_db_isolation.db")
    ml = _reset_memory_layer(db)
    from memory_layer.agent_hooks import pre_task_hook

    # Store insights for userA and userB
    _store_insights([{"insight": "Secret note for User A", "type": "test"}], task_id="tA", user_id="userA")
    _store_insights([{"insight": "Public note for User B", "type": "test"}], task_id="tB", user_id="userB")

    # User A searches for 'note' -> must only see User A's insight
    res_a = pre_task_hook("tA", "userA", "note", k=5)
    assert len(res_a) == 1
    assert res_a[0]["content"] == "Secret note for User A"

    # User B searches for 'note' -> must only see User B's insight
    res_b = pre_task_hook("tB", "userB", "note", k=5)
    assert len(res_b) == 1
    assert res_b[0]["content"] == "Public note for User B"


def test_input_validation_and_injection_prevention():
    import pytest
    db = str(Path(tempfile.gettempdir()) / "test_db_injection.db")
    ml = _reset_memory_layer(db)

    # Malicious SQL-like / expression strings must be rejected
    with pytest.raises(ValueError):
        ml.mark_insight("100 OR 1==1", "trash")

    with pytest.raises(ValueError):
        ml.set_status_for_task("task'; DROP TABLE --", "trash")

    with pytest.raises(ValueError):
        ml.mark_insight_as_kb("100", "faq; delete from all")


def test_path_traversal_protection():
    from memory_layer.agent_hooks import post_task_hook
    # Create an outside dummy file
    sensitive_file = Path("/etc/resolv.conf")
    if sensitive_file.exists():
        # Passing system path must be rejected without error and resolv.conf must NOT be unlinked
        post_task_hook("taskSec", "userSec", str(sensitive_file))
        assert sensitive_file.exists()


def test_client_reset_and_thread_safety():
    import concurrent.futures
    db = str(Path(tempfile.gettempdir()) / "test_db_threads.db")
    ml = _reset_memory_layer(db)

    ml.reset_client()
    assert ml._client_instance is None

    # Concurrent get_client calls must all return the exact same instance safely
    def fetch():
        return ml.get_client()

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
        results = list(ex.map(lambda _: fetch(), range(16)))

    first = results[0]
    for r in results:
        assert r is first


def test_source_chunk_pointer_and_blake3_uid():
    db = str(Path(tempfile.gettempdir()) / "test_db_source_pointer.db")
    ml = _reset_memory_layer(db)
    from memory_layer.agent_hooks import pre_task_hook, post_task_hook

    uid = ml.compute_blake3_uid("tenant1", "task999", "rule", "Always run quote-aware chunking")
    assert len(uid) == 16

    # Test storing insight with SourceChunkPointer
    pointer = {
        "storage_uri": "s3://datalake/raw_data.csv",
        "file_path": "/tmp/raw_data.csv",
        "chunk_id": "chunk_001",
        "line_range": [100, 150],
        "git_commit_sha": "abc1234",
    }
    insight_file = Path(tempfile.gettempdir()) / "tmp_pointer_insight.json"
    insight_file.write_text(json.dumps([{
        "insight": "Critical quote-aware chunking invariant",
        "type": "rule",
        "source_pointer": pointer,
    }]), encoding="utf-8")

    post_task_hook("task999", "userPointer", str(insight_file))
    results = pre_task_hook("task999", "userPointer", "chunking", k=1)

    assert len(results) == 1
    retrieved = results[0]
    assert retrieved["source_pointer"]["storage_uri"] == "s3://datalake/raw_data.csv"
    assert retrieved["source_pointer"]["chunk_id"] == "chunk_001"
