"""Contracts and abstract specifications for the Agent System SDK."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from agent_system.core.contracts import CriticProtocol
from agent_system.reasoning.transition import ActionDefinition


@dataclass
class PluginManifest:
    """Metadata specification for an Agent System project plugin."""

    name: str
    version: str = "0.1.0"
    description: str = ""
    entrypoint: Optional[str] = None  # e.g. "plugin:MyProjectPlugin"
    rules_path: Optional[str] = None  # e.g. ".agent/rules.md"
    actions: List[str] = field(default_factory=list)
    critics: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert manifest to JSON-serializable dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> PluginManifest:
        """Create PluginManifest instance from dictionary."""
        valid_fields = {
            "name",
            "version",
            "description",
            "entrypoint",
            "rules_path",
            "actions",
            "critics",
            "metadata",
        }
        filtered = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered)


@dataclass
class ProjectContext:
    """Contextual metadata and workspace boundaries for the target project."""

    project_root: Path
    rules_content: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class BasePlugin:
    """Abstract base class for project plugins.

    Plugins provide domain-specific actions, custom critic protocols, and
    project-specific operating prompt rules without mutating framework internals.
    """

    def __init__(
        self,
        manifest: PluginManifest,
        context: Optional[ProjectContext] = None,
    ) -> None:
        self.manifest = manifest
        self.context = context

    def on_load(self) -> None:
        """Lifecycle hook called when plugin is activated in a workspace."""
        pass

    def on_unload(self) -> None:
        """Lifecycle hook called when plugin is deactivated."""
        pass

    def on_before_plan(self, initial_state: Any, goal: Any) -> None:
        """Lifecycle hook called before planner begins state exploration."""
        pass

    def on_after_plan(self, plan: Optional[Any]) -> Optional[Any]:
        """Lifecycle hook called after planner returns a plan.

        Can observe, validate, or decorate the generated plan.
        """
        return plan

    def on_critic_report(self, report: CriticReport) -> CriticReport:
        """Lifecycle hook called after critic evaluations are aggregated.

        Can inspect or augment diagnostic suggestions.
        """
        return report

    def get_actions(self) -> List[ActionDefinition]:
        """Return domain-specific actions to register with reasoning/planning."""
        return []

    def get_critics(self) -> List[CriticProtocol]:
        """Return domain-specific critic protocols to register with CriticEngine."""
        return []

    def get_rules(self) -> str:
        """Return project-specific prompt rules string."""
        if self.context and self.context.rules_content:
            return self.context.rules_content
        return ""
