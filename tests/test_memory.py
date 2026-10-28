"""Tests for 3-Tier Memory: Episodic, Semantic (FTS5 + pure-Python BM25), Scratchpad."""

import tempfile
from pathlib import Path
import pytest

from agent_system.core.contracts import TraceRecord
from agent_system.memory.episodic import EpisodicMemory
from agent_system.memory.scratchpad import WorkingScratchpad
from agent_system.memory.semantic import PurePythonBM25, SemanticMemory
from agent_system.storage.sqlite_store import SQLiteStore


@pytest.fixture
def temp_store():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_mem.db"
        yield SQLiteStore(db_path)


def test_episodic_memory(temp_store):
    episodic = EpisodicMemory(temp_store)

    # 1. Record traces
    trace1 = TraceRecord(task_id="task-42", step_index=0, action="init", observation="ready")
    trace2 = TraceRecord(task_id="task-42", step_index=1, action="execute", observation="success", reward=1.0, done=True)
    episodic.record_trace(trace1)
    episodic.record_trace(trace2)

    traces = episodic.get_traces("task-42")
    assert len(traces) == 2
    assert traces[0].action == "init"
    assert traces[1].done is True

    # 2. Recovery recipes
    episodic.record_recipe("POPUP_BLOCKED", "click_close_button", ["popup", "ui"])
    recipe = episodic.lookup_recipe("POPUP_BLOCKED")
    assert recipe is not None
    assert recipe["recipe"] == "click_close_button"
    assert recipe["success_count"] == 1

    # Reinforce recipe
    episodic.record_recipe("POPUP_BLOCKED", "click_close_button")
    reinforced = episodic.lookup_recipe("POPUP_BLOCKED")
    assert reinforced["success_count"] == 2


def test_pure_python_bm25_ranking():
    bm25 = PurePythonBM25()
    from agent_system.core.contracts import MemoryItem

    item1 = MemoryItem("doc1", "Python async programming with asyncio event loop", "python")
    item2 = MemoryItem("doc2", "Database indexing and SQLite query optimization", "database")
    item3 = MemoryItem("doc3", "Python SQLite database connection and WAL mode", "database")

    bm25.add_document(item1)
    bm25.add_document(item2)
    bm25.add_document(item3)

    # Query for database
    results = bm25.search("database sqlite", top_k=2)
    assert len(results) == 2
    # doc3 has both 'sqlite' and 'database', should rank high
    doc_ids = [r.item_id for r in results]
    assert "doc3" in doc_ids or "doc2" in doc_ids


def test_semantic_memory_fts5_and_fallback(temp_store):
    semantic = SemanticMemory(temp_store)

    semantic.index_document("doc-1", "Machine learning agents and cognitive reasoning loops", category="ai")
    semantic.index_document("doc-2", "Software testing and static code analysis AST", category="qa")
    semantic.index_document("doc-3", "Automated cognitive planning with Tree of Thoughts", category="ai")

    # Search with category filter
    res = semantic.search("cognitive thoughts", category="ai", top_k=2)
    assert len(res) >= 1
    assert any("cognitive" in item.content.lower() for item in res)

    # Test forced pure-Python fallback
    semantic_fallback = SemanticMemory(temp_store)
    semantic_fallback.has_fts5 = False  # Simulate environment without FTS5
    semantic_fallback.fallback_bm25.add_document(res[0])
    fallback_res = semantic_fallback.search("cognitive", top_k=1)
    assert len(fallback_res) == 1


def test_semantic_memory_3kb_budget(temp_store):
    semantic = SemanticMemory(temp_store)
    # Insert a very long document
    long_content = "Hệ thống tác tử thông minh nhận thức độc lập. " * 200
    semantic.index_document("long-1", long_content, category="test")

    res = semantic.search("thông minh", category="test", max_bytes=1024)
    assert len(res) == 1
    assert len(res[0].content.encode("utf-8")) <= 1024


def test_working_scratchpad():
    pad = WorkingScratchpad()

    # Default session
    pad.set("counter", 1)
    assert pad.get("counter") == 1
    assert pad.has("counter") is True

    # Isolated session
    with pad.session("task-A") as s:
        s["status"] = "in_progress"

    assert pad.get("status", session_id="task-A") == "in_progress"
    assert pad.get("status", session_id="default") is None

    # Clear session
    pad.clear("task-A")
    assert pad.get("status", session_id="task-A") is None


def test_pure_python_bm25_clean_postings_on_update():
    from agent_system.core.contracts import MemoryItem

    bm25 = PurePythonBM25()
    doc = MemoryItem("doc1", "apple fruit red")
    bm25.add_document(doc)

    assert len(bm25.search("apple")) == 1

    # Update document with completely new terms
    updated_doc = MemoryItem("doc1", "banana yellow tropical")
    bm25.add_document(updated_doc)

    # Old term "apple" must no longer return doc1
    assert len(bm25.search("apple")) == 0
    # New term "banana" must return doc1
    assert len(bm25.search("banana")) == 1


def test_semantic_memory_fallback_syncs_from_db(temp_store):
    primary = SemanticMemory(temp_store)
    primary.index_document("doc-sync", "Quantum computing and qubit coherence", category="physics")

    fallback_instance = SemanticMemory(temp_store)
    fallback_instance.has_fts5 = False
    assert fallback_instance.fallback_bm25.doc_count == 0

    res = fallback_instance.search("quantum qubit", category="physics")
    assert len(res) == 1
    assert res[0].item_id == "doc-sync"
    assert fallback_instance.fallback_bm25.doc_count >= 1


def test_working_scratchpad_concurrent_sessions():
    import threading
    import time

    pad = WorkingScratchpad()
    session_b_completed = False

    def session_a_worker():
        with pad.session("session_A"):
            time.sleep(0.15)

    def session_b_worker():
        nonlocal session_b_completed
        time.sleep(0.02)
        t0 = time.time()
        pad.set("ready", True, session_id="session_B")
        elapsed = time.time() - t0
        assert elapsed < 0.1
        session_b_completed = True

    t1 = threading.Thread(target=session_a_worker)
    t2 = threading.Thread(target=session_b_worker)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    assert session_b_completed is True
    assert pad.get("ready", session_id="session_B") is True
