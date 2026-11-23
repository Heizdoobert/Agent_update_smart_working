"""Tests for agent environment installer and system instruction setup."""

from __future__ import annotations

import json
from pathlib import Path

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


def test_write_hermes_mcp_yaml_new_file(tmp_path):
    from agent_system.sdk.installer import write_hermes_mcp_yaml

    cfg = tmp_path / "config.yaml"
    write_hermes_mcp_yaml(cfg, "/abs/agent-system", ["mcp"])
    text = cfg.read_text(encoding="utf-8")
    assert "mcp_servers:" in text
    assert "  agent-system:" in text
    assert "    command: /abs/agent-system" in text
    assert '    args: ["mcp"]' in text


def test_write_hermes_mcp_yaml_preserves_other_servers(tmp_path):
    from agent_system.sdk.installer import write_hermes_mcp_yaml

    cfg = tmp_path / "config.yaml"
    cfg.write_text("mcp_servers:\n  jina:\n    url: https://example.com/mcp\n    timeout: 120\n", encoding="utf-8")
    write_hermes_mcp_yaml(cfg, "/abs/agent-system", ["mcp"])
    text = cfg.read_text(encoding="utf-8")
    assert "  jina:" in text                      # other server preserved
    assert "https://example.com/mcp" in text
    assert "  agent-system:" in text


def test_write_hermes_mcp_yaml_replaces_existing_entry(tmp_path):
    from agent_system.sdk.installer import write_hermes_mcp_yaml

    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        "mcp_servers:\n  agent-system:\n    command: /old/bridge/run.sh\n    args: []\n",
        encoding="utf-8",
    )
    write_hermes_mcp_yaml(cfg, "/new/agent-system", ["mcp"])
    text = cfg.read_text(encoding="utf-8")
    assert "/old/bridge/run.sh" not in text        # old entry gone
    assert "    command: /new/agent-system" in text
    assert text.count("agent-system:") == 1        # no duplicate
    assert '    args: ["mcp"]' in text


def test_inject_opencode_mcp_json_new_file(tmp_path):
    import json

    from agent_system.sdk.installer import inject_opencode_mcp_json

    cfg = tmp_path / "opencode.json"
    inject_opencode_mcp_json(cfg, "/abs/agent-system", ["mcp"])
    data = json.loads(cfg.read_text(encoding="utf-8"))
    entry = data["mcp"]["servers"]["agent-system"]
    assert entry["type"] == "local"
    assert entry["command"] == ["/abs/agent-system", "mcp"]


def test_inject_opencode_mcp_json_preserves_existing(tmp_path):
    import json

    from agent_system.sdk.installer import inject_opencode_mcp_json

    cfg = tmp_path / "opencode.json"
    cfg.write_text('{"$schema": "https://opencode.ai/config.json", "providers": {"openai": {}}}', encoding="utf-8")
    inject_opencode_mcp_json(cfg, "/abs/agent-system", ["mcp"])
    data = json.loads(cfg.read_text(encoding="utf-8"))
    assert data["$schema"] == "https://opencode.ai/config.json"   # preserved
    assert data["providers"]["openai"] == {}                       # preserved
    assert data["mcp"]["servers"]["agent-system"]["command"] == ["/abs/agent-system", "mcp"]


def test_install_hermes_and_opencode_targets(monkeypatch, tmp_path):
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: fake_home)
    monkeypatch.delenv("HERMES_HOME", raising=False)

    res = install_agent_environment(target="hermes", dry_run=False)
    assert res["dry_run"] is False
    hermes_cfg = fake_home / ".hermes" / "config.yaml"
    assert hermes_cfg.is_file()
    assert "  agent-system:" in hermes_cfg.read_text(encoding="utf-8")

    res = install_agent_environment(target="opencode", dry_run=False)
    oc_cfg = fake_home / ".config" / "opencode" / "opencode.json"
    assert oc_cfg.is_file()
    oc_data = json.loads(oc_cfg.read_text(encoding="utf-8"))
    assert "agent-system" in oc_data["mcp"]["servers"]


def test_inject_mcp_config(tmp_path):
    config_file = tmp_path / "claude_desktop_config.json"

    # Inject into non-existent file
    assert inject_mcp_config(config_file) is True
    assert config_file.is_file()

    data = json.loads(config_file.read_text(encoding="utf-8"))
    assert "mcpServers" in data
    assert "agent-system" in data["mcpServers"]
    assert Path(data["mcpServers"]["agent-system"]["command"]).stem == "agent-system"
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
