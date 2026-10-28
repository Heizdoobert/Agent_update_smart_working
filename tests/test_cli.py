"""Tests for Unified CLI interface."""

import json
import tempfile
from pathlib import Path
import pytest

from agent_system.cli.main import main


def test_cli_help(capsys):
    with pytest.raises(SystemExit) as excinfo:
        main(["--help"])
    assert excinfo.value.code == 0
    captured = capsys.readouterr()
    assert "agent-system" in captured.out


def test_cli_version(capsys):
    with pytest.raises(SystemExit) as excinfo:
        main(["--version"])
    assert excinfo.value.code == 0
    captured = capsys.readouterr()
    assert "agent-system 0.1.0" in captured.out


def test_cli_session_lifecycle(capsys):
    # Set
    rc = main(["session", "set", "--id", "cli_sess", "--key", "user", "--value", "agent_1"])
    assert rc == 0

    # Get
    capsys.readouterr()
    rc = main(["session", "get", "--id", "cli_sess"])
    assert rc == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["user"] == "agent_1"

    # List
    rc = main(["session", "list"])
    assert rc == 0
    captured = capsys.readouterr()
    assert "cli_sess" in captured.out

    # Delete
    rc = main(["session", "delete", "--id", "cli_sess"])
    assert rc == 0


def test_cli_critic_and_reflect(tmp_path, capsys):
    bad_code_file = tmp_path / "bad.py"
    bad_code_file.write_text("import pdb\n\ndef run():\n    return 42\n", encoding="utf-8")

    # Critic check (should fail because pdb is imported)
    rc = main(["critic", "--file", str(bad_code_file)])
    assert rc == 1  # Exit code 1 for reject
    captured = capsys.readouterr()
    res = json.loads(captured.out)
    assert res["status"] == "REJECT"

    # Reflect check (should auto-patch and succeed)
    rc = main(["reflect", "--file", str(bad_code_file), "--output-code"])
    assert rc == 0
    captured = capsys.readouterr()
    assert "# [Self-Reflection" in captured.out


def test_cli_plan(tmp_path, capsys):
    init_file = tmp_path / "init.json"
    init_file.write_text(json.dumps({"has_key": False, "door_unlocked": False}), encoding="utf-8")

    actions_file = tmp_path / "actions.json"
    actions_file.write_text(
        json.dumps(
            [
                {
                    "name": "pickup_key",
                    "cost": 1.0,
                    "preconditions": {"has_key": False},
                    "effects": {"has_key": True},
                },
                {
                    "name": "unlock_door",
                    "cost": 1.0,
                    "preconditions": {"has_key": True, "door_unlocked": False},
                    "effects": {"door_unlocked": True},
                },
            ]
        ),
        encoding="utf-8",
    )

    rc = main(
        [
            "plan",
            "--initial",
            str(init_file),
            "--actions",
            str(actions_file),
            "--goal-key",
            "door_unlocked",
            "--method",
            "astar",
        ]
    )
    assert rc == 0
    captured = capsys.readouterr()
    plan_out = json.loads(captured.out)
    assert len(plan_out["steps"]) == 2
    assert plan_out["steps"][0]["action"] == "pickup_key"
    assert plan_out["steps"][1]["action"] == "unlock_door"
