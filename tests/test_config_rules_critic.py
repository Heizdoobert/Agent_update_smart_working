"""Tests for MarkdownRulesCritic and PluginManifestCritic adapters."""

from __future__ import annotations

import json
import pytest

from agent_system.core.contracts import CriticStatus
from agent_system.reflection.adapters.config_rules import MarkdownRulesCritic, PluginManifestCritic


def test_markdown_rules_critic_valid():
    critic = MarkdownRulesCritic()
    valid_md = "# Project Rules\n\n## Guidelines\n- Clean architecture\n```python\nprint('safe')\n```\n"
    report = critic.validate(valid_md)
    assert report.verdict.status == CriticStatus.PASS
    assert report.verdict.score == 100.0
    assert len(report.diagnostics) == 0


def test_markdown_rules_critic_detects_unclosed_fences():
    critic = MarkdownRulesCritic()
    broken_md = "# Project Rules\n\n```python\ndef broken():\n    pass\n"
    report = critic.validate(broken_md)
    assert report.verdict.status == CriticStatus.REJECT
    assert any(d.code == "UNCLOSED_CODE_FENCE" for d in report.diagnostics)
    assert report.verdict.score < 80.0


def test_markdown_rules_critic_missing_top_heading():
    critic = MarkdownRulesCritic()
    no_h1_md = "Just plain text without any markdown heading."
    report = critic.validate(no_h1_md)
    assert report.verdict.status == CriticStatus.WARNING or report.verdict.status == CriticStatus.REJECT
    assert any(d.code == "MISSING_TOP_HEADING" for d in report.diagnostics)


def test_markdown_rules_critic_warns_on_oversize():
    critic = MarkdownRulesCritic(max_bytes=500)
    oversize_md = "# Rules\n" + ("Long rule description here.\n" * 100)
    report = critic.validate(oversize_md)
    assert any(d.code == "RULES_EXCEED_BUDGET" for d in report.diagnostics)


def test_plugin_manifest_critic_valid():
    critic = PluginManifestCritic()
    valid_manifest = {
        "name": "my_valid_plugin",
        "version": "1.0.0",
        "rules_path": ".agent/rules.md",
        "entrypoint": "plugin:MyPlugin",
    }
    report = critic.validate(valid_manifest)
    assert report.verdict.status == CriticStatus.PASS
    assert report.verdict.score == 100.0


def test_plugin_manifest_critic_invalid_name_and_missing_version():
    critic = PluginManifestCritic()
    bad_manifest = {
        "name": "123-bad-name!",
    }
    report = critic.validate(bad_manifest)
    assert report.verdict.status == CriticStatus.REJECT
    codes = [d.code for d in report.diagnostics]
    assert "INVALID_NAME_IDENTIFIER" in codes
    assert "MISSING_REQUIRED_FIELD" in codes
