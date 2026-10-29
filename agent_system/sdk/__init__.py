"""Agent System SDK: Modular Plugin & Extensibility Kit."""

from __future__ import annotations

from agent_system.sdk.contracts import (
    BasePlugin,
    PluginManifest,
    ProjectContext,
)
from agent_system.sdk.registry import PluginRegistry
from agent_system.sdk.wizard import OnboardingWizard

__all__ = [
    "BasePlugin",
    "PluginManifest",
    "ProjectContext",
    "PluginRegistry",
    "OnboardingWizard",
]
