"""Core interfaces, contracts, and primitives for agent_system."""

from .contracts import (
    ActionStep,
    CriticReport,
    CriticStatus,
    CriticVerdict,
    DiagnosticItem,
    MemoryItem,
    Plan,
    TaskGoal,
    ThoughtNode,
    TraceRecord,
    ActionSpace,
    CriticProtocol,
    TransitionModel,
)
from .truncator import StructuralTruncator

__all__ = [
    "ActionStep",
    "CriticReport",
    "CriticStatus",
    "CriticVerdict",
    "DiagnosticItem",
    "MemoryItem",
    "Plan",
    "TaskGoal",
    "ThoughtNode",
    "TraceRecord",
    "ActionSpace",
    "CriticProtocol",
    "TransitionModel",
    "StructuralTruncator",
]
