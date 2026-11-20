#!/usr/bin/env python3
"""
Subagent Orchestrator & Token Optimization Router
------------------------------------------------
Enforces hierarchical agent dispatching:
- Session Model: Lead Architect / Manager (final critic, synthesis, planning)
- Worker Subagents: Light models for mechanical tasks to maximize speed and minimize token consumption.
"""

from enum import Enum
from typing import Dict, Any, List, Tuple
# Memory hardening utilities
from memory_layer import hardening


class TaskTier(str, Enum):
    MECHANICAL = "flash_lite"      # Scanning, grepping, running tests, reading raw logs, memory retrieval
    IMPLEMENTATION = "flash"       # Code generation, unit bugfixes, test drafting
    ARCHITECTURAL = "inherit"      # Deep reasoning, cross-system architecture, multi-factor security review


TASK_ROUTING: Dict[str, TaskTier] = {
    # Mechanical tasks -> flash_lite
    "scan_codebase": TaskTier.MECHANICAL,
    "run_tests": TaskTier.MECHANICAL,
    "read_logs": TaskTier.MECHANICAL,
    "memory_lookup": TaskTier.MECHANICAL,
    "lint_and_format": TaskTier.MECHANICAL,
    "file_search": TaskTier.MECHANICAL,

    # Implementation tasks -> flash
    "implement_feature": TaskTier.IMPLEMENTATION,
    "fix_bug": TaskTier.IMPLEMENTATION,
    "write_unit_tests": TaskTier.IMPLEMENTATION,
    "refactor_module": TaskTier.IMPLEMENTATION,

    # Architectural tasks -> inherit / pro
    "system_architecture": TaskTier.ARCHITECTURAL,
    "security_audit": TaskTier.ARCHITECTURAL,
    "final_signoff": TaskTier.ARCHITECTURAL,
}


def resolve_subagent_model(task_type: str) -> str:
    """Resolve the optimal token‑saving model for an assigned sub‑task."""
    tier = TASK_ROUTING.get(task_type.lower(), TaskTier.MECHANICAL)
    return tier.value


def dispatch_with_hardening(
    task_id: str,
    task_type: str,
    role: str,
    prompt: str,
    project_id: str,
    workspace: str = "inherit",
) -> Tuple[Dict[str, Any], str]:
    """Prepare a WAL entry, format the sub‑agent payload, and return both.

    The caller is responsible for invoking the sub‑agent using the returned payload
    and subsequently calling ``commit.commit_write`` with the returned UID upon
    successful completion, or ``rollback.rollback_write`` on failure.
    """
    # Prepare a deterministic UID and WAL entry.
    uid = hardening.prepare_write(
        project_id=project_id,
        task_id=task_id,
        insight_type="subagent_dispatch",
        insight_text=prompt,
        metadata={"task_type": task_type, "role": role},
    )
    payload = format_subagent_dispatch(
        task_id=task_id,
        task_type=task_type,
        role=role,
        prompt=prompt,
        workspace=workspace,
    )
    return payload, uid


def format_subagent_dispatch(
    task_id: str,
    task_type: str,
    role: str,
    prompt: str,
    workspace: str = "inherit",
) -> Dict[str, Any]:
    """Prepare a standardized, token‑optimized ``invoke_subagent`` payload."""
    model = resolve_subagent_model(task_type)
    return {
        "TaskId": task_id,
        "TypeName": "self",
        "Role": role,
        "Model": model,
        "Workspace": workspace,
        "Prompt": prompt,
    }


if __name__ == "__main__":
    # Self‑test routing
    assert resolve_subagent_model("scan_codebase") == "flash_lite"
    assert resolve_subagent_model("run_tests") == "flash_lite"
    assert resolve_subagent_model("implement_feature") == "flash"
    assert resolve_subagent_model("system_architecture") == "inherit"
    print("Subagent Orchestrator Routing Tests: ALL PASSED")

"""
Subagent Orchestrator & Token Optimization Router
------------------------------------------------
Enforces hierarchical agent dispatching:
- Session Model: Lead Architect / Manager (final critic, synthesis, planning)
- Worker Subagents: Light models for mechanical tasks to maximize speed and minimize token consumption.
"""

from enum import Enum
from typing import Dict, Any, List, Tuple
# Memory hardening utilities
from memory_layer import hardening, commit, rollback


class TaskTier(str, Enum):
    MECHANICAL = "flash_lite"      # Scanning, grepping, running tests, reading raw logs, memory retrieval
    IMPLEMENTATION = "flash"       # Code generation, unit bugfixes, test drafting
    ARCHITECTURAL = "inherit"      # Deep reasoning, cross-system architecture, multi-factor security review


TASK_ROUTING: Dict[str, TaskTier] = {
    # Mechanical tasks -> flash_lite
    "scan_codebase": TaskTier.MECHANICAL,
    "run_tests": TaskTier.MECHANICAL,
    "read_logs": TaskTier.MECHANICAL,
    "memory_lookup": TaskTier.MECHANICAL,
    "lint_and_format": TaskTier.MECHANICAL,
    "file_search": TaskTier.MECHANICAL,

    # Implementation tasks -> flash
    "implement_feature": TaskTier.IMPLEMENTATION,
    "fix_bug": TaskTier.IMPLEMENTATION,
    "write_unit_tests": TaskTier.IMPLEMENTATION,
    "refactor_module": TaskTier.IMPLEMENTATION,

    # Architectural tasks -> inherit / pro
    "system_architecture": TaskTier.ARCHITECTURAL,
    "security_audit": TaskTier.ARCHITECTURAL,
    "final_signoff": TaskTier.ARCHITECTURAL,
}


def resolve_subagent_model(task_type: str) -> str:
    """Resolve the optimal token-saving model for an assigned sub-task."""
    tier = TASK_ROUTING.get(task_type.lower(), TaskTier.MECHANICAL)
    return tier.value


def dispatch_with_hardening(
    task_id: str,
    task_type: str,
    role: str,
    prompt: str,
    project_id: str,
    workspace: str = "inherit",
) -> Tuple[Dict[str, Any], str]:
    """Prepare a WAL entry, format the subagent payload, and return both.

    The caller is responsible for invoking the subagent using the returned payload
    and subsequently calling ``commit.commit_write`` with the returned UID upon
    successful completion, or ``rollback.rollback_write`` on failure.
    """
    # Prepare a deterministic UID and WAL entry.
    uid = hardening.prepare_write(
        project_id=project_id,
        task_id=task_id,
        insight_type="subagent_dispatch",
        insight_text=prompt,
        metadata={"task_type": task_type, "role": role},
    )
    payload = format_subagent_dispatch(
        task_id=task_id,
        task_type=task_type,
        role=role,
        prompt=prompt,
        workspace=workspace,
    )
    return payload, uid

    task_id: str,
    task_type: str,
    role: str,
    prompt: str,
    workspace: str = "inherit",
) -> Dict[str, Any]:
    """Prepare a standardized, token-optimized invoke_subagent payload."""
    model = resolve_subagent_model(task_type)
    return {
        "TaskId": task_id,
        "TypeName": "self",
        "Role": role,
        "Model": model,
        "Workspace": workspace,
        "Prompt": prompt,
    }


if __name__ == "__main__":
    # Self-test routing
    assert resolve_subagent_model("scan_codebase") == "flash_lite"
    assert resolve_subagent_model("run_tests") == "flash_lite"
    assert resolve_subagent_model("implement_feature") == "flash"
    assert resolve_subagent_model("system_architecture") == "inherit"
    print("Subagent Orchestrator Routing Tests: ALL PASSED")
