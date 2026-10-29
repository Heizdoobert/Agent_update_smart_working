"""Tests for SDK Contracts, Manifest, and Markdown Code Fence Preservation."""

from __future__ import annotations

import json
from pathlib import Path
import pytest

from agent_system.core.contracts import CriticProtocol, CriticReport, CriticStatus, CriticVerdict
from agent_system.core.truncator import StructuralTruncator
from agent_system.reasoning.transition import ActionDefinition
from agent_system.sdk.contracts import (
    BasePlugin,
    PluginManifest,
    ProjectContext,
)


def test_markdown_fence_preservation():
    """Verify that truncating markdown inside a code block safely closes the fence."""
    markdown_with_code = (
        "# Project Rules\n\n"
        "Here are the code guidelines:\n"
        "```python\n"
        "def important_rule():\n"
        "    return 'Never do this' * 100\n"
        "    # " + ("long content " * 300) + "\n"
        "```\n"
        "End of rules."
    )
    
    # Truncate to a tight limit that cuts midway inside the python code block
    truncated = StructuralTruncator.truncate_text(markdown_with_code, max_bytes=500)
    
    assert len(truncated.encode("utf-8")) <= 500
    assert "...[TRUNCATED]" in truncated
    # Code fence count must be even (opened and closed)
    assert truncated.count("```") % 2 == 0
    # Must contain closing code block before suffix
    assert "```\n...[TRUNCATED]" in truncated or "```...[TRUNCATED]" in truncated


def test_plugin_manifest_serialization():
    """Verify PluginManifest dataclass and dictionary/JSON conversion."""
    manifest = PluginManifest(
        name="game_bot",
        version="1.0.0",
        description="Airtest game bot plugin",
        entrypoint="bot_plugin:GameBotPlugin",
        rules_path=".agent/rules.md",
        actions=["tap_button", "swipe_screen"],
        metadata={"domain": "gaming"},
    )
    
    data = manifest.to_dict()
    assert data["name"] == "game_bot"
    assert data["version"] == "1.0.0"
    assert data["entrypoint"] == "bot_plugin:GameBotPlugin"
    assert data["actions"] == ["tap_button", "swipe_screen"]
    
    # Load from dict
    reloaded = PluginManifest.from_dict(data)
    assert reloaded == manifest


def test_base_plugin_lifecycle_and_defaults(tmp_path):
    """Verify BasePlugin default implementations and lifecycle hooks."""
    manifest = PluginManifest(name="sample_plugin")
    ctx = ProjectContext(project_root=tmp_path, rules_content="Custom Project Rules")
    
    class SamplePlugin(BasePlugin):
        def __init__(self, manifest: PluginManifest, context: ProjectContext | None = None):
            super().__init__(manifest, context)
            self.loaded = False
            self.unloaded = False
            
        def on_load(self) -> None:
            self.loaded = True
            
        def on_unload(self) -> None:
            self.unloaded = True

        def get_actions(self) -> list[ActionDefinition]:
            return [
                ActionDefinition(
                    name="custom_action",
                    cost=1.0,
                    preconditions={"ready": True},
                    effects={"done": True},
                )
            ]

    plugin = SamplePlugin(manifest, ctx)
    assert not plugin.loaded
    plugin.on_load()
    assert plugin.loaded
    
    assert plugin.get_rules() == "Custom Project Rules"
    actions = plugin.get_actions()
    assert len(actions) == 1
    assert actions[0].name == "custom_action"
    
    critics = plugin.get_critics()
    assert critics == []
    
    plugin.on_unload()
    assert plugin.unloaded
