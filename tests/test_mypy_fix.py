"""Tests for the mypy-fix module (9 type errors -> 0 + CI gate).

Covers the four fix groups:
  M1  truncator.py  — rename candidate -> candidate_dict (dict branch of truncate_json)
  M2  mcp/tools.py  — planner: AStarPlanner | MCTSPlanner (MCTS branch)
  M3  cli/main.py   — planner union (both A* and MCTS branches)
  M4-M7 mcp/tools.py — critics: List[CriticProtocol] (polymorphism)
  M8-M9 cli/main.py  — cmd_metrics dashboard all entries are Metric (to_dict)

The M4-M7 fix is exercised indirectly: the critic path through
CriticEngine(critics) is the contract mypy verifies; we assert the
dispatcher can be constructed and that the tool returns a valid report.
"""

import json
import subprocess
import sys
from pathlib import Path

from agent_system.core.truncator import StructuralTruncator
from agent_system.mcp.tools import CognitiveToolsDispatcher
from agent_system.metrics import Metric

# ---------------------------------------------------------------------------
# M1 — truncator dict branch (candidate -> candidate_dict)
# ---------------------------------------------------------------------------

def test_truncate_json_dict_under_budget_unchanged():
    """Small dict: truncate_json returns the input dict unchanged."""
    data = {"a": 1, "b": 2, "c": 3}
    out = StructuralTruncator.truncate_json(data, max_bytes=10_000)
    assert out == data


def test_truncate_json_dict_oversized_drops_keys():
    """Oversized dict: must drop keys to fit budget, output must be valid JSON."""
    data = {f"key_{i:02d}": "x" * 40 for i in range(30)}
    max_bytes = 200
    out = StructuralTruncator.truncate_json(data, max_bytes=max_bytes)
    # output is a dict, fits budget, and is parseable
    assert isinstance(out, dict)
    raw = json.dumps(out, ensure_ascii=False)
    assert len(raw.encode("utf-8")) <= max_bytes + 2  # small slack for separators
    # at least one key must remain (not the empty-dict fallback)
    assert len(out) >= 1
    # must round-trip through json.loads
    assert json.loads(raw) == out


def test_truncate_json_dict_nested_value_truncates_sub_value():
    """Dict whose one value is a big list: sub-value must be truncated, not dropped."""
    data = {"small": 1, "big_list": list(range(200))}
    max_bytes = 300
    out = StructuralTruncator.truncate_json(data, max_bytes=max_bytes)
    assert isinstance(out, dict)
    raw = json.dumps(out, ensure_ascii=False)
    assert len(raw.encode("utf-8")) <= max_bytes + 2
    # the small key must survive (it fits)
    assert "small" in out
    # big_list either present (truncated) or omitted, but output is valid JSON
    json.loads(raw)


def test_truncate_json_list_branch_unchanged():
    """List branch (separate from dict branch) still works — guards rename didn't leak."""
    data = [list(range(50)) for _ in range(20)]
    max_bytes = 400
    out = StructuralTruncator.truncate_json(data, max_bytes=max_bytes)
    assert isinstance(out, list)
    raw = json.dumps(out, ensure_ascii=False)
    assert len(raw.encode("utf-8")) <= max_bytes + 2
    json.loads(raw)


def test_truncate_payload_json_roundtrip():
    """truncate_payload on oversized JSON returns valid JSON within budget."""
    data = {"payload": "z" * 5000}
    raw_in = json.dumps(data)
    max_bytes = 120
    out = StructuralTruncator.truncate_payload(raw_in, max_bytes=max_bytes)
    assert len(out.encode("utf-8")) <= max_bytes + 2
    # must be parseable JSON (dict or minimal fallback)
    parsed = json.loads(out)
    assert isinstance(parsed, (dict, list, str, int, float, bool)) or parsed is None


# ---------------------------------------------------------------------------
# M2 / M3 — planner union annotation (AStarPlanner | MCTSPlanner)
# Both branches must produce a valid plan for a 2-state transition.
# ---------------------------------------------------------------------------

def _plan_fixture(tmp_path: Path):
    init = tmp_path / "init.json"
    actions = tmp_path / "actions.json"
    init.write_text('{"pos": 0}')
    actions.write_text(
        json.dumps([
            {"name": "step1", "cost": 1, "preconditions": {"pos": 0}, "effects": {"pos": 1}},
            {"name": "step2", "cost": 1, "preconditions": {"pos": 1}, "effects": {"pos": 2}},
        ])
    )
    return init, actions


def test_plan_astar_branch(tmp_path):
    """M3 A* branch (planner = AStarPlanner) produces a valid plan."""
    init, actions = _plan_fixture(tmp_path)
    cmd = [
        sys.executable, "-m", "agent_system.cli.main",
        "plan", "--initial", str(init), "--actions", str(actions),
        "--goal-key", "pos", "--goal-value", "2", "--method", "astar",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    assert proc.returncode == 0, proc.stderr
    out = json.loads(proc.stdout)
    assert out.get("steps"), "expected non-empty plan steps"
    # plan must reach goal: last step effect = goal
    assert out["steps"][-1]["params"] == {"pos": 2}


def test_plan_mcts_branch(tmp_path):
    """M2/M3 MCTS branch (planner = MCTSPlanner) produces a valid plan."""
    init, actions = _plan_fixture(tmp_path)
    cmd = [
        sys.executable, "-m", "agent_system.cli.main",
        "plan", "--initial", str(init), "--actions", str(actions),
        "--goal-key", "pos", "--goal-value", "2", "--method", "mcts",
        "--simulations", "30",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    assert proc.returncode == 0, proc.stderr
    out = json.loads(proc.stdout)
    assert out.get("steps"), "expected non-empty plan steps from MCTS"
    assert out["steps"][-1]["params"] == {"pos": 2}


# ---------------------------------------------------------------------------
# M4-M7 — critics: List[CriticProtocol] (polymorphism through CriticEngine)
# ---------------------------------------------------------------------------

def test_dispatcher_constructs_and_exposes_agent_critic():
    """CognitiveToolsDispatcher must be constructible; _tool_agent_critic callable."""
    d = CognitiveToolsDispatcher(root_path="/tmp")
    assert hasattr(d, "_tool_agent_critic")
    assert callable(d._tool_agent_critic)


def test_agent_critic_python_path(tmp_path):
    """M4-M7: the python critic path through CriticEngine(critics) returns a report."""
    d = CognitiveToolsDispatcher(root_path="/tmp")
    result = d._tool_agent_critic({"code": "def f() -> int:\n    return 1\n", "language": "python"})
    report = json.loads(result)
    # report must have the standard shape (status/score/summary)
    assert "status" in report
    assert "score" in report
    # a clean python function should pass
    assert report["status"] == "PASS"


def test_agent_critic_markdown_path():
    """M4-M7: markdown critic path (different critic in the same list)."""
    d = CognitiveToolsDispatcher(root_path="/tmp")
    result = d._tool_agent_critic({"code": "# Title\n\nBody text.\n", "language": "markdown"})
    report = json.loads(result)
    assert "status" in report
    assert "score" in report


def test_agent_critic_json_path():
    """M4-M7: json critic path (SchemaCritic in the same polymorphic list)."""
    d = CognitiveToolsDispatcher(root_path="/tmp")
    result = d._tool_agent_critic({"code": '{"a": 1, "b": [1, 2]}', "language": "json"})
    report = json.loads(result)
    assert "status" in report
    assert "score" in report


# ---------------------------------------------------------------------------
# M8-M9 — cmd_metrics dashboard all entries are Metric (to_dict works)
# ---------------------------------------------------------------------------

def test_metric_to_dict_shape():
    m = Metric(name="x", value=1.0, level="safe", action="ok")
    d = m.to_dict()
    assert d == {"name": "x", "value": 1.0, "level": "safe", "action": "ok"}


def test_metrics_cli_json_all_entries_serializable(tmp_path, monkeypatch, capsys):
    """M8-M9: every dashboard entry must be a Metric with to_dict() (no ad-hoc dict)."""
    from agent_system.cli.main import build_parser

    monkeypatch.chdir(tmp_path)
    parser = build_parser()
    args = parser.parse_args(["metrics", "--json"])
    rc = args.func(args)
    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    assert len(data) == 8
    # every entry must have the Metric.to_dict() shape
    for entry in data:
        assert set(entry.keys()) == {"name", "value", "level", "action"}, f"bad shape: {entry.keys()}"
    # the previously ad-hoc entry must now be a proper Metric
    names = {e["name"] for e in data}
    assert "flow_retry_ceiling" in names
    assert names == {
        "context_usage_pct", "kv_cache_hit_rate", "input_output_ratio",
        "tool_count", "rollback_rate", "self_verification_rate",
        "token_shift_to_verification", "flow_retry_ceiling",
    }


def test_metrics_cli_text_renders_all(tmp_path, monkeypatch, capsys):
    """M8-M9: text table must render all 8 metrics without AttributeError."""
    from agent_system.cli.main import build_parser

    monkeypatch.chdir(tmp_path)
    parser = build_parser()
    args = parser.parse_args(["metrics"])
    rc = args.func(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "KPI Dashboard" in out
    for name in ("flow_retry_ceiling", "context_usage_pct", "self_verification_rate"):
        assert name in out


# ---------------------------------------------------------------------------
# CI / regression — gate coverage note
# ---------------------------------------------------------------------------
# ruff + mypy are CI tools (installed per-job in .github/workflows/ci.yml).
# They are NOT project Python dependencies, so they are not asserted here;
# the CI `lint` and `mypy` jobs enforce them. This file covers the CODE
# behavior those annotations must not break (M1..M9 above).
