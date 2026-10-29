"""Tests for KnowledgeIngester in agent_system.sdk.ingestion."""
import os
from pathlib import Path
import tempfile
import pytest

from agent_system.sdk.scanner import ProjectManifest
from agent_system.sdk.ingestion import KnowledgeIngester, IngestionResult
from agent_system.memory.semantic import SemanticMemory
from agent_system.storage.sqlite_store import SQLiteStore
from agent_system.reflection.adapters.config_rules import MarkdownRulesCritic


def test_ingestion_creates_tier1_rules_under_3kb_and_symlink():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        manifest = ProjectManifest(
            root_path=str(tmppath),
            primary_language="Python",
            tech_stack=["Python", "FastAPI", "pytest", "Docker"],
            test_framework="pytest",
            build_commands={"test": "pytest tests/ -v", "run": "uvicorn app:main"},
            documentation_files=[],
            detected_rules=[
                "Always write type hints for functions",
                "Keep functions under 50 lines",
                "Never log sensitive credentials",
            ],
            extra_metadata={},
        )
        ingester = KnowledgeIngester(root_path=tmppath)
        result = ingester.ingest(manifest)

        assert isinstance(result, IngestionResult)
        assert result.rules_bytes <= 3072
        assert result.rules_path.is_file()

        # Check rules content
        rules_text = result.rules_path.read_text()
        assert "# Project Rules" in rules_text or "# " in rules_text
        assert "FastAPI" in rules_text
        assert "pytest tests/ -v" in rules_text

        # Validate with MarkdownRulesCritic
        critic = MarkdownRulesCritic()
        critic_report = critic.validate(rules_text)
        assert critic_report.is_passed
        assert critic_report.verdict.score >= 90.0

        # Check symlink or file for AGENTS.md
        agents_md = tmppath / "AGENTS.md"
        assert agents_md.exists()

        # Check agent_plugin.json created
        plugin_json = tmppath / "agent_plugin.json"
        assert plugin_json.is_file()


def test_ingestion_tier2_semantic_memory_chunking():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        # Create a sample README with H2 sections
        readme = tmppath / "README.md"
        readme.write_text("""# Project Gateway

Overview of Gateway architecture.

## Deployment Guide
Deploy the container with docker-compose up. Ensure port 8080 is open.

## Troubleshooting
If connection fails with code 502, check Redis cache server status.
""")
        manifest = ProjectManifest(
            root_path=str(tmppath),
            primary_language="Python",
            tech_stack=["Python"],
            documentation_files=["README.md"],
            detected_rules=[],
        )
        db_path = tmppath / ".agent" / "memory.db"
        ingester = KnowledgeIngester(root_path=tmppath, db_path=db_path)
        result = ingester.ingest(manifest)

        assert result.chunks_indexed >= 2

        # Verify semantic memory can search this knowledge
        store = SQLiteStore(db_path=db_path)
        memory = SemanticMemory(store=store)

        search_results = memory.search("502 Redis cache server", top_k=3)
        assert len(search_results) > 0
        assert any("Redis" in r.content or "502" in r.content for r in search_results)


def test_ingestion_huge_rules_list_strictly_truncated():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        # Create 100 long rules that would normally exceed 5KB
        huge_rules = [f"Rule #{i}: " + ("x" * 100) for i in range(100)]
        manifest = ProjectManifest(
            root_path=str(tmppath),
            primary_language="Python",
            tech_stack=["Python"] * 50,
            detected_rules=huge_rules,
        )
        ingester = KnowledgeIngester(root_path=tmppath)
        result = ingester.ingest(manifest)

        assert result.rules_bytes <= 3072
        assert len(result.rules_path.read_bytes()) <= 3072
