"""Batch Prompt Distillation and Teleprompter Optimization."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from agent_system.core.contracts import TraceRecord


@dataclass
class PromptCandidate:
    prompt_id: str
    system_prompt: str
    few_shot_examples: List[Dict[str, str]] = field(default_factory=list)
    average_score: float = 0.0
    token_estimate: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def render(self) -> str:
        parts = [self.system_prompt]
        if self.few_shot_examples:
            parts.append("\n## Examples:")
            for idx, ex in enumerate(self.few_shot_examples, 1):
                parts.append(f"### Example {idx}\nInput: {ex.get('input', '')}\nOutput: {ex.get('output', '')}")
        return "\n\n".join(parts)


class DistillationEngine:
    """Offline batch optimizer compressing teacher reasoning traces into compact student prompts."""

    def __init__(self, trace_store: Optional[List[TraceRecord]] = None):
        self.traces = trace_store or []

    def record_trace(self, trace: TraceRecord) -> None:
        self.traces.append(trace)

    def extract_distilled_examples(
        self, min_reward: float = 0.5, max_examples: int = 5
    ) -> List[Dict[str, str]]:
        """Filter traces by high reward to construct exemplary few-shot demonstrations."""
        successful_traces = [t for t in self.traces if t.reward >= min_reward]
        examples: List[Dict[str, str]] = []

        for t in successful_traces[:max_examples]:
            examples.append(
                {
                    "input": f"Task: {t.task_id} (Step {t.step_index})",
                    "output": f"Action: {t.action} -> Observation: {t.observation}",
                }
            )

        return examples

    def generate_candidate_prompts(
        self,
        base_instruction: str,
        rules: Optional[List[str]] = None,
        few_shot_pool: Optional[List[Dict[str, str]]] = None,
    ) -> List[PromptCandidate]:
        """Synthesize multiple candidate prompt variants (compact, detailed, rule-focused)."""
        rule_list = rules or []
        examples = few_shot_pool or self.extract_distilled_examples()

        candidates: List[PromptCandidate] = []

        # Candidate 1: Minimal concise instruction
        c1_text = f"{base_instruction}\n" + "\n".join(f"- {r}" for r in rule_list[:3])
        candidates.append(
            PromptCandidate(
                prompt_id="cand_minimal",
                system_prompt=c1_text,
                few_shot_examples=examples[:1],
                token_estimate=len(c1_text.split()),
            )
        )

        # Candidate 2: Full distilled instruction with top 3 examples
        c2_text = f"{base_instruction}\n\nStrict Operational Guidelines:\n" + "\n".join(f"{i+1}. {r}" for i, r in enumerate(rule_list))
        candidates.append(
            PromptCandidate(
                prompt_id="cand_full_distilled",
                system_prompt=c2_text,
                few_shot_examples=examples[:3],
                token_estimate=len(c2_text.split()),
            )
        )

        return candidates

    def benchmark_and_optimize(
        self,
        candidates: List[PromptCandidate],
        benchmark_dataset: List[Dict[str, Any]],
        evaluator_fn: Callable[[PromptCandidate, Dict[str, Any]], float],
    ) -> PromptCandidate:
        """Evaluate candidate prompts on benchmark cases and select highest performing prompt."""
        if not candidates:
            raise ValueError("No prompt candidates to benchmark.")

        for cand in candidates:
            total_score = 0.0
            for case in benchmark_dataset:
                score = evaluator_fn(cand, case)
                total_score += score
            cand.average_score = round(total_score / max(1, len(benchmark_dataset)), 2)

        # Sort by highest average score; break ties with lower token count (more compact)
        ranked = sorted(
            candidates,
            key=lambda c: (c.average_score, -c.token_estimate),
            reverse=True,
        )

        return ranked[0]

    def export_distilled_prompt(self, candidate: PromptCandidate, output_path: Path) -> None:
        """Save winning prompt candidate to disk as JSON."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "prompt_id": candidate.prompt_id,
            "average_score": candidate.average_score,
            "system_prompt": candidate.system_prompt,
            "few_shot_examples": candidate.few_shot_examples,
            "rendered": candidate.render(),
        }
        output_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
