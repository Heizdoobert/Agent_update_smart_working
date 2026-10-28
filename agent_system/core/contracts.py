"""Core data contracts and abstract protocols for the cognitive agent framework."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol, Tuple, runtime_checkable


class CriticStatus(str, Enum):
    PASS = "PASS"
    REJECT = "REJECT"
    WARNING = "WARNING"


@dataclass
class DiagnosticItem:
    code: str
    message: str
    severity: str = "ERROR"  # ERROR, WARNING, INFO
    line: Optional[int] = None
    column: Optional[int] = None
    fix_recipe: Optional[str] = None


@dataclass
class CriticVerdict:
    status: CriticStatus
    score: float  # 0.0 to 100.0
    summary: str


@dataclass
class CriticReport:
    verdict: CriticVerdict
    diagnostics: List[DiagnosticItem] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    raw_artifact: Optional[str] = None

    @property
    def is_passed(self) -> bool:
        return self.verdict.status == CriticStatus.PASS and self.verdict.score >= 80.0


@dataclass
class TaskGoal:
    goal_id: str
    description: str
    constraints: List[str] = field(default_factory=list)
    target_output: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ActionStep:
    step_id: str
    action_type: str
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    expected_outcome: Optional[str] = None
    status: str = "PENDING"  # PENDING, RUNNING, COMPLETED, FAILED


@dataclass
class ThoughtNode:
    node_id: str
    thought: str
    parent_ids: List[str] = field(default_factory=list)
    children_ids: List[str] = field(default_factory=list)
    score: float = 0.0
    depth: int = 0
    visits: int = 0
    is_terminal: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Plan:
    plan_id: str
    goal_id: str
    steps: List[ActionStep] = field(default_factory=list)
    total_score: float = 0.0
    rationale: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TraceRecord:
    task_id: str
    step_index: int
    action: str
    observation: str
    reward: float = 0.0
    done: bool = False
    timestamp: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MemoryItem:
    item_id: str
    content: str
    category: str = "general"
    score: float = 1.0
    timestamp: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class CriticProtocol(Protocol):
    """Abstract protocol for artifact evaluation and compliance."""

    def validate(
        self, artifact: Any, context: Optional[Dict[str, Any]] = None
    ) -> CriticReport:
        """Validate artifact and return structured diagnostic report."""
        ...


@runtime_checkable
class ActionSpace(Protocol):
    """Abstract protocol defining available actions for a given state."""

    def get_available_actions(self, state: Any) -> List[Any]:
        """Return list of valid actions executable from state."""
        ...


@runtime_checkable
class TransitionModel(Protocol):
    """Abstract protocol defining state transitions and heuristic rollout."""

    def step(
        self, state: Any, action: Any
    ) -> Tuple[Any, float, bool, Dict[str, Any]]:
        """Execute action on state.

        Returns: (next_state, reward, is_terminal, info_dict)
        """
        ...
