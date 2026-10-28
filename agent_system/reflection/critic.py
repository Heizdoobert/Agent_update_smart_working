"""Critic Coordinator and base schema validator."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from agent_system.core.contracts import (
    CriticProtocol,
    CriticReport,
    CriticStatus,
    CriticVerdict,
    DiagnosticItem,
)


class SchemaCritic:
    """Validates structural JSON or dictionary schema invariants."""

    def __init__(self, required_keys: Optional[List[str]] = None):
        self.required_keys = required_keys or []

    def validate(
        self, artifact: Any, context: Optional[Dict[str, Any]] = None
    ) -> CriticReport:
        diagnostics: List[DiagnosticItem] = []
        parsed = artifact

        if isinstance(artifact, str):
            try:
                parsed = json.loads(artifact)
            except Exception as e:
                diagnostics.append(
                    DiagnosticItem(
                        code="INVALID_JSON",
                        message=f"Artifact is not valid JSON: {e}",
                        severity="ERROR",
                        fix_recipe="Format string as valid JSON syntax",
                    )
                )
                return CriticReport(
                    verdict=CriticVerdict(
                        status=CriticStatus.REJECT,
                        score=0.0,
                        summary="Artifact failed JSON parsing",
                    ),
                    diagnostics=diagnostics,
                    raw_artifact=str(artifact),
                )

        if isinstance(parsed, dict):
            for k in self.required_keys:
                if k not in parsed:
                    diagnostics.append(
                        DiagnosticItem(
                            code="MISSING_KEY",
                            message=f"Missing required key '{k}'",
                            severity="ERROR",
                            fix_recipe=f"Add '{k}' to dictionary",
                        )
                    )

        if diagnostics:
            score = max(0.0, 100.0 - len(diagnostics) * 25.0)
            status = CriticStatus.PASS if score >= 80.0 else CriticStatus.REJECT
            return CriticReport(
                verdict=CriticVerdict(
                    status=status,
                    score=score,
                    summary=f"Found {len(diagnostics)} schema violations",
                ),
                diagnostics=diagnostics,
                raw_artifact=str(artifact),
            )

        return CriticReport(
            verdict=CriticVerdict(
                status=CriticStatus.PASS,
                score=100.0,
                summary="Schema validated perfectly",
            ),
            diagnostics=[],
            raw_artifact=str(artifact),
        )


class CriticEngine:
    """Coordinates multiple critics and computes aggregated compliance verdict."""

    def __init__(self, critics: Optional[List[CriticProtocol]] = None):
        self.critics: List[CriticProtocol] = critics or []

    def register_critic(self, critic: CriticProtocol) -> None:
        self.critics.append(critic)

    def evaluate(
        self, artifact: Any, context: Optional[Dict[str, Any]] = None
    ) -> CriticReport:
        if not self.critics:
            return CriticReport(
                verdict=CriticVerdict(
                    status=CriticStatus.PASS,
                    score=100.0,
                    summary="No critics registered; passed by default",
                ),
                raw_artifact=str(artifact),
            )

        all_diagnostics: List[DiagnosticItem] = []
        scores: List[float] = []

        for critic in self.critics:
            report = critic.validate(artifact, context=context)
            all_diagnostics.extend(report.diagnostics)
            scores.append(report.verdict.score)

        avg_score = sum(scores) / len(scores)
        has_error = any(d.severity == "ERROR" for d in all_diagnostics)

        status = CriticStatus.PASS if avg_score >= 80.0 and not has_error else CriticStatus.REJECT

        suggestions = [
            f"[{d.code}] {d.message} -> Suggested fix: {d.fix_recipe}"
            for d in all_diagnostics
            if d.fix_recipe
        ]

        return CriticReport(
            verdict=CriticVerdict(
                status=status,
                score=round(avg_score, 2),
                summary=f"Aggregated evaluation across {len(self.critics)} critics: {status.value} (Score: {avg_score:.1f}/100)",
            ),
            diagnostics=all_diagnostics,
            suggestions=suggestions,
            raw_artifact=str(artifact),
        )
