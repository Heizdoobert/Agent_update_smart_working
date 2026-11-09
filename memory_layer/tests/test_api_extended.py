# Extended tests for memory_layer API
import os, json, tempfile, shutil
import pytest
from pathlib import Path

from memory_layer.agent_hooks import post_task_hook, pre_task_hook
from memory_layer.api import get_ready_vectors, set_status_for_task

@pytest.fixture(autouse=True)
def setup_isolated_db(request):
    db_path = str(Path(tempfile.gettempdir()) / f"test_milvus_ext_{request.node.name}_{os.getpid()}.db")
    p = Path(db_path)
    if p.exists():
        if p.is_dir():
            shutil.rmtree(p)
        else:
            p.unlink()
    os.environ["MEMORY_DB"] = db_path
    from memory_layer._client import reset_client
    reset_client()
    yield
    reset_client()
    if p.exists():
        if p.is_dir():
            shutil.rmtree(p)
        else:
            p.unlink()


def _setup_insights(task_id, user_id, insights):
    # write temporary insight file
    insight_file = Path(tempfile.gettempdir()) / "insights_ext.json"
    insight_file.write_text(json.dumps(insights), encoding="utf-8")
    post_task_hook(task_id, user_id, str(insight_file))
    # file removed by hook
    assert not insight_file.exists()
    return task_id, user_id

def test_complex_query_filtering():
    task, user = _setup_insights("taskA", "user1", [
        {"insight": "First insight about cats", "type": "test"},
        {"insight": "Second insight about dogs", "type": "test"},
    ])
    # Query for 'dogs' should return only the second insight
    results = pre_task_hook(task, user, "dogs", k=5)
    assert len(results) == 1
    assert results[0]["content"] == "Second insight about dogs"

def test_status_marking_and_ready_vectors():
    task, user = _setup_insights("taskB", "user2", [
        {"insight": "Short term insight", "type": "test"},
        {"insight": "Another short term", "type": "test"},
    ])
    # Initially, ready vectors should contain 2 short‑term entries
    ready = get_ready_vectors(k=10)
    assert len(ready) >= 2
    # Mark all insights of this task as longterm
    updated = set_status_for_task(task, "longterm")
    assert updated == 2
    # After marking, ready vectors (shortterm) should no longer include them
    ready_after = get_ready_vectors(k=10)
    # It's possible other short‑term entries exist from previous tests, filter by task_id
    ready_task = [r for r in ready_after if r.get("task_id") == task]
    assert len(ready_task) == 0

# Cleanup DB after tests
def teardown_module(module):
    from memory_layer._client import reset_client
    reset_client()
    db_path = Path(os.getenv("MEMORY_DB"))
    if db_path.exists():
        if db_path.is_dir():
            shutil.rmtree(db_path)
        else:
            db_path.unlink()
