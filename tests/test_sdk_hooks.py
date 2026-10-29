"""Tests for Plugin Hook Event Bus: on_before_plan, on_after_plan, on_critic_report."""

from __future__ import annotations

from typing import Any, Optional
import pytest

from agent_system.core.contracts import (
    ActionStep,
    CriticReport,
    CriticStatus,
    CriticVerdict,
    DiagnosticItem,
    Plan,
)
from agent_system.reasoning.transition import StateNode
from agent_system.sdk.contracts import BasePlugin, PluginManifest
from agent_system.sdk.registry import PluginRegistry


class AuditingPlugin(BasePlugin):
    def __init__(self, manifest: PluginManifest, context=None):
        super().__init__(manifest, context)
        self.before_plan_called = False
        self.recorded_initial_state = None

    def on_before_plan(self, initial_state: Any, goal: Any) -> None:
        self.before_plan_called = True
        self.recorded_initial_state = initial_state

    def on_after_plan(self, plan: Optional[Plan]) -> Optional[Plan]:
        if plan is not None:
            # Decorate rationale with plugin audit trail
            plan.rationale += " [Audited by AuditingPlugin]"
        return plan

    def on_critic_report(self, report: CriticReport) -> CriticReport:
        # Augment report with extra diagnostic info
        report.suggestions.append("Hook suggestion from AuditingPlugin")
        return report


def test_plugin_event_bus_lifecycle():
    registry = PluginRegistry()
    manifest = PluginManifest(name="auditor_plugin")
    plugin = AuditingPlugin(manifest)
    
    # Register manually to test event dispatching
    registry._active_plugins[manifest.name] = plugin
    
    # 1. Test before_plan event
    init_state = StateNode("s0", {"ready": True})
    goal_fn = lambda s: s.get("ready") is True
    registry.trigger_before_plan(init_state, goal_fn)
    
    assert plugin.before_plan_called is True
    assert plugin.recorded_initial_state == init_state
    
    # 2. Test after_plan event
    test_plan = Plan(plan_id="p1", goal_id="g1", steps=[], total_score=1.0, rationale="Base rationale")
    augmented_plan = registry.trigger_after_plan(test_plan)
    assert augmented_plan is not None
    assert "[Audited by AuditingPlugin]" in augmented_plan.rationale
    
    # 3. Test critic_report event
    base_report = CriticReport(
        verdict=CriticVerdict(status=CriticStatus.PASS, score=90.0, summary="OK"),
        diagnostics=[],
        suggestions=["Base suggestion"],
    )
    augmented_report = registry.trigger_critic_report(base_report)
    assert "Hook suggestion from AuditingPlugin" in augmented_report.suggestions
