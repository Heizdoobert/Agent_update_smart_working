import os
import sys
import unittest
from unittest.mock import patch

# Add repository root to sys.path for import
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(repo_root)

from scripts.run_agent import run_agent

class CLIAgentTest(unittest.TestCase):
    def test_default_model_selection(self):
        # Ensure SMALL_MODEL not set
        if 'SMALL_MODEL' in os.environ:
            del os.environ['SMALL_MODEL']
        out = run_agent('claude', 'test prompt')
        self.assertIn('Claude (claude-2.0)', out)
        out = run_agent('hermes', 'test')
        self.assertIn('Hermes (openhermes-7b)', out)

    def test_small_model_selection(self):
        os.environ['SMALL_MODEL'] = 'true'
        out = run_agent('claude', 'test prompt')
        self.assertIn('Claude (claude-2.0-lite)', out)
        out = run_agent('opencode', 'hello')
        self.assertIn('OpenCode (gpt-3.5-turbo-lite)', out)
        out = run_agent('antigravity', 'ping')
        self.assertIn('Antigravity (flash)', out)
        # Clean up
        del os.environ['SMALL_MODEL']

if __name__ == '__main__':
    unittest.main()
