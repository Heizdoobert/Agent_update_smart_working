"""Core data contracts and abstract protocols for the cognitive agent framework."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Protocol, runtime_checkable


class CriticStatus(StrEnum):
    PASS = "PASS"
    REJECT = "REJECT"
    WARNING = "WARNING"


@dataclass
class DiagnosticItem:
    code: str
    message: str
    severity: str = "ERROR"  # ERROR, WARNING, INFO
    line: int | None = None
    column: int | None = None
    fix_recipe: str | None = None


@dataclass
class CriticVerdict:
    status: CriticStatus
    score: float  # 0.0 to 100.0
    summary: str


@dataclass
class CriticReport:
    verdict: CriticVerdict
    diagnostics: list[DiagnosticItem] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    raw_artifact: str | None = None

    @property
    def is_passed(self) -> bool:
        return self.verdict.status == CriticStatus.PASS and self.verdict.score >= 80.0


@dataclass
class TaskGoal:
    goal_id: str
    description: str
    constraints: list[str] = field(default_factory=list)
    target_output: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ActionStep:
    step_id: str
    action_type: str
    description: str
    parameters: dict[str, Any] = field(default_factory=dict)
    expected_outcome: str | None = None
    status: str = "PENDING"  # PENDING, RUNNING, COMPLETED, FAILED


@dataclass
class ThoughtNode:
    node_id: str
    thought: str
    parent_ids: list[str] = field(default_factory=list)
    children_ids: list[str] = field(default_factory=list)
    score: float = 0.0
    depth: int = 0
    visits: int = 0
    is_terminal: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Plan:
    plan_id: str
    goal_id: str
    steps: list[ActionStep] = field(default_factory=list)
    total_score: float = 0.0
    rationale: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class TraceRecord:
    task_id: str
    step_index: int
    action: str
    observation: str
    reward: float = 0.0
    done: bool = False
    timestamp: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class MemoryItem:
    item_id: str
    content: str
    category: str = "general"
    score: float = 1.0
    timestamp: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class CriticProtocol(Protocol):
    """Abstract protocol for artifact evaluation and compliance."""

    def validate(
        self, artifact: Any, context: dict[str, Any] | None = None
    ) -> CriticReport:
        """Validate artifact and return structured diagnostic report."""
        ...


@runtime_checkable
class ActionSpace(Protocol):
    """Abstract protocol defining available actions for a given state."""

    def get_available_actions(self, state: Any) -> list[Any]:
        """Return list of valid actions executable from state."""
        ...


@runtime_checkable
class TransitionModel(Protocol):
    """Abstract protocol defining state transitions and heuristic rollout."""

    def step(
        self, state: Any, action: Any
    ) -> tuple[Any, float, bool, dict[str, Any]]:
        """Execute action on state.

        Returns: (next_state, reward, is_terminal, info_dict)
        """
        ...
