"""Tests for Batch Prompt Distillation Engine."""

import json
import tempfile
from pathlib import Path
import pytest

from agent_system.core.contracts import TraceRecord
from agent_system.distillation.distiller import DistillationEngine, PromptCandidate


def test_distillation_example_extraction():
    engine = DistillationEngine()
    engine.record_trace(TraceRecord("t1", 0, "read_spec", "spec loaded", reward=1.0))
    engine.record_trace(TraceRecord("t1", 1, "bad_step", "error occurred", reward=-0.5))
    engine.record_trace(TraceRecord("t1", 2, "heal_error", "healed successfully", reward=1.0))

    examples = engine.extract_distilled_examples(min_reward=0.5)
    assert len(examples) == 2
    assert "read_spec" in examples[0]["output"]
    assert "heal_error" in examples[1]["output"]


def test_distillation_candidate_generation_and_optimization():
    engine = DistillationEngine()
    # Add a high-reward trace
    engine.record_trace(TraceRecord("t1", 0, "optimal_plan", "passed", reward=1.0))

    candidates = engine.generate_candidate_prompts(
        base_instruction="You are an autonomous cognitive agent.",
        rules=["Never make up coordinates", "Always check invariants"],
    )

    assert len(candidates) >= 2

    # Benchmark dataset
    dataset = [
        {"test_id": "case1", "expected_rule": "Never make up coordinates"},
        {"test_id": "case2", "expected_rule": "Always check invariants"},
    ]

    # Evaluator giving higher score if candidate includes both rules
    def evaluator(cand: PromptCandidate, case: dict) -> float:
        score = 50.0
        if case["expected_rule"] in cand.system_prompt:
            score += 50.0
        return score

    best = engine.benchmark_and_optimize(candidates, dataset, evaluator)
    assert best is not None
    assert best.average_score >= 80.0
    rendered = best.render()
    assert "You are an autonomous cognitive agent." in rendered


def test_export_distilled_prompt():
    engine = DistillationEngine()
    cand = PromptCandidate(
        prompt_id="test_cand",
        system_prompt="Execute tasks cleanly.",
        average_score=95.0,
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        out_file = Path(tmpdir) / "distilled.json"
        engine.export_distilled_prompt(cand, out_file)
        assert out_file.exists()

        data = json.loads(out_file.read_text(encoding="utf-8"))
        assert data["prompt_id"] == "test_cand"
        assert data["average_score"] == 95.0
