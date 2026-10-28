"""State and Transition models for planning and reasoning."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple


@dataclass(frozen=True)
class StateNode:
    """Immutable state representation for search algorithms."""
    state_id: str
    attributes: Dict[str, Any] = field(default_factory=dict)
    is_terminal: bool = False

    def get(self, key: str, default: Any = None) -> Any:
        return self.attributes.get(key, default)


@dataclass
class ActionDefinition:
    """Action definition with preconditions, effects, and execution cost."""
    name: str
    cost: float = 1.0
    preconditions: Dict[str, Any] = field(default_factory=dict)
    effects: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_applicable(self, state: StateNode) -> bool:
        """Check if action preconditions are met by current state attributes."""
        for k, v in self.preconditions.items():
            if state.get(k) != v:
                return False
        return True

    def apply(self, state: StateNode) -> StateNode:
        """Apply action effects to produce new state."""
        new_attrs = dict(state.attributes)
        new_attrs.update(self.effects)
        # Unique deterministic state id derived from sorted attributes
        attr_sig = ",".join(f"{k}={v}" for k, v in sorted(new_attrs.items()))
        return StateNode(
            state_id=f"state({attr_sig})",
            attributes=new_attrs,
            is_terminal=False,
        )


class StateMachineTransitionModel:
    """Domain-agnostic transition model for discrete state-space planning."""

    def __init__(self, actions: List[ActionDefinition]):
        self.actions = actions

    def get_available_actions(self, state: StateNode) -> List[ActionDefinition]:
        """Return actions whose preconditions are satisfied."""
        return [a for a in self.actions if a.is_applicable(state)]

    def step(
        self, state: StateNode, action: ActionDefinition
    ) -> Tuple[StateNode, float, bool, Dict[str, Any]]:
        """Transition state by applying action. Reward is negative of cost."""
        next_state = action.apply(state)
        cost = action.cost
        reward = -cost
        return next_state, reward, next_state.is_terminal, {}
