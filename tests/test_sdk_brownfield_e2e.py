"""End-to-End integration test for Brownfield Codebase Scanner and Ingestion."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import pytest

from agent_system.sdk.registry import PluginRegistry
from agent_system.reflection.adapters.config_rules import MarkdownRulesCritic
from agent_system.storage.sqlite_store import SQLiteStore
from agent_system.memory.semantic import SemanticMemory


def test_brownfield_full_lifecycle_e2e():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)

        # 1. Simulate an existing Node.js & Python polyglot brownfield repository
        (tmppath / "package.json").write_text(json.dumps({
            "name": "fullstack-service",
            "version": "1.2.0",
            "scripts": {
                "test": "jest --runInBand",
                "build": "next build"
            },
            "dependencies": {
                "next": "^14.0.0",
                "react": "^18.2.0"
            }
        }))

        docs_dir = tmppath / "docs"
        docs_dir.mkdir(parents=True, exist_ok=True)
        (docs_dir / "architecture.md").write_text("""# System Architecture

## Authentication Service
JWT-based authentication tokens with asymmetric RSA-256 signing keys.

## Database Migrations
Migrations are managed via Prisma CLI against Postgres 15 cluster.
""")

        readme = tmppath / "README.md"
        readme.write_text("""# Fullstack Service
Enterprise web application.

## Rules
- Always run jest tests before creating a pull request
- Adhere to clean architecture standards
- Never expose API keys in frontend bundles
""")

        # 2. Step 1: Scan via CLI with --json
        scan_cmd = [
            sys.executable,
            "-m",
            "agent_system.cli.main",
            "scan",
            "--root",
            str(tmppath),
            "--json",
        ]
        scan_res = subprocess.run(scan_cmd, capture_output=True, text=True)
        assert scan_res.returncode == 0
        scan_data = json.loads(scan_res.stdout)

        assert "TypeScript" in scan_data["tech_stack"] or "JavaScript" in scan_data["tech_stack"]
        assert scan_data["test_framework"] == "jest"
        assert len(scan_data["documentation_files"]) >= 2
        assert any("clean architecture" in r.lower() for r in scan_data["detected_rules"])

        # 3. Step 2: Ingest via init --auto with --json
        init_cmd = [
            sys.executable,
            "-m",
            "agent_system.cli.main",
            "init",
            "--auto",
            "--root",
            str(tmppath),
            "--json",
        ]
        init_res = subprocess.run(init_cmd, capture_output=True, text=True, input="")
        assert init_res.returncode == 0
        init_data = json.loads(init_res.stdout)
        assert init_data["status"] == "SUCCESS"
        assert init_data["rules_bytes"] <= 3072
        assert init_data["chunks_indexed"] >= 2

        # 4. Verify Tier 1: Rules & Plugin Artifacts
        rules_file = tmppath / ".agent" / "rules.md"
        assert rules_file.is_file()
        assert len(rules_file.read_bytes()) <= 3072

        critic = MarkdownRulesCritic()
        critic_report = critic.validate(rules_file.read_text(encoding="utf-8"))
        assert critic_report.is_passed
        assert critic_report.verdict.score >= 90.0

        # Check symlink or file AGENTS.md
        agents_symlink = tmppath / "AGENTS.md"
        assert agents_symlink.exists()

        # Check agent_plugin.json is valid and loadable by PluginRegistry
        plugin_file = tmppath / "agent_plugin.json"
        assert plugin_file.is_file()
        registry = PluginRegistry(allowed_roots=[tmppath])
        plugin = registry.load_plugin(tmppath)
        assert plugin is not None
        assert plugin.manifest.name == "fullstack_service"
        assert plugin.manifest.rules_path == ".agent/rules.md"

        # 5. Verify Tier 2: Deep Retrieval in Semantic Memory
        db_path = tmppath / ".agent" / "memory.db"
        assert db_path.is_file()
        store = SQLiteStore(db_path=db_path)
        memory = SemanticMemory(store=store)

        search_res = memory.search("RSA-256 JWT authentication", top_k=3)
        assert len(search_res) > 0
        assert any("RSA-256" in item.content for item in search_res)

        search_res_db = memory.search("Prisma Postgres migration", top_k=3)
        assert len(search_res_db) > 0
        assert any("Prisma" in item.content for item in search_res_db)
