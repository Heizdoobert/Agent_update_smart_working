"""Critic adapters for Markdown prompt rules and Plugin Manifest configurations."""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from agent_system.core.contracts import (
    CriticProtocol,
    CriticReport,
    CriticStatus,
    CriticVerdict,
    DiagnosticItem,
)


class MarkdownRulesCritic:
    """Validates structural and budget invariants of Markdown prompt rules."""

    DEFAULT_MAX_BYTES = 3072  # 3KB context budget

    def __init__(self, max_bytes: int = DEFAULT_MAX_BYTES) -> None:
        self.max_bytes = max_bytes

    def validate(
        self, artifact: Any, context: Optional[Dict[str, Any]] = None
    ) -> CriticReport:
        text = str(artifact or "")
        diagnostics: List[DiagnosticItem] = []
        score = 100.0

        # Check 1: Top-level heading (# ...)
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        has_h1 = any(line.startswith("# ") for line in lines)
        if not has_h1:
            diagnostics.append(
                DiagnosticItem(
                    code="MISSING_TOP_HEADING",
                    message="Markdown rules document is missing a top-level '# ' heading.",
                    severity="WARNING",
                    fix_recipe="Add a top-level heading '# Project Operating Rules' at the beginning.",
                )
            )
            score -= 20.0

        # Check 2: Unclosed markdown code fences (```)
        fence_count = text.count("```")
        if fence_count % 2 != 0:
            diagnostics.append(
                DiagnosticItem(
                    code="UNCLOSED_CODE_FENCE",
                    message="Markdown text contains unclosed code fence (odd number of '```').",
                    severity="ERROR",
                    fix_recipe="Close open code block with '```' on a new line.",
                )
            )
            score -= 40.0

        # Check 3: Budget check
        encoded_len = len(text.encode("utf-8"))
        if encoded_len > self.max_bytes:
            diagnostics.append(
                DiagnosticItem(
                    code="RULES_EXCEED_BUDGET",
                    message=f"Markdown rules payload ({encoded_len} bytes) exceeds budget of {self.max_bytes} bytes.",
                    severity="WARNING",
                    fix_recipe=f"Condense guidelines to fit within {self.max_bytes} bytes.",
                )
            )
            score -= 15.0

        score = max(0.0, score)
        has_error = any(d.severity == "ERROR" for d in diagnostics)
        has_warning = any(d.severity == "WARNING" for d in diagnostics)

        if has_error or score < 60.0:
            status = CriticStatus.REJECT
        elif has_warning:
            status = CriticStatus.WARNING
        else:
            status = CriticStatus.PASS

        suggestions = [
            f"[{d.code}] {d.message} -> Fix: {d.fix_recipe}"
            for d in diagnostics
            if d.fix_recipe
        ]

        return CriticReport(
            verdict=CriticVerdict(
                status=status,
                score=score,
                summary=f"MarkdownRulesCritic evaluation: {status.value} (Score: {score:.1f}/100)",
            ),
            diagnostics=diagnostics,
            suggestions=suggestions,
            raw_artifact=text,
        )


class PluginManifestCritic:
    """Validates structural configuration invariants of agent_plugin.json manifests."""

    SEMVER_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")

    def validate(
        self, artifact: Any, context: Optional[Dict[str, Any]] = None
    ) -> CriticReport:
        diagnostics: List[DiagnosticItem] = []
        score = 100.0

        data = artifact
        if isinstance(artifact, str):
            try:
                data = json.loads(artifact)
            except Exception as e:
                return CriticReport(
                    verdict=CriticVerdict(
                        status=CriticStatus.REJECT,
                        score=0.0,
                        summary=f"Manifest JSON syntax error: {e}",
                    ),
                    diagnostics=[
                        DiagnosticItem(
                            code="INVALID_JSON",
                            message=str(e),
                            severity="ERROR",
                            fix_recipe="Format artifact as valid JSON.",
                        )
                    ],
                )

        if not isinstance(data, dict):
            return CriticReport(
                verdict=CriticVerdict(
                    status=CriticStatus.REJECT,
                    score=0.0,
                    summary="Manifest must be a JSON object / dictionary.",
                ),
                diagnostics=[
                    DiagnosticItem(
                        code="INVALID_MANIFEST_TYPE",
                        message="Expected dictionary but got "
                        + type(data).__name__,
                        severity="ERROR",
                    )
                ],
            )

        # Check required fields
        if "name" not in data or not data["name"]:
            diagnostics.append(
                DiagnosticItem(
                    code="MISSING_REQUIRED_FIELD",
                    message="Manifest is missing required field 'name'.",
                    severity="ERROR",
                    fix_recipe="Specify a 'name' string in manifest.",
                )
            )
            score -= 40.0
        else:
            name_val = str(data["name"])
            if not name_val.isidentifier():
                diagnostics.append(
                    DiagnosticItem(
                        code="INVALID_NAME_IDENTIFIER",
                        message=f"Plugin name '{name_val}' is not a valid Python identifier.",
                        severity="ERROR",
                        fix_recipe="Use letters, numbers, and underscores; cannot start with a digit.",
                    )
                )
                score -= 30.0

        if "version" not in data or not data["version"]:
            diagnostics.append(
                DiagnosticItem(
                    code="MISSING_REQUIRED_FIELD",
                    message="Manifest is missing required field 'version'.",
                    severity="ERROR",
                    fix_recipe="Specify a semver 'version' (e.g. '0.1.0').",
                )
            )
            score -= 30.0
        elif not self.SEMVER_PATTERN.match(str(data["version"])):
            diagnostics.append(
                DiagnosticItem(
                    code="INVALID_VERSION_FORMAT",
                    message=f"Version '{data['version']}' does not match semver format (X.Y.Z).",
                    severity="WARNING",
                    fix_recipe="Format version as 'MAJOR.MINOR.PATCH'.",
                )
            )
            score -= 10.0

        if "rules_path" in data and data["rules_path"]:
            rpath = str(data["rules_path"])
            if not rpath.endswith(".md"):
                diagnostics.append(
                    DiagnosticItem(
                        code="INVALID_RULES_EXTENSION",
                        message=f"Rules path '{rpath}' should point to a markdown (.md) file.",
                        severity="WARNING",
                        fix_recipe="Change extension to '.md'.",
                    )
                )
                score -= 10.0

        score = max(0.0, score)
        has_error = any(d.severity == "ERROR" for d in diagnostics)
        has_warning = any(d.severity == "WARNING" for d in diagnostics)

        if has_error or score < 80.0:
            status = CriticStatus.REJECT
        elif has_warning:
            status = CriticStatus.WARNING
        else:
            status = CriticStatus.PASS

        suggestions = [
            f"[{d.code}] {d.message} -> Fix: {d.fix_recipe}"
            for d in diagnostics
            if d.fix_recipe
        ]

        return CriticReport(
            verdict=CriticVerdict(
                status=status,
                score=score,
                summary=f"PluginManifestCritic evaluation: {status.value} (Score: {score:.1f}/100)",
            ),
            diagnostics=diagnostics,
            suggestions=suggestions,
            raw_artifact=str(data),
        )
