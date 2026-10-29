"""Tests for CLI scan command and init --auto in agent_system.cli.main."""
import json
import subprocess
import sys
import tempfile
from pathlib import Path
import pytest


def test_cli_scan_json_output():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        # Create a Python repo structure
        (tmppath / "pyproject.toml").write_text('[project]\nname = "cli_demo"\ndependencies = ["fastapi"]')
        (tmppath / "README.md").write_text("# Demo Project\n\n## Rules\n- Always test before push")

        cmd = [
            sys.executable,
            "-m",
            "agent_system.cli.main",
            "scan",
            "--root",
            str(tmppath),
            "--json",
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        assert res.returncode == 0
        data = json.loads(res.stdout)
        assert data["primary_language"] == "Python"
        assert "fastapi" in [s.lower() for s in data["tech_stack"]]
        assert "README.md" in data["documentation_files"]


def test_cli_scan_human_readable_output():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        (tmppath / "package.json").write_text('{"name": "web", "scripts": {"test": "vitest"}}')

        cmd = [
            sys.executable,
            "-m",
            "agent_system.cli.main",
            "scan",
            "--root",
            str(tmppath),
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        assert res.returncode == 0
        assert "Project Scan Summary" in res.stdout
        assert "TypeScript" in res.stdout or "JavaScript" in res.stdout


def test_cli_init_auto_non_interactive():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        (tmppath / "pyproject.toml").write_text('[project]\nname = "auto_svc"\n')
        (tmppath / "README.md").write_text("# Auto Service\n\n## Guide\nRun with python main.py")

        cmd = [
            sys.executable,
            "-m",
            "agent_system.cli.main",
            "init",
            "--auto",
            "--root",
            str(tmppath),
        ]
        # Run with closed stdin to guarantee no prompt blocking
        res = subprocess.run(cmd, capture_output=True, text=True, input="")
        assert res.returncode == 0
        assert (tmppath / ".agent" / "rules.md").is_file()
        assert (tmppath / "agent_plugin.json").is_file()
        assert (tmppath / "AGENTS.md").exists()
        assert (tmppath / ".agent" / "memory.db").exists()
