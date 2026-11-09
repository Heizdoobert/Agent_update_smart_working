"""Opt-in LLM patcher for SelfReflector: asks a cheap Claude model to fix diagnostics the rule patcher cannot."""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Callable, List, Optional

from agent_system.core.contracts import DiagnosticItem

Patcher = Callable[[str, List[DiagnosticItem]], str]
RULE_FIXABLE = {"FORBIDDEN_IMPORT", "FORBIDDEN_CALL", "MISSING_RETURN_TYPE"}  # fixed by SelfReflector rules


def claude_patcher(model: str = "haiku", max_usd: float = 0.20, timeout: int = 120) -> Patcher:
    """Return a patcher that calls `claude -p` (no tools, no session, project settings only)."""
    real = Path.home() / ".local/bin/claude.real"  # NO_SANDBOX host binary; plain `claude` is a Docker wrapper
    exe = os.environ.get("AGENT_SYSTEM_CLAUDE") or (str(real) if real.exists() else "claude")

    def patch(artifact: str, diagnostics: List[DiagnosticItem]) -> str:
        diagnostics = [d for d in diagnostics if d.code not in RULE_FIXABLE]
        if not diagnostics:  # the reflector's rule patcher handles these for free
            return artifact
        issues = "\n".join(f"- line {d.line}: {d.code} {d.message}" for d in diagnostics)
        prompt = (
            "Fix the violations in this code. Reply with ONLY the complete corrected code, "
            f"no explanation, no markdown fences.\n\nViolations:\n{issues}\n\nCode:\n{artifact}"
        )
        proc = subprocess.run(
            [exe, "-p", "--model", model, "--output-format", "json", "--no-session-persistence",
             "--max-budget-usd", str(max_usd), "--setting-sources", "project", "--strict-mcp-config",
             "--disable-slash-commands", "--tools", ""],
            input=prompt, capture_output=True, text=True, timeout=timeout,
            env={**os.environ, "NO_SANDBOX": "1"},
        )
        if proc.returncode != 0:
            return artifact
        text = json.loads(proc.stdout).get("result", "").strip()
        fenced = re.match(r"^```[\w-]*\n(.*?)\n```$", text, re.S)
        return fenced.group(1) if fenced else text or artifact

    return patch


def default_patcher() -> Optional[Patcher]:
    """LLM patcher only when AGENT_SYSTEM_LLM_PATCH=1 (costs tokens, so never implicit)."""
    return claude_patcher() if os.environ.get("AGENT_SYSTEM_LLM_PATCH") == "1" else None
