"""Tests for Unified CLI interface."""

import json
import tempfile
from pathlib import Path
import pytest

from agent_system import __version__
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
    assert f"agent-system {__version__}" in captured.out


def test_cli_package_invocation_no_runtime_warnings():
    import subprocess
    # Verify python -m agent_system and python -m agent_system.cli run cleanly with zero stderr warnings
    for mod in ["agent_system", "agent_system.cli", "agent_system.cli.main"]:
        proc = subprocess.run(
            ["python3", "-m", mod, "--version"],
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0
        assert f"agent-system {__version__}" in proc.stdout
        assert "RuntimeWarning" not in proc.stderr
        assert proc.stderr.strip() == ""


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


def test_cli_plan_goal_value_primitives(tmp_path, capsys):
    init_file = tmp_path / "init_num.json"
    init_file.write_text(json.dumps({"stage": 0}), encoding="utf-8")

    actions_file = tmp_path / "actions_num.json"
    actions_file.write_text(
        json.dumps(
            [
                {
                    "name": "advance_stage",
                    "cost": 1.0,
                    "preconditions": {"stage": 0},
                    "effects": {"stage": 5},
                }
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
            "stage",
            "--goal-value",
            "5",
            "--method",
            "astar",
        ]
    )
    assert rc == 0
    captured = capsys.readouterr()
    plan_out = json.loads(captured.out)
    assert len(plan_out["steps"]) == 1
    assert plan_out["steps"][0]["action"] == "advance_stage"

    init_bool = tmp_path / "init_bool.json"
    init_bool.write_text(json.dumps({"done": False}), encoding="utf-8")
    actions_bool = tmp_path / "actions_bool.json"
    actions_bool.write_text(
        json.dumps([{"name": "finish", "cost": 1.0, "preconditions": {"done": False}, "effects": {"done": True}}]),
        encoding="utf-8",
    )
    rc_bool = main(
        [
            "plan",
            "--initial",
            str(init_bool),
            "--actions",
            str(actions_bool),
            "--goal-key",
            "done",
            "--goal-value",
            "true",
            "--method",
            "mcts",
        ]
    )
    assert rc_bool == 0
    captured_bool = capsys.readouterr()
    plan_bool = json.loads(captured_bool.out)
    assert len(plan_bool["steps"]) == 1
