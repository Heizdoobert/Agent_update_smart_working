"""Deterministic A* heuristic planner for optimal path search."""

from __future__ import annotations

import heapq
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from agent_system.core.contracts import ActionStep, Plan
from agent_system.reasoning.transition import ActionDefinition, StateMachineTransitionModel, StateNode


class AStarPlanner:
    """A* heuristic search planner guaranteeing mathematically optimal shortest-cost plans."""

    def __init__(
        self,
        transition_model: StateMachineTransitionModel,
        heuristic_fn: Optional[Callable[[StateNode], float]] = None,
        max_expansions: int = 2000,
    ):
        self.model = transition_model
        self.heuristic = heuristic_fn or (lambda s: 0.0)
        self.max_expansions = max_expansions

    def plan(
        self,
        initial_state: StateNode,
        is_goal: Callable[[StateNode], bool],
        goal_id: str = "goal",
    ) -> Optional[Plan]:
        """Execute A* search to synthesize an optimal plan reaching the goal."""
        start_time = time.time()
        # Priority queue item: (f_score, tie_breaker, g_score, state, path_of_actions)
        counter = 0
        h_start = self.heuristic(initial_state)
        frontier: List[Tuple[float, int, float, StateNode, List[ActionDefinition]]] = []
        heapq.heappush(frontier, (h_start, counter, 0.0, initial_state, []))

        best_cost: Dict[str, float] = {initial_state.state_id: 0.0}
        expansions = 0

        while frontier and expansions < self.max_expansions:
            f, _, g, current_state, path = heapq.heappop(frontier)
            expansions += 1

            # Goal check
            if is_goal(current_state):
                elapsed = time.time() - start_time
                steps = [
                    ActionStep(
                        step_id=f"step_{idx+1}",
                        action_type=act.name,
                        description=f"Apply {act.name}",
                        parameters=act.effects,
                        expected_outcome=f"State attributes: {act.effects}",
                        status="PENDING",
                    )
                    for idx, act in enumerate(path)
                ]
                return Plan(
                    plan_id=f"astar_plan_{int(time.time()*1000)}",
                    goal_id=goal_id,
                    steps=steps,
                    total_score=max(0.0, 100.0 - g),  # Lower cost = higher score
                    rationale=f"Optimal A* path found in {expansions} expansions ({elapsed*1000:.1f}ms). Total cost: {g}",
                    metadata={"cost": g, "expansions": expansions, "elapsed_ms": elapsed * 1000},
                )

            # Prune if a cheaper path to this state was already processed
            if g > best_cost.get(current_state.state_id, float("inf")):
                continue

            available_actions = self.model.get_available_actions(current_state)
            for action in available_actions:
                next_state, _, _, _ = self.model.step(current_state, action)
                new_g = g + action.cost

                if new_g < best_cost.get(next_state.state_id, float("inf")):
                    best_cost[next_state.state_id] = new_g
                    counter += 1
                    h = self.heuristic(next_state)
                    f_score = new_g + h
                    heapq.heappush(
                        frontier,
                        (f_score, counter, new_g, next_state, path + [action]),
                    )

        return None
