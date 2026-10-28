"""Monte Carlo Tree Search (MCTS) Planner for stochastic/rollout reasoning spaces."""

from __future__ import annotations

import math
import random
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from agent_system.core.contracts import ActionStep, Plan
from agent_system.reasoning.transition import ActionDefinition, StateMachineTransitionModel, StateNode


class MCTSNode:
    """Node in MCTS search tree holding state, action, visits, and value."""

    def __init__(
        self,
        state: StateNode,
        parent: Optional[MCTSNode] = None,
        action: Optional[ActionDefinition] = None,
        untried_actions: Optional[List[ActionDefinition]] = None,
    ):
        self.state = state
        self.parent = parent
        self.action = action
        self.children: List[MCTSNode] = []
        self.visits: int = 0
        self.total_value: float = 0.0
        self.untried_actions = untried_actions or []

    @property
    def q_value(self) -> float:
        return self.total_value / max(1, self.visits)

    def uct_score(self, exploration_constant: float = 1.414) -> float:
        if self.visits == 0:
            return float("inf")
        if not self.parent or self.parent.visits == 0:
            return self.q_value
        exploration = exploration_constant * math.sqrt(
            math.log(self.parent.visits) / self.visits
        )
        return self.q_value + exploration


class MCTSPlanner:
    """MCTS Planner executing multi-branch rollout simulations."""

    def __init__(
        self,
        transition_model: StateMachineTransitionModel,
        evaluation_fn: Optional[Callable[[StateNode], float]] = None,
        exploration_constant: float = 1.414,
        max_rollout_depth: int = 15,
    ):
        self.model = transition_model
        self.eval_fn = evaluation_fn or (lambda s: 0.0)
        self.c = exploration_constant
        self.max_depth = max_rollout_depth

    def plan(
        self,
        initial_state: StateNode,
        is_goal: Callable[[StateNode], bool],
        simulations: int = 100,
        goal_id: str = "mcts_goal",
    ) -> Optional[Plan]:
        start_time = time.time()
        initial_actions = self.model.get_available_actions(initial_state)
        root = MCTSNode(
            state=initial_state,
            untried_actions=list(initial_actions),
        )

        for _ in range(simulations):
            # 1. Selection
            node = root
            while not node.untried_actions and node.children:
                # Pick child with highest UCT
                node = max(node.children, key=lambda c: c.uct_score(self.c))

            # 2. Expansion
            if node.untried_actions and not is_goal(node.state):
                action = node.untried_actions.pop()
                next_state, _, _, _ = self.model.step(node.state, action)
                next_actions = self.model.get_available_actions(next_state)
                child_node = MCTSNode(
                    state=next_state,
                    parent=node,
                    action=action,
                    untried_actions=list(next_actions),
                )
                node.children.append(child_node)
                node = child_node

            # 3. Simulation (Rollout)
            sim_state = node.state
            sim_depth = 0
            sim_reward = 0.0

            while sim_depth < self.max_depth and not is_goal(sim_state):
                actions = self.model.get_available_actions(sim_state)
                if not actions:
                    break
                # Random rollout policy
                chosen_act = random.choice(actions)
                sim_state, r, _, _ = self.model.step(sim_state, chosen_act)
                sim_reward += r
                sim_depth += 1

            if is_goal(sim_state):
                sim_reward += 100.0  # Big goal reward
            else:
                sim_reward += self.eval_fn(sim_state)

            # 4. Backpropagation
            curr: Optional[MCTSNode] = node
            while curr is not None:
                curr.visits += 1
                curr.total_value += sim_reward
                curr = curr.parent

        # Extract best trajectory from root by highest visits
        trajectory: List[ActionDefinition] = []
        curr = root
        while curr.children:
            best_child = max(curr.children, key=lambda c: c.visits)
            if best_child.action:
                trajectory.append(best_child.action)
            curr = best_child
            if is_goal(curr.state):
                break

        if not trajectory:
            return None

        elapsed = time.time() - start_time
        steps = [
            ActionStep(
                step_id=f"mcts_step_{idx+1}",
                action_type=act.name,
                description=f"Execute {act.name}",
                parameters=act.effects,
                expected_outcome=f"Effects: {act.effects}",
                status="PENDING",
            )
            for idx, act in enumerate(trajectory)
        ]

        return Plan(
            plan_id=f"mcts_plan_{int(time.time()*1000)}",
            goal_id=goal_id,
            steps=steps,
            total_score=round(max(0.0, min(100.0, root.q_value)), 2),
            rationale=f"MCTS synthesized path in {simulations} simulations ({elapsed*1000:.1f}ms). Steps: {len(steps)}",
            metadata={"simulations": simulations, "elapsed_ms": elapsed * 1000},
        )
