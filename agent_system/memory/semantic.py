"""Semantic Memory powered by SQLite FTS5 with automatic Pure-Python BM25 fallback."""

from __future__ import annotations

import json
import math
import re
import sqlite3
import time
from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional, Set

from agent_system.core.contracts import MemoryItem
from agent_system.core.truncator import StructuralTruncator
from agent_system.storage.sqlite_store import SQLiteStore


class PurePythonBM25:
    """Pure-Python in-memory inverted index with BM25 ranking when FTS5 is missing."""

    def __init__(self, k1: float = 1.5, b: float = 0.75) -> None:
        self.k1 = k1
        self.b = b
        self.docs: Dict[str, MemoryItem] = {}
        self.doc_lengths: Dict[str, int] = {}
        self.total_doc_len: int = 0
        self.avg_doc_len: float = 0.0
        self.inverted_index: Dict[str, Dict[str, int]] = defaultdict(dict)  # term -> {doc_id: freq}
        self.doc_count: int = 0

    def _tokenize(self, text: str) -> List[str]:
        return re.findall(r"\w+", text.lower(), re.UNICODE)

    def add_document(self, item: MemoryItem) -> None:
        if item.item_id in self.docs:
            old_item = self.docs[item.item_id]
            old_len = self.doc_lengths.get(item.item_id, 0)
            self.total_doc_len -= old_len
            # Targeted term cleanup instead of scanning entire vocabulary
            for term in set(self._tokenize(old_item.content)):
                if term in self.inverted_index:
                    self.inverted_index[term].pop(item.item_id, None)

        self.docs[item.item_id] = item
        tokens = self._tokenize(item.content)
        length = len(tokens)
        self.doc_lengths[item.item_id] = length
        self.total_doc_len += length

        counts = Counter(tokens)
        for term, freq in counts.items():
            self.inverted_index[term][item.item_id] = freq

        self.doc_count = len(self.docs)
        self.avg_doc_len = self.total_doc_len / max(1, self.doc_count)

    def search(
        self, query: str, category: Optional[str] = None, top_k: int = 3
    ) -> List[MemoryItem]:
        query_terms = self._tokenize(query)
        if not query_terms or self.doc_count == 0:
            return []

        scores: Dict[str, float] = defaultdict(float)

        for term in query_terms:
            if term not in self.inverted_index:
                continue
            matching_docs = self.inverted_index[term]
            df = len(matching_docs)
            # IDF with standard smoothing
            idf = math.log((self.doc_count - df + 0.5) / (df + 0.5) + 1.0)

            for doc_id, tf in matching_docs.items():
                doc = self.docs[doc_id]
                if category and doc.category != category:
                    continue

                doc_len = self.doc_lengths.get(doc_id, 1)
                num = tf * (self.k1 + 1)
                den = tf + self.k1 * (1 - self.b + self.b * (doc_len / max(1.0, self.avg_doc_len)))
                scores[doc_id] += idf * (num / den)

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
        result: List[MemoryItem] = []
        for doc_id, score in ranked:
            item = self.docs[doc_id]
            result.append(
                MemoryItem(
                    item_id=item.item_id,
                    content=item.content,
                    category=item.category,
                    score=round(score, 4),
                    timestamp=item.timestamp,
                    metadata=item.metadata,
                )
            )
        return result


class SemanticMemory:
    """Hybrid Semantic Memory: SQLite FTS5 primary with transparent Pure-Python BM25 fallback."""

    def __init__(self, store: Optional[SQLiteStore] = None) -> None:
        self.store = store or SQLiteStore()
        self.has_fts5 = self._check_and_init_fts5()
        self.fallback_bm25 = PurePythonBM25()
        if not self.has_fts5:
            self._load_fallback_from_db()

    def _check_and_init_fts5(self) -> bool:
        """Attempt to initialize FTS5 virtual table. Return False if module unavailable."""
        try:
            with self.store.transaction() as cur:
                cur.execute(
                    """
                    CREATE VIRTUAL TABLE IF NOT EXISTS semantic_fts USING fts5(
                        item_id UNINDEXED,
                        category,
                        content,
                        tokenize='porter unicode61'
                    );
                    """
                )
            return True
        except sqlite3.OperationalError:
            # FTS5 module not compiled in SQLite
            return False

    def _load_fallback_from_db(self) -> None:
        """Sync persistent memories table into in-memory pure-python BM25 index."""
        def _load(cur: sqlite3.Cursor) -> None:
            cur.execute("SELECT item_id, category, content, score, timestamp, metadata_json FROM memories;")
            rows = cur.fetchall()
            for r in rows:
                item = MemoryItem(
                    item_id=r["item_id"],
                    category=r["category"],
                    content=r["content"],
                    score=r["score"],
                    timestamp=r["timestamp"],
                    metadata=json.loads(r["metadata_json"] or "{}"),
                )
                self.fallback_bm25.add_document(item)

        self.store.execute_with_retry(_load)

    def index_document(
        self,
        item_id: str,
        content: str,
        category: str = "general",
        score: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Index a document into semantic memory."""
        now = time.time()
        meta = metadata or {}
        meta_json = json.dumps(meta, ensure_ascii=False)
        item = MemoryItem(
            item_id=item_id,
            content=content,
            category=category,
            score=score,
            timestamp=now,
            metadata=meta,
        )

        # 1. Always persist to base memories table
        def _persist(cur: sqlite3.Cursor) -> None:
            cur.execute(
                """
                INSERT INTO memories (item_id, category, content, score, timestamp, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(item_id) DO UPDATE SET
                    category = excluded.category,
                    content = excluded.content,
                    score = excluded.score,
                    timestamp = excluded.timestamp,
                    metadata_json = excluded.metadata_json;
                """,
                (item_id, category, content, score, now, meta_json),
            )
            # 2. If FTS5 available, sync into virtual table
            if self.has_fts5:
                cur.execute(
                    "DELETE FROM semantic_fts WHERE item_id = ?;", (item_id,)
                )
                cur.execute(
                    "INSERT INTO semantic_fts (item_id, category, content) VALUES (?, ?, ?);",
                    (item_id, category, content),
                )

        self.store.execute_with_retry(_persist)

        # 3. Always maintain in-memory fallback index
        self.fallback_bm25.add_document(item)

    def search(
        self,
        query: str,
        category: Optional[str] = None,
        top_k: int = 3,
        max_bytes: int = StructuralTruncator.DEFAULT_MAX_BYTES,
    ) -> List[MemoryItem]:
        """Search memory with query, ranking via BM25, bounded by max_bytes."""
        results: List[MemoryItem] = []

        if self.has_fts5:
            try:
                results = self._search_fts5(query, category=category, top_k=top_k)
            except sqlite3.OperationalError:
                # FTS5 query syntax error or unexpected failure -> degrade to pure python
                if self.fallback_bm25.doc_count == 0:
                    self._load_fallback_from_db()
                results = self.fallback_bm25.search(query, category=category, top_k=top_k)
        else:
            if self.fallback_bm25.doc_count == 0:
                self._load_fallback_from_db()
            results = self.fallback_bm25.search(query, category=category, top_k=top_k)

        # Apply StructuralTruncator to enforce context limit across results
        return self._truncate_results(results, max_bytes=max_bytes)

    def _search_fts5(
        self, query: str, category: Optional[str] = None, top_k: int = 3
    ) -> List[MemoryItem]:
        # Sanitize query for FTS5 (escape quotes, split words)
        words = re.findall(r"\w+", query, re.UNICODE)
        if not words:
            return []
        sanitized = " OR ".join(f'"{w}"' for w in words)

        def _query_db(cur: sqlite3.Cursor) -> List[MemoryItem]:
            if category:
                sql = """
                SELECT f.item_id, f.category, f.content, bm25(semantic_fts) as rank, m.metadata_json, m.timestamp
                FROM semantic_fts f
                JOIN memories m ON f.item_id = m.item_id
                WHERE semantic_fts MATCH ? AND f.category = ?
                ORDER BY rank ASC
                LIMIT ?;
                """
                cur.execute(sql, (sanitized, category, top_k))
            else:
                sql = """
                SELECT f.item_id, f.category, f.content, bm25(semantic_fts) as rank, m.metadata_json, m.timestamp
                FROM semantic_fts f
                JOIN memories m ON f.item_id = m.item_id
                WHERE semantic_fts MATCH ?
                ORDER BY rank ASC
                LIMIT ?;
                """
                cur.execute(sql, (sanitized, top_k))

            rows = cur.fetchall()
            return [
                MemoryItem(
                    item_id=r["item_id"],
                    category=r["category"],
                    content=r["content"],
                    score=abs(float(r["rank"])),  # FTS5 bm25 is negative (lower = better)
                    timestamp=r["timestamp"],
                    metadata=json.loads(r["metadata_json"] or "{}"),
                )
                for r in rows
            ]

        return self.store.execute_with_retry(_query_db)

    def _truncate_results(
        self, results: List[MemoryItem], max_bytes: int
    ) -> List[MemoryItem]:
        truncated_results: List[MemoryItem] = []
        used_bytes = 0

        for item in results:
            item_bytes = len(item.content.encode("utf-8"))
            remaining_bytes = max_bytes - used_bytes
            if remaining_bytes <= 64:
                break

            if item_bytes > remaining_bytes:
                safe_content = StructuralTruncator.truncate_text(
                    item.content, max_bytes=remaining_bytes
                )
                truncated_item = MemoryItem(
                    item_id=item.item_id,
                    content=safe_content,
                    category=item.category,
                    score=item.score,
                    timestamp=item.timestamp,
                    metadata=item.metadata,
                )
                truncated_results.append(truncated_item)
                used_bytes += len(safe_content.encode("utf-8"))
                break
            else:
                truncated_results.append(item)
                used_bytes += item_bytes

        return truncated_results
