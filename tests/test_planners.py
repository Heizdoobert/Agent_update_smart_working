"""Tests for A* and MCTS Planners."""

import time
import pytest

from agent_system.reasoning.astar import AStarPlanner
from agent_system.reasoning.mcts import MCTSPlanner
from agent_system.reasoning.transition import ActionDefinition, StateMachineTransitionModel, StateNode


@pytest.fixture
def workflow_environment():
    initial_state = StateNode(
        state_id="init",
        attributes={"auth": False, "data_loaded": False, "report_generated": False},
    )

    actions = [
        ActionDefinition(
            name="login",
            cost=1.0,
            preconditions={"auth": False},
            effects={"auth": True},
        ),
        ActionDefinition(
            name="load_data",
            cost=2.0,
            preconditions={"auth": True, "data_loaded": False},
            effects={"data_loaded": True},
        ),
        ActionDefinition(
            name="generate_report_efficient",
            cost=1.0,
            preconditions={"data_loaded": True, "report_generated": False},
            effects={"report_generated": True},
        ),
        ActionDefinition(
            name="expensive_shortcut",
            cost=20.0,
            preconditions={"auth": True, "report_generated": False},
            effects={"report_generated": True},
        ),
    ]

    model = StateMachineTransitionModel(actions)
    is_goal = lambda s: s.get("report_generated") is True

    return initial_state, model, is_goal


def test_astar_finds_optimal_path(workflow_environment):
    initial_state, model, is_goal = workflow_environment

    planner = AStarPlanner(model)
    t0 = time.time()
    plan = planner.plan(initial_state, is_goal, goal_id="generate_report")
    elapsed_ms = (time.time() - t0) * 1000

    assert plan is not None
    assert len(plan.steps) == 3
    # Verifies it selected the optimal (cheapest) path: login -> load_data -> generate_report_efficient (cost 4)
    step_names = [s.action_type for s in plan.steps]
    assert step_names == ["login", "load_data", "generate_report_efficient"]
    assert "expensive_shortcut" not in step_names
    # Sub-second latency check (<100ms)
    assert elapsed_ms < 100.0


def test_mcts_planner(workflow_environment):
    initial_state, model, is_goal = workflow_environment

    planner = MCTSPlanner(model, max_rollout_depth=10)
    t0 = time.time()
    plan = planner.plan(initial_state, is_goal, simulations=50, goal_id="mcts_report")
    elapsed_ms = (time.time() - t0) * 1000

    assert plan is not None
    assert len(plan.steps) >= 2
    # Check that execution of the plan reaches the goal
    state = initial_state
    for step in plan.steps:
        # Find action
        act = next(a for a in model.actions if a.name == step.action_type)
        state, _, _, _ = model.step(state, act)

    assert is_goal(state) is True
    # Fast rollout check (<100ms)
    assert elapsed_ms < 100.0
