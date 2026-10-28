"""In-Memory Self-Reflection Engine with bounded iterations and oscillation detection."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from agent_system.core.contracts import CriticReport, DiagnosticItem
from agent_system.reflection.critic import CriticEngine


@dataclass
class ReflectionResult:
    """Result of self-reflection and repair loop."""
    success: bool
    final_artifact: str
    iterations: int
    history: List[CriticReport] = field(default_factory=list)
    patched: bool = False
    message: str = ""


class SelfReflector:
    """Orchestrates in-memory self-reflection: evaluate -> reflect -> patch -> re-evaluate."""

    def __init__(
        self,
        critic: CriticEngine,
        custom_patcher: Optional[Callable[[str, List[DiagnosticItem]], str]] = None,
        max_iterations: int = 3,
    ):
        self.critic = critic
        self.custom_patcher = custom_patcher
        self.max_iterations = min(5, max(1, max_iterations))

    def reflect_and_patch(
        self,
        initial_artifact: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> ReflectionResult:
        """Run self-reflection loop with hard iteration bound and cycle detection."""
        current_artifact = initial_artifact
        history: List[CriticReport] = []
        seen_signatures: List[str] = []
        patched_any = False

        for iteration in range(1, self.max_iterations + 1):
            report = self.critic.evaluate(current_artifact, context=context)
            history.append(report)

            # Check if artifact meets compliance criteria
            if report.is_passed:
                return ReflectionResult(
                    success=True,
                    final_artifact=current_artifact,
                    iterations=iteration,
                    history=history,
                    patched=patched_any,
                    message=f"Achieved passing compliance score ({report.verdict.score}/100) on iteration {iteration}.",
                )

            # Generate state signature to detect rule oscillation loops
            diag_sig = "|".join(sorted(f"{d.code}:{d.line}" for d in report.diagnostics))
            content_hash = hashlib.sha256(current_artifact.encode("utf-8")).hexdigest()[:12]
            combined_sig = f"{content_hash}_{diag_sig}"

            if combined_sig in seen_signatures:
                return ReflectionResult(
                    success=False,
                    final_artifact=current_artifact,
                    iterations=iteration,
                    history=history,
                    patched=patched_any,
                    message="Oscillation detected: conflicting rule corrections produced recurring state.",
                )
            seen_signatures.append(combined_sig)

            # If reached max iterations, stop
            if iteration >= self.max_iterations:
                break

            # Apply patches based on diagnostics
            patched_code = self._apply_fixes(current_artifact, report.diagnostics)
            if patched_code == current_artifact:
                # No fixes could be applied deterministically
                return ReflectionResult(
                    success=False,
                    final_artifact=current_artifact,
                    iterations=iteration,
                    history=history,
                    patched=patched_any,
                    message="Unresolvable diagnostics: deterministic patcher cannot fix remaining violations.",
                )

            current_artifact = patched_code
            patched_any = True

        return ReflectionResult(
            success=False,
            final_artifact=current_artifact,
            iterations=self.max_iterations,
            history=history,
            patched=patched_any,
            message=f"Max iteration limit ({self.max_iterations}) reached without achieving pass score.",
        )

    def _apply_fixes(self, artifact: str, diagnostics: List[DiagnosticItem]) -> str:
        """Apply deterministic fix recipes for common static rule violations."""
        if self.custom_patcher:
            try:
                custom_result = self.custom_patcher(artifact, diagnostics)
                if custom_result != artifact:
                    return custom_result
            except Exception:
                pass

        lines = artifact.splitlines()

        for diag in diagnostics:
            # Fix 1: Forbidden import removal
            if diag.code == "FORBIDDEN_IMPORT" and diag.line is not None:
                line_idx = diag.line - 1
                if 0 <= line_idx < len(lines):
                    # Comment out or remove line
                    lines[line_idx] = f"# [Self-Reflection: removed forbidden import] # {lines[line_idx]}"

            # Fix 2: Dangerous call removal
            elif diag.code == "FORBIDDEN_CALL" and diag.line is not None:
                line_idx = diag.line - 1
                if 0 <= line_idx < len(lines):
                    lines[line_idx] = re.sub(
                        r"\b(eval|exec)\((.*?)\)",
                        r"# [Dangerous call removed] \2",
                        lines[line_idx],
                    )

            # Fix 3: Missing return type annotation in Python
            elif diag.code == "MISSING_RETURN_TYPE" and diag.line is not None:
                line_idx = diag.line - 1
                if 0 <= line_idx < len(lines):
                    line_str = lines[line_idx]
                    if line_str.rstrip().endswith(":"):
                        lines[line_idx] = line_str.rstrip()[:-1] + " -> Any:"

        return "\n".join(lines)
