# Utility wrapper for tenant‑aware vector store using Milvus Lite.
"""Utility wrapper for tenant‑aware vector store using Milvus Lite.

The wrapper stores embeddings in the project's Milvus Lite collection while
including a `tenant_id` field to enforce isolation.  It provides a simple
`add_documents`, `query`, and `delete_all` API that the rest of the codebase can
use without dealing directly with Milvus details.

Usage example::

    from scripts.tenant_vector_store import TenantVectorStore

    store = TenantVectorStore(tenant_id="tenant_123")
    store.add_documents(["Hello world", "Goodbye world"])
    results = store.query("hello", top_k=5)
"""

import os
import re
from typing import List, Any

from memory_layer.api import _validate_id as _validate_tenant_id
from memory_layer._client import get_client
from memory_layer.api import compute_blake3_uid  # deterministic UID generator

class TenantVectorStore:
    """Tenant‑scoped wrapper around Milvus Lite.

    Parameters
    ----------
    tenant_id: str
        Identifier for the tenant; validated against the project's safe‑id pattern.
    """

    def __init__(self, tenant_id: str):
        self.tenant_id = _validate_tenant_id(tenant_id, name="tenant_id")
        # Retrieve singleton Milvus client, collection name, and embedding dimension.
        self.client, self.collection, self.dim = get_client()

    def _embed(self, texts: List[str]) -> List[List[float]]:
        """Deterministic stub embedding generator.

        For test purposes we create a reproducible vector of length ``self.dim``
        based on the SHA‑256 hash of each text.  In production this would call a
        real embedding model.
        """
        import hashlib
        vectors = []
        for txt in texts:
            h = int(hashlib.sha256(txt.encode()).hexdigest(), 16)
            val = (h % 1000) / 1000.0
            vectors.append([val] * self.dim)
        return vectors

    def add_documents(self, texts: List[str]):
        """Add raw text documents for the current tenant.

        Each document is embedded via ``_embed`` and inserted with a ``tenant_id``
        payload field.  A deterministic ``insight_id`` is generated to allow
        idempotent upserts.
        """
        if not texts:
            return
        vectors = self._embed(texts)
        entities = []
        for txt, vec in zip(texts, vectors):
            insight_id = compute_blake3_uid(self.tenant_id, "add", "text", txt)
            entity = {
                "vector": vec,
                "tenant_id": self.tenant_id,
                "content": txt,
                "insight_id": insight_id,
            }
            entities.append(entity)
        self.client.insert(collection_name=self.collection, data=entities)
        self.client.flush(collection_name=self.collection)

    def query(self, query_text: str, top_k: int = 10) -> List[Any]:
        """Similarity search restricted to the current tenant.

        Returns a list of dictionaries containing ``insight_id``, ``content``
        and the relevance ``score``.
        """
        if not query_text:
            return []
        q_vec = self._embed([query_text])[0]
        # Milvus Lite search expects `data` (vectors) and the name of the vector field.
        results = self.client.search(
            collection_name=self.collection,
            data=[q_vec],
            anns_field="vector",
            search_params={"metric_type": "L2", "params": {"nprobe": 10}},
            limit=top_k,
            filter=f"tenant_id == '{self.tenant_id}'",
            output_fields=["insight_id", "content"],
        )
        hits = []
        for hit in results[0]:
            hits.append({
                "insight_id": hit.id,
                "content": hit.entity.get("content"),
                "score": hit.score,
            })
        return hits

    def delete_all(self):
        """Delete all vectors belonging to this tenant.

        Useful for test teardown.  It issues a delete with a ``tenant_id`` filter.
        """
        self.client.delete(collection_name=self.collection, filter=f"tenant_id == '{self.tenant_id}'")
        self.client.flush(collection_name=self.collection)

if __name__ == "__main__":
    # Simple sanity check when run directly.
    store = TenantVectorStore(tenant_id="demo")
    store.add_documents(["sample text one", "another example sentence"])
    print("Query results:", store.query("sample"))
    store.delete_all()
    print("After delete, query:", store.query("sample"))
