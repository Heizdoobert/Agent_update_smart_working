"""Tests for CLI integration with SDK: init subcommand, planning action fallback, and safe root invocation."""

from __future__ import annotations

import io
import json
from pathlib import Path
import pytest

from agent_system.cli.main import main


def test_cli_init_subcommand(tmp_path, monkeypatch, capsys):
    # Simulate user answering the 4 questions in interactive wizard
    user_inputs = io.StringIO("cli_test_bot\nAlways test before commit\ncli_action\nclean_ast\n")
    monkeypatch.setattr("sys.stdin", user_inputs)
    
    # Change CWD to tmp_path
    monkeypatch.chdir(tmp_path)
    
    rc = main(["init"])
    assert rc == 0
    captured = capsys.readouterr()
    assert "Successfully configured project SDK" in captured.out
    
    assert (tmp_path / "agent_plugin.json").is_file()
    assert (tmp_path / ".agent" / "rules.md").is_file()
    assert (tmp_path / "plugin.py").is_file()


def test_cli_plan_fallback_to_plugin_actions(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    
    # Setup a state file
    init_file = tmp_path / "init.json"
    init_file.write_text(json.dumps({"ready": True, "done": False}), encoding="utf-8")
    
    # Setup plugin with an action
    plugin_py = tmp_path / "plugin.py"
    plugin_py.write_text(
        """
from agent_system.reasoning.transition import ActionDefinition
from agent_system.sdk.contracts import BasePlugin

class PlanBotPlugin(BasePlugin):
    def get_actions(self):
        return [
            ActionDefinition(
                name="plugin_step",
                cost=1.0,
                preconditions={"ready": True},
                effects={"done": True},
            )
        ]
""",
        encoding="utf-8",
    )
    
    manifest = {
        "name": "plan_bot",
        "version": "0.1.0",
        "entrypoint": "plugin:PlanBotPlugin",
    }
    (tmp_path / "agent_plugin.json").write_text(json.dumps(manifest), encoding="utf-8")
    
    # Call plan WITHOUT --actions flag
    rc = main(["plan", "--initial", str(init_file), "--goal-key", "done", "--goal-value", "true"])
    assert rc == 0
    captured = capsys.readouterr()
    plan_data = json.loads(captured.out)
    assert len(plan_data["steps"]) == 1
    assert plan_data["steps"][0]["action"] == "plugin_step"


def test_cli_plan_fails_when_no_actions_and_no_plugin(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    init_file = tmp_path / "init.json"
    init_file.write_text(json.dumps({"a": 1}), encoding="utf-8")
    
    rc = main(["plan", "--initial", str(init_file), "--goal-key", "a", "--goal-value", "2"])
    assert rc == 1
    captured = capsys.readouterr()
    assert "No action definitions found" in captured.err or "Error" in captured.err


def test_cli_unix_pipe_never_hijacked_by_wizard(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    # Ensure CWD is clean (no plugin)
    # Piped input to critic
    piped_code = io.StringIO("def add(a: int, b: int) -> int:\n    return a + b\n")
    monkeypatch.setattr("sys.stdin", piped_code)
    
    rc = main(["critic", "--file", "-"])
    assert rc == 0
    captured = capsys.readouterr()
    # Must output critic evaluation JSON, NOT wizard prompt
    res = json.loads(captured.out)
    assert res["status"] == "PASS"
    assert "Project Setup Wizard" not in captured.out
