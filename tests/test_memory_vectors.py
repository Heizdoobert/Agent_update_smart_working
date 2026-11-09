"""Vector search ranks by embedding; recipe/index MCP tools work end to end."""

import json

from agent_system.mcp.tools import CognitiveToolsDispatcher
from agent_system.memory import embedder
from agent_system.memory.semantic import SemanticMemory
from agent_system.storage.sqlite_store import SQLiteStore

WORDS = ["redis", "restore", "button", "css"]


def fake_embed(texts, query=False):  # keyword-count vectors, no model download
    return [[float(t.lower().count(w)) for w in WORDS] + [0.1] for t in texts]


def test_vector_ranking_and_fallback(tmp_path, monkeypatch):
    mem = SemanticMemory(store=SQLiteStore(tmp_path / "m.db"))
    monkeypatch.setattr(embedder, "embed", lambda t, query=False: None)  # no embedder: BM25 only
    mem.index_document("a", "css button color")
    monkeypatch.setattr(embedder, "embed", fake_embed)
    mem.index_document("b", "redis restore from dump")
    assert mem.search("redis restore", top_k=1)[0].item_id == "b"  # vector hit
    assert {r.item_id for r in mem.search("css", top_k=2)} == {"a", "b"}  # BM25 tops up the unembedded row


def test_mcp_index_and_recipe_tools(tmp_path, monkeypatch):
    monkeypatch.setattr(embedder, "embed", fake_embed)
    d = CognitiveToolsDispatcher(root_path=tmp_path)
    d._store = SQLiteStore(tmp_path / "t.db")
    assert d.dispatch("agent_memory_index", {"text": "redis restore tip"}) == "indexed 1"
    assert json.loads(d.dispatch("agent_memory_search", {"query": "redis"}))[0]["content"] == "redis restore tip"
    d.dispatch("agent_memory_recipe_record", {"key": "k1", "recipe": "do x"})
    assert d.dispatch("agent_memory_recipe_get", {"key": "k1"}) == "do x"
