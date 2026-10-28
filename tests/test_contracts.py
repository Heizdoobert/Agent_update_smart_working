"""Unit tests for Core Contracts and StructuralTruncator."""

import json
import pytest

from agent_system.core.contracts import (
    ActionSpace,
    ActionStep,
    CriticProtocol,
    CriticReport,
    CriticStatus,
    CriticVerdict,
    DiagnosticItem,
    MemoryItem,
    Plan,
    TaskGoal,
    ThoughtNode,
    TraceRecord,
    TransitionModel,
)
from agent_system.core.truncator import StructuralTruncator


def test_core_contracts_instantiation():
    goal = TaskGoal(
        goal_id="g1",
        description="Build cognitive agent",
        constraints=["offline", "domain-agnostic"],
    )
    assert goal.goal_id == "g1"
    assert len(goal.constraints) == 2

    node = ThoughtNode(
        node_id="n1",
        thought="Explore A* approach",
        score=0.95,
        depth=1,
    )
    assert node.score == 0.95
    assert node.depth == 1

    verdict = CriticVerdict(status=CriticStatus.PASS, score=92.0, summary="Good")
    report = CriticReport(
        verdict=verdict,
        diagnostics=[
            DiagnosticItem(
                code="WARN01",
                message="Consider adding docstrings",
                severity="WARNING",
                line=12,
            )
        ],
    )
    assert report.is_passed is True

    step = ActionStep(
        step_id="s1",
        action_type="inspect",
        description="Inspect system state",
    )
    plan = Plan(plan_id="p1", goal_id="g1", steps=[step], total_score=88.5)
    assert len(plan.steps) == 1

    trace = TraceRecord(
        task_id="t1",
        step_index=0,
        action="search",
        observation="found 3 results",
        reward=1.0,
        done=False,
    )
    assert trace.reward == 1.0

    mem = MemoryItem(item_id="m1", content="FTS index doc", category="guide")
    assert mem.category == "guide"


def test_protocols_runtime_checkable():
    class DummyCritic:
        def validate(self, artifact, context=None):
            return CriticReport(
                verdict=CriticVerdict(CriticStatus.PASS, 100.0, "OK")
            )

    class DummyActionSpace:
        def get_available_actions(self, state):
            return ["left", "right"]

    class DummyTransition:
        def step(self, state, action):
            return state, 1.0, True, {}

    assert isinstance(DummyCritic(), CriticProtocol)
    assert isinstance(DummyActionSpace(), ActionSpace)
    assert isinstance(DummyTransition(), TransitionModel)


def test_truncator_utf8_vietnamese_safety():
    # Vietnamese multi-byte string: "Hệ thống tác tử thông minh tự hành đa tác vụ nhận thức cấp cao"
    repeated = "Hệ thống tác tử thông minh tự hành nhận thức. " * 50
    encoded_len = len(repeated.encode("utf-8"))
    assert encoded_len > 1500

    limit = 300
    truncated = StructuralTruncator.truncate_text(repeated, max_bytes=limit)
    truncated_bytes = truncated.encode("utf-8")
    assert len(truncated_bytes) <= limit
    # Must decode cleanly without UnicodeDecodeError
    assert truncated_bytes.decode("utf-8") == truncated
    assert "...[TRUNCATED]" in truncated


def test_truncator_json_validity():
    large_payload = {
        "items": [
            {"id": i, "name": f"Tác vụ số {i}", "data": "Dữ liệu thử nghiệm bộ nhớ " * 5}
            for i in range(50)
        ],
        "status": "active",
        "description": "Kiểm thử cắt tỉa JSON",
    }
    raw_json = json.dumps(large_payload, ensure_ascii=False)
    assert len(raw_json.encode("utf-8")) > 3072

    truncated_str = StructuralTruncator.truncate_payload(raw_json, max_bytes=1024)
    assert len(truncated_str.encode("utf-8")) <= 1024

    # Must be valid parseable JSON!
    parsed = json.loads(truncated_str)
    assert isinstance(parsed, dict)
    assert "status" in parsed
