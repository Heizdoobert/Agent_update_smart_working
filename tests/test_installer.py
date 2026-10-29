"""Tests for agent environment installer and system instruction setup."""

from __future__ import annotations

import json
from pathlib import Path
import pytest

from agent_system.reflection.adapters.config_rules import MarkdownRulesCritic
from agent_system.sdk.installer import (
    UNIVERSAL_SYSTEM_INSTRUCTION,
    inject_mcp_config,
    install_agent_environment,
)


def test_universal_system_instruction_compliance():
    # Verify instruction is under 3072 bytes
    encoded = UNIVERSAL_SYSTEM_INSTRUCTION.encode("utf-8")
    assert len(encoded) <= 3072

    # Verify critic validation passes 100/100
    critic = MarkdownRulesCritic()
    report = critic.validate(UNIVERSAL_SYSTEM_INSTRUCTION)
    assert report.verdict.status.value == "PASS"
    assert report.verdict.score == 100.0


def test_inject_mcp_config(tmp_path):
    config_file = tmp_path / "claude_desktop_config.json"

    # Inject into non-existent file
    assert inject_mcp_config(config_file) is True
    assert config_file.is_file()

    data = json.loads(config_file.read_text(encoding="utf-8"))
    assert "mcpServers" in data
    assert "agent-system" in data["mcpServers"]
    assert data["mcpServers"]["agent-system"]["command"] == "agent-system"
    assert data["mcpServers"]["agent-system"]["args"] == ["mcp"]

    # Inject into existing file with other servers preserved
    data["mcpServers"]["other-tool"] = {"command": "other", "args": []}
    config_file.write_text(json.dumps(data), encoding="utf-8")

    assert inject_mcp_config(config_file) is True
    updated = json.loads(config_file.read_text(encoding="utf-8"))
    assert "other-tool" in updated["mcpServers"]
    assert "agent-system" in updated["mcpServers"]


def test_install_agent_environment_dry_run(monkeypatch, tmp_path):
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: fake_home)

    res = install_agent_environment(target="all", dry_run=True)
    assert res["dry_run"] is True
    assert len(res["mcp_installed"]) > 0
    assert len(res["rules_installed"]) > 0

    # Ensure dry_run did not write files
    assert not (fake_home / ".cursorrules").exists()


def test_install_agent_environment_live(monkeypatch, tmp_path):
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: fake_home)

    res = install_agent_environment(target="all", dry_run=False)
    assert res["dry_run"] is False

    # Check rules files created
    cursor_rules = fake_home / ".cursorrules"
    assert cursor_rules.is_file()
    assert "Universal Agent Cognitive Operating Protocol" in cursor_rules.read_text(encoding="utf-8")

    # Check MCP configs created
    cursor_mcp = fake_home / ".cursor" / "mcp.json"
    assert cursor_mcp.is_file()
    mcp_data = json.loads(cursor_mcp.read_text(encoding="utf-8"))
    assert "agent-system" in mcp_data["mcpServers"]
