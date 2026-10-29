"""Tests for Interactive Onboarding Wizard: safe I/O, identifier validation, and rollback."""

from __future__ import annotations

import io
import json
from pathlib import Path
import pytest

from agent_system.sdk.wizard import OnboardingWizard


def test_wizard_successful_scaffolding(tmp_path):
    # Simulate user answers for the 4 questions:
    # Q1: project name
    # Q2: project rules
    # Q3: custom actions
    # Q4: critic requirements
    user_inputs = io.StringIO("my_game_project\nMust follow strict MVVM architecture\ntap_play, collect_gold\nstrict_types\n")
    output = io.StringIO()
    
    wizard = OnboardingWizard(target_dir=tmp_path, stdin=user_inputs, stdout=output)
    
    assert wizard.is_needed() is True
    success = wizard.run()
    assert success is True
    
    # Verify files created
    rules_file = tmp_path / ".agent" / "rules.md"
    assert rules_file.is_file()
    assert "strict MVVM architecture" in rules_file.read_text(encoding="utf-8")
    
    manifest_file = tmp_path / "agent_plugin.json"
    assert manifest_file.is_file()
    data = json.loads(manifest_file.read_text(encoding="utf-8"))
    assert data["name"] == "my_game_project"
    assert data["actions"] == ["tap_play", "collect_gold"]
    assert data["entrypoint"] == "plugin:MyGameProjectPlugin"
    
    plugin_py = tmp_path / "plugin.py"
    assert plugin_py.is_file()
    plugin_content = plugin_py.read_text(encoding="utf-8")
    assert "class MyGameProjectPlugin(BasePlugin):" in plugin_content
    assert "tap_play" in plugin_content
    assert "collect_gold" in plugin_content


def test_wizard_rejects_invalid_identifiers(tmp_path):
    # First tries invalid name "123 bad-name!", then valid name "valid_proj"
    user_inputs = io.StringIO("123 bad-name!\nvalid_proj\nStandard rules\naction_one\n\n")
    output = io.StringIO()
    
    wizard = OnboardingWizard(target_dir=tmp_path, stdin=user_inputs, stdout=output)
    success = wizard.run()
    assert success is True
    
    manifest = json.loads((tmp_path / "agent_plugin.json").read_text(encoding="utf-8"))
    assert manifest["name"] == "valid_proj"


def test_wizard_rollback_on_interrupt(tmp_path):
    class InterruptingIO:
        def __init__(self):
            self.calls = 0

        def readline(self):
            self.calls += 1
            if self.calls == 1:
                return "test_interrupt_proj\n"
            # Simulate Ctrl+C on question 2
            raise KeyboardInterrupt()

    output = io.StringIO()
    wizard = OnboardingWizard(target_dir=tmp_path, stdin=InterruptingIO(), stdout=output)
    
    success = wizard.run()
    assert success is False
    
    # Must clean up completely; no partially written files left
    assert not (tmp_path / "agent_plugin.json").exists()
    assert not (tmp_path / ".agent").exists()
    assert not (tmp_path / "plugin.py").exists()


def test_wizard_not_needed_if_already_configured(tmp_path):
    (tmp_path / "agent_plugin.json").write_text("{}", encoding="utf-8")
    wizard = OnboardingWizard(target_dir=tmp_path)
    assert wizard.is_needed() is False
