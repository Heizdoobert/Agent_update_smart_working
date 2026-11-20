# tests/test_tenant_vector_store_milvus.py
"""Tests for the Milvus‑based tenant‑aware vector store wrapper.

The wrapper uses the project's Milvus Lite client (`memory_layer._client`).
These tests run entirely in‑process without external services.
"""

import os
import tempfile
import unittest

# Ensure the wrapper picks up a fresh, isolated Milvus database.

def _setup_temp_db():
    tmp_dir = tempfile.TemporaryDirectory()
    # Set MEMORY_DB env to a file inside the temp dir.
    os.environ["MEMORY_DB"] = os.path.join(tmp_dir.name, "milvus_lite.db")
    return tmp_dir

class TenantVectorStoreMilvusTest(unittest.TestCase):
    def test_isolation_and_persistence(self):
        from scripts.tenant_vector_store import TenantVectorStore
        # Create a temporary Milvus DB for this test.
        tmp = _setup_temp_db()
        try:
            # Tenant A adds a document.
            store_a = TenantVectorStore(tenant_id="tenant_a")
            store_a.add_documents(["apple banana"])
            results_a1 = store_a.query("apple", top_k=5)
            self.assertTrue(any("apple" in hit["content"] for hit in results_a1))

            # New instance for same tenant should see the data.
            store_a2 = TenantVectorStore(tenant_id="tenant_a")
            results_a2 = store_a2.query("apple", top_k=5)
            self.assertTrue(any("apple" in hit["content"] for hit in results_a2))

            # Tenant B should not see Tenant A's data.
            store_b = TenantVectorStore(tenant_id="tenant_b")
            store_b.add_documents(["carrot donut"])
            results_b = store_b.query("carrot", top_k=5)
            self.assertTrue(any("carrot" in hit["content"] for hit in results_b))
            # Ensure isolation.
            self.assertFalse(any("carrot" in hit["content"] for hit in results_a2))

            # Cleanup.
            store_a.delete_all()
            store_b.delete_all()
            self.assertEqual(store_a2.query("apple", top_k=5), [])
            self.assertEqual(store_b.query("carrot", top_k=5), [])
        finally:
            tmp.cleanup()
            # Unset env to avoid affecting other tests.
            os.environ.pop("MEMORY_DB", None)

if __name__ == "__main__":
    unittest.main()
