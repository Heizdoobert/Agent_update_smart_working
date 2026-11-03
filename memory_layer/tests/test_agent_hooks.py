import os
import json
import tempfile
import unittest
from pathlib import Path

# Ensure we use a temporary Milvus Lite DB for isolation
os.environ["MEMORY_DB"] = str(Path(tempfile.gettempdir()) / "test_milvus_lite.db")

from memory_layer.agent_hooks import pre_task_hook, post_task_hook
from memory_layer.scripts.memory_reflection import load_insights

class TestAgentHooks(unittest.TestCase):
    def setUp(self):
        self.db_path = str(Path(tempfile.gettempdir()) / "test_milvus_agent_hooks.db")
        p = Path(self.db_path)
        if p.exists():
            if p.is_dir():
                import shutil
                shutil.rmtree(p)
            else:
                p.unlink()
        os.environ["MEMORY_DB"] = self.db_path
        from memory_layer._client import reset_client
        reset_client()
        # Create a temporary insight JSON file
        self.insight_file = Path(tempfile.gettempdir()) / "insights_test.json"
        insights = [
            {"insight": "Test insight 1", "type": "test"},
            {"insight": "Another insight", "type": "test"},
        ]
        self.insight_file.write_text(json.dumps(insights), encoding="utf-8")
        self.task_id = "task123"
        self.user_id = "userX"

    def tearDown(self):
        from memory_layer._client import reset_client
        reset_client()
        # Clean up files
        if self.insight_file.exists():
            self.insight_file.unlink()
        # Remove temporary DB directory (Milvus Lite creates a folder)
        if hasattr(self, "db_path"):
            db_path = Path(self.db_path)
            if db_path.exists():
                if db_path.is_dir():
                    import shutil
                    shutil.rmtree(db_path)
                else:
                    db_path.unlink()


    def test_post_task_hook_stores_insights(self):
        # Run post hook to store insights
        post_task_hook(self.task_id, self.user_id, str(self.insight_file))
        # After execution, the insight file should be removed
        self.assertFalse(self.insight_file.exists())
        # Verify that insights can be retrieved using pre_task_hook
        retrieved = pre_task_hook(self.task_id, self.user_id, "Test insight", k=5)
        self.assertTrue(any(insight.get("content") == "Test insight 1" for insight in retrieved))
        self.assertTrue(any(insight.get("content") == "Another insight" for insight in retrieved))

    def test_pre_task_hook_no_insights(self):
        # No insights stored yet, should return empty list
        result = pre_task_hook(self.task_id, self.user_id, "nonexistent query", k=5)
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 0)

if __name__ == "__main__":
    unittest.main()
