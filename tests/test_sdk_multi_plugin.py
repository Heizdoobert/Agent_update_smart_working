"""Tests for Multi-Plugin Composite Action Space and Precedence Resolution."""

from __future__ import annotations

import json
from pathlib import Path
import pytest

from agent_system.reasoning.transition import ActionDefinition
from agent_system.sdk.contracts import BasePlugin, PluginManifest
from agent_system.sdk.registry import PluginRegistry


class LowPriorityPlugin(BasePlugin):
    def get_actions(self):
        return [
            ActionDefinition(name="common_action", cost=5.0, effects={"tier": "low"}),
            ActionDefinition(name="low_only_action", cost=1.0, effects={"low": True}),
        ]


class HighPriorityPlugin(BasePlugin):
    def get_actions(self):
        return [
            ActionDefinition(name="common_action", cost=1.0, effects={"tier": "high"}),
            ActionDefinition(name="high_only_action", cost=1.0, effects={"high": True}),
        ]


def test_multi_plugin_precedence_and_deduplication():
    registry = PluginRegistry()
    
    # Low priority manifest (priority=50)
    manifest_low = PluginManifest(name="low_plugin", priority=50)
    plugin_low = LowPriorityPlugin(manifest_low)
    
    # High priority manifest (priority=100)
    manifest_high = PluginManifest(name="high_plugin", priority=100)
    plugin_high = HighPriorityPlugin(manifest_high)
    
    registry._active_plugins["low_plugin"] = plugin_low
    registry._active_plugins["high_plugin"] = plugin_high
    
    actions = registry.get_all_actions()
    
    # Should have 3 unique actions: common_action (high priority override), high_only_action, low_only_action
    action_names = {a.name for a in actions}
    assert action_names == {"common_action", "high_only_action", "low_only_action"}
    assert len(actions) == 3
    
    # Verify that common_action came from high priority plugin (cost 1.0, tier="high")
    common = next(a for a in actions if a.name == "common_action")
    assert common.cost == 1.0
    assert common.effects.get("tier") == "high"


def test_discover_and_load_multiple_plugins_in_directory(tmp_path):
    # Create plugins/ directory with 2 sub-plugins
    plugins_dir = tmp_path / "plugins"
    plugins_dir.mkdir()
    
    p1 = plugins_dir / "plugin_a"
    p1.mkdir()
    (p1 / "agent_plugin.json").write_text(json.dumps({"name": "plugin_a", "priority": 10}), encoding="utf-8")
    
    p2 = plugins_dir / "plugin_b"
    p2.mkdir()
    (p2 / "agent_plugin.json").write_text(json.dumps({"name": "plugin_b", "priority": 20}), encoding="utf-8")
    
    registry = PluginRegistry(allowed_roots=[tmp_path])
    loaded = registry.discover_and_load_all(plugins_dir)
    assert len(loaded) == 2
    assert "plugin_a" in [p.manifest.name for p in loaded]
    assert "plugin_b" in [p.manifest.name for p in loaded]


def test_multi_plugin_rules_context_budget_truncation():
    from agent_system.sdk.contracts import ProjectContext
    
    registry = PluginRegistry()
    
    # Plugin 1 provides 2000 bytes of rules
    p1 = BasePlugin(
        manifest=PluginManifest(name="p1"),
        context=ProjectContext(project_root="/tmp", rules_content="A" * 2000),
    )
    # Plugin 2 provides 2000 bytes of rules
    p2 = BasePlugin(
        manifest=PluginManifest(name="p2"),
        context=ProjectContext(project_root="/tmp", rules_content="B" * 2000),
    )
    
    registry._active_plugins["p1"] = p1
    registry._active_plugins["p2"] = p2
    
    combined_rules = registry.get_project_rules()
    assert len(combined_rules.encode("utf-8")) <= 3072
    assert "...[TRUNCATED]" in combined_rules
    assert combined_rules.startswith("A" * 100)

