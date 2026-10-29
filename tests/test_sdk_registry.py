"""Tests for PluginRegistry: dynamic loading, path whitelisting, and isolation."""

from __future__ import annotations

import json
from pathlib import Path
import pytest

from agent_system.core.contracts import CriticProtocol, CriticReport, CriticStatus, CriticVerdict, DiagnosticItem
from agent_system.reasoning.transition import ActionDefinition
from agent_system.sdk.contracts import BasePlugin, PluginManifest, ProjectContext
from agent_system.sdk.registry import PluginRegistry


@pytest.fixture
def mock_plugin_project(tmp_path):
    """Create a temporary project folder with rules, manifest, and plugin code."""
    proj_dir = tmp_path / "sample_project"
    proj_dir.mkdir()
    
    agent_dir = proj_dir / ".agent"
    agent_dir.mkdir()
    
    # 1. Project rules markdown
    rules_file = agent_dir / "rules.md"
    rules_file.write_text("# Custom Project Rules\n- Rule 1: Always type hint\n", encoding="utf-8")
    
    # 2. Plugin code implementing BasePlugin
    plugin_py = proj_dir / "my_plugin.py"
    plugin_code = """
from agent_system.core.contracts import CriticReport, CriticStatus, CriticVerdict, DiagnosticItem
from agent_system.reasoning.transition import ActionDefinition
from agent_system.sdk.contracts import BasePlugin

class DummyCritic:
    def validate(self, artifact, context=None):
        return CriticReport(
            verdict=CriticVerdict(status=CriticStatus.PASS, score=95.0, summary="Domain Critic Pass"),
            diagnostics=[]
        )

class SampleDomainPlugin(BasePlugin):
    def __init__(self, manifest, context=None):
        super().__init__(manifest, context)
        self.activated = False

    def on_load(self):
        self.activated = True

    def on_unload(self):
        self.activated = False

    def get_actions(self):
        return [
            ActionDefinition(name="domain_deploy", cost=2.0, preconditions={"build": True}, effects={"deployed": True})
        ]

    def get_critics(self):
        return [DummyCritic()]
"""
    plugin_py.write_text(plugin_code, encoding="utf-8")
    
    # 3. Manifest file
    manifest = {
        "name": "sample_domain_plugin",
        "version": "1.0.0",
        "entrypoint": "my_plugin:SampleDomainPlugin",
        "rules_path": ".agent/rules.md",
    }
    manifest_file = proj_dir / "agent_plugin.json"
    manifest_file.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    
    return proj_dir


def test_plugin_registry_load_and_unload(mock_plugin_project):
    registry = PluginRegistry(allowed_roots=[mock_plugin_project])
    
    # Discovery
    manifest = registry.discover_manifest(mock_plugin_project)
    assert manifest is not None
    assert manifest.name == "sample_domain_plugin"
    
    # Load
    plugin = registry.load_plugin(mock_plugin_project)
    assert plugin is not None
    assert getattr(plugin, "activated", False) is True
    
    # Verify rules, actions, and critics
    assert "Always type hint" in registry.get_project_rules()
    actions = registry.get_all_actions()
    assert len(actions) == 1
    assert actions[0].name == "domain_deploy"
    
    critics = registry.get_all_critics()
    assert len(critics) == 1
    report = critics[0].validate("any_code")
    assert report.verdict.status == CriticStatus.PASS
    
    # Unload
    registry.unload_plugin("sample_domain_plugin")
    assert getattr(plugin, "activated", True) is False
    assert len(registry.get_all_actions()) == 0
    assert len(registry.get_all_critics()) == 0


def test_plugin_registry_security_whitelisting(mock_plugin_project, tmp_path):
    # Only allow a different directory
    restricted_dir = tmp_path / "restricted"
    restricted_dir.mkdir()
    registry = PluginRegistry(allowed_roots=[restricted_dir])
    
    # Attempting to load mock_plugin_project (outside allowed roots) must raise PermissionError
    with pytest.raises(PermissionError) as excinfo:
        registry.load_plugin(mock_plugin_project)
    assert "Security violation" in str(excinfo.value)


def test_plugin_registry_corrupted_manifest_graceful_fallback(tmp_path):
    bad_dir = tmp_path / "bad_project"
    bad_dir.mkdir()
    bad_manifest = bad_dir / "agent_plugin.json"
    bad_manifest.write_text("{ this is not valid json :", encoding="utf-8")
    
    registry = PluginRegistry(allowed_roots=[bad_dir])
    manifest = registry.discover_manifest(bad_dir)
    assert manifest is None  # Safe fallback without crashing
    
    plugin = registry.load_plugin(bad_dir)
    assert plugin is None  # Safe fallback to unextended core


def test_plugin_registry_instance_isolation(mock_plugin_project):
    reg1 = PluginRegistry(allowed_roots=[mock_plugin_project])
    reg2 = PluginRegistry(allowed_roots=[mock_plugin_project])
    
    reg1.load_plugin(mock_plugin_project)
    assert len(reg1.get_all_actions()) == 1
    # reg2 is independent and must not share mutable state
    assert len(reg2.get_all_actions()) == 0
