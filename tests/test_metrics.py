"""Boundary tests for agent_system.metrics (module F-007, M1/M2/M4/M6).

Each threshold is tested on BOTH sides of the boundary (safe vs warn/critical).
"""

import json
import math

from agent_system import metrics as M
from agent_system.metrics import (
    context_usage_pct,
    flow_should_handoff,
    input_output_ratio,
    kv_cache_hit_rate,
    rollback_rate,
    self_verification_rate,
    token_shift_to_verification,
    tool_count,
)

# ── context_usage_pct: warn@30, critical@40 ────────────────────────────────

def test_context_safe_below_30():
    assert context_usage_pct(29, 100).level == "safe"


def test_context_warn_at_30():
    assert context_usage_pct(30, 100).level == "warn"


def test_context_critical_at_40():
    assert context_usage_pct(40, 100).level == "critical"


def test_context_critical_above_40():
    assert context_usage_pct(55, 100).level == "critical"


def test_context_no_data():
    m = context_usage_pct(None, None)
    assert m.level == "no_data"
    assert math.isnan(m.value)


# ── kv_cache_hit_rate: target >80 ──────────────────────────────────────────

def test_kv_safe_above_80():
    assert kv_cache_hit_rate(81, 100).level == "safe"


def test_kv_warn_near_80():
    assert kv_cache_hit_rate(65, 100).level == "warn"


def test_kv_critical_far_below_80():
    assert kv_cache_hit_rate(30, 100).level == "critical"


def test_kv_no_data():
    assert kv_cache_hit_rate(None, None).level == "no_data"


# ── input_output_ratio: <80:1 safe ─────────────────────────────────────────

def test_ratio_safe_under_80():
    assert input_output_ratio(79, 1).level == "safe"


def test_ratio_warn_over_80():
    assert input_output_ratio(85, 1).level == "warn"


def test_ratio_critical_very_high():
    assert input_output_ratio(200, 1).level == "critical"


def test_ratio_no_data():
    assert input_output_ratio(None, None).level == "no_data"


# ── tool_count: <15 safe, >30 prune ────────────────────────────────────────

def test_tool_safe_under_15():
    assert tool_count(14).level == "safe"


def test_tool_warn_15_to_30():
    assert tool_count(20).level == "warn"


def test_tool_critical_over_30():
    assert tool_count(31).level == "critical"


def test_tool_no_data():
    assert tool_count(None).level == "no_data"


# ── rollback_rate: <=0.5% safe ─────────────────────────────────────────────

def test_rollback_safe_at_0_5pct():
    assert rollback_rate(1, 200).level == "safe"  # 0.5%


def test_rollback_warn_over_0_5pct():
    assert rollback_rate(5, 200).level == "warn"  # 2.5%


def test_rollback_critical_storm():
    assert rollback_rate(50, 200).level == "critical"  # 25%


def test_rollback_no_data():
    assert rollback_rate(None, None).level == "no_data"


# ── self_verification_rate: >90% target ────────────────────────────────────

def test_selfverify_safe_above_90():
    assert self_verification_rate(91, 100).level == "safe"


def test_selfverify_warn_80_to_90():
    assert self_verification_rate(85, 100).level == "warn"


def test_selfverify_critical_below_80():
    assert self_verification_rate(71, 100).level == "critical"  # 5/7 real data


def test_selfverify_no_data():
    assert self_verification_rate(None, None).level == "no_data"


# ── token_shift_to_verification: ~70% target ───────────────────────────────

def test_tokenshift_safe_near_70():
    assert token_shift_to_verification(70, 100).level == "safe"


def test_tokenshift_warn_low():
    assert token_shift_to_verification(30, 100).level == "warn"


def test_tokenshift_no_data():
    assert token_shift_to_verification(None, None).level == "no_data"


# ── flow retry ceiling (M4, THIẾT §18.5) ───────────────────────────────────

def test_flow_ceiling_constant_is_2():
    assert M.FLOW_RETRY_CEILING == 2
    assert M.FLOW_RETRY_CEILING_SINGLE == 3


def test_flow_handoff_at_ceiling_parallel():
    # parallel loop: 2 failed rounds -> Human Gate
    assert flow_should_handoff(2, parallel=True) is True
    assert flow_should_handoff(1, parallel=True) is False


def test_flow_handoff_single_keeps_3():
    assert flow_should_handoff(3, parallel=False) is True
    assert flow_should_handoff(2, parallel=False) is False


def test_flow_never_allows_above_ceiling():
    # even a huge round count must hand off, never exceed the ceiling
    assert flow_should_handoff(999, parallel=True) is True


# ── CLI: metrics --json valid, 8 keys (M3) ─────────────────────────────────

def test_cli_metrics_json_valid_and_8_keys(tmp_path, monkeypatch, capsys):
    from agent_system.cli.main import build_parser

    monkeypatch.chdir(tmp_path)
    parser = build_parser()
    args = parser.parse_args(["metrics", "--json"])
    rc = args.func(args)
    assert rc == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert len(data) == 8
    names = {d["name"] for d in data}
    expected = {
        "context_usage_pct", "kv_cache_hit_rate", "input_output_ratio",
        "tool_count", "rollback_rate", "self_verification_rate",
        "token_shift_to_verification", "flow_retry_ceiling",
    }
    assert names == expected


def test_cli_metrics_never_crashes_on_missing_files(tmp_path, monkeypatch, capsys):
    from agent_system.cli.main import build_parser

    monkeypatch.chdir(tmp_path)  # empty dir: no progress, no features.json
    parser = build_parser()
    args = parser.parse_args(["metrics"])
    rc = args.func(args)
    assert rc == 0
    assert "KPI Dashboard" in capsys.readouterr().out


# ── alert path (M6): context >=40 emits reset guidance ─────────────────────

def test_alert_reset_guidance_at_45():
    m = context_usage_pct(45, 100)
    assert m.level == "critical"
    assert "RESET SESSION" in m.action.upper()
