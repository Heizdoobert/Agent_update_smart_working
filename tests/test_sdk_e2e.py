"""End-to-End (E2E) Integration Tests for the complete SDK Plugin Lifecycle."""

from __future__ import annotations

import io
import json
from pathlib import Path
import pytest

from agent_system.core.contracts import CriticStatus
from agent_system.reasoning.astar import AStarPlanner
from agent_system.reasoning.mcts import MCTSPlanner
from agent_system.reasoning.transition import ActionDefinition, StateMachineTransitionModel, StateNode
from agent_system.reflection.critic import CriticEngine
from agent_system.sdk.contracts import BasePlugin, PluginManifest, ProjectContext
from agent_system.sdk.registry import PluginRegistry
from agent_system.sdk.wizard import OnboardingWizard


def test_full_sdk_plugin_lifecycle_e2e(tmp_path):
    """Verify entire workflow:

    1. Scaffolding via OnboardingWizard.
    2. Discovery & loading via PluginRegistry.
    3. Rules bounding (<3KB).
    4. Reasoning integration with A* and MCTS.
    5. Critic integration.
    6. Clean deactivation (Plug-out).
    """
    proj_dir = tmp_path / "game_automation_proj"
    proj_dir.mkdir()

    # Step 1: Run Wizard
    simulated_input = io.StringIO(
        "game_bot\n"
        "Must verify screenshot before tapping; no raw coordinates.\n"
        "detect_ui, tap_play\n"
        "screen_critic\n"
    )
    wizard = OnboardingWizard(
        target_dir=proj_dir,
        stdin=simulated_input,
        stdout=io.StringIO(),
    )
    assert wizard.is_needed() is True
    scaffold_ok = wizard.run()
    assert scaffold_ok is True
    assert wizard.is_needed() is False

    # Customize generated plugin.py with realistic logic
    plugin_file = proj_dir / "plugin.py"
    plugin_code = """
from __future__ import annotations
from typing import List
from agent_system.core.contracts import CriticProtocol, CriticReport, CriticStatus, CriticVerdict, DiagnosticItem
from agent_system.reasoning.transition import ActionDefinition
from agent_system.sdk.contracts import BasePlugin

class CustomScreenCritic:
    def validate(self, artifact, context=None):
        content = str(artifact)
        if "raw_coordinates" in content:
            return CriticReport(
                verdict=CriticVerdict(status=CriticStatus.REJECT, score=40.0, summary="Raw coordinates forbidden"),
                diagnostics=[DiagnosticItem(code="FORBIDDEN_RAW_COORD", message="Found raw coordinates", severity="ERROR")]
            )
        return CriticReport(
            verdict=CriticVerdict(status=CriticStatus.PASS, score=100.0, summary="Screen Critic Passed")
        )

class GameBotPlugin(BasePlugin):
    def get_actions(self) -> List[ActionDefinition]:
        return [
            ActionDefinition(
                name="detect_ui",
                cost=1.0,
                preconditions={"screen_ready": True, "ui_found": False},
                effects={"ui_found": True},
            ),
            ActionDefinition(
                name="tap_play",
                cost=1.0,
                preconditions={"ui_found": True, "playing": False},
                effects={"playing": True},
            ),
        ]

    def get_critics(self) -> List[CriticProtocol]:
        return [CustomScreenCritic()]
"""
    plugin_file.write_text(plugin_code, encoding="utf-8")

    # Step 2: Discovery & Loading
    registry = PluginRegistry(allowed_roots=[proj_dir])
    manifest = registry.discover_manifest(proj_dir)
    assert manifest is not None
    assert manifest.name == "game_bot"

    plugin = registry.load_plugin(proj_dir)
    assert plugin is not None

    # Step 3: Rules Retrieval & Context Truncation
    rules = registry.get_project_rules()
    assert "Must verify screenshot before tapping" in rules
    assert len(rules.encode("utf-8")) <= 3072

    # Step 4: Reasoning Integration (A* & MCTS)
    plugin_actions = registry.get_all_actions()
    assert len(plugin_actions) == 2

    model = StateMachineTransitionModel(plugin_actions)
    init_state = StateNode(state_id="s0", attributes={"screen_ready": True, "ui_found": False, "playing": False})
    is_goal = lambda s: s.get("playing") is True

    # A* Planner
    astar = AStarPlanner(model)
    astar_plan = astar.plan(init_state, is_goal)
    assert astar_plan is not None
    assert len(astar_plan.steps) == 2
    assert [s.action_type for s in astar_plan.steps] == ["detect_ui", "tap_play"]

    # MCTS Planner
    mcts = MCTSPlanner(model, max_rollout_depth=10)
    mcts_plan = mcts.plan(init_state, is_goal, simulations=50)
    assert mcts_plan is not None
    assert len(mcts_plan.steps) == 2
    assert [s.action_type for s in mcts_plan.steps] == ["detect_ui", "tap_play"]

    # Step 5: Critic Integration
    domain_critics = registry.get_all_critics()
    assert len(domain_critics) == 1

    critic_engine = CriticEngine(critics=domain_critics)
    
    # Negative check (contains raw_coordinates)
    bad_code = "tap(raw_coordinates=(100, 200))"
    report_bad = critic_engine.evaluate(bad_code)
    assert report_bad.verdict.status == CriticStatus.REJECT
    assert any(d.code == "FORBIDDEN_RAW_COORD" for d in report_bad.diagnostics)

    # Positive check
    good_code = "tap(template='btn_play')"
    report_good = critic_engine.evaluate(good_code)
    assert report_good.verdict.status == CriticStatus.PASS
    assert report_good.verdict.score == 100.0

    # Step 6: Plug-out
    registry.unload_plugin("game_bot")
    assert registry.get_all_actions() == []
    assert registry.get_all_critics() == []
    assert registry.get_project_rules() == ""
