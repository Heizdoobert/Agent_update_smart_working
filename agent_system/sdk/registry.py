"""Dynamic Plugin Registry with safe path whitelisting and module isolation."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from agent_system.core.contracts import CriticProtocol
from agent_system.core.truncator import StructuralTruncator
from agent_system.reasoning.transition import ActionDefinition
from agent_system.sdk.contracts import BasePlugin, PluginManifest, ProjectContext


class PluginRegistry:
    """Safe, instance-based registry managing dynamic project plugins.

    Enforces filesystem whitelisting, prevents arbitrary module shadowing,
    and maintains isolated instance lifecycles without mutating global state.
    """

    MANIFEST_FILENAMES = ["agent_plugin.json", ".agent/plugin.json"]

    def __init__(
        self,
        allowed_roots: Optional[List[Union[str, Path]]] = None,
    ) -> None:
        self.allowed_roots = [
            Path(r).resolve() for r in (allowed_roots or [Path.cwd()])
        ]
        self._active_plugins: Dict[str, BasePlugin] = {}

    def _is_path_whitelisted(self, path: Path) -> bool:
        """Verify that resolved path resides within one of the allowed roots."""
        resolved = path.resolve()
        for root in self.allowed_roots:
            try:
                resolved.relative_to(root)
                return True
            except ValueError:
                continue
        return False

    def discover_manifest(
        self, directory: Optional[Union[str, Path]] = None
    ) -> Optional[PluginManifest]:
        """Discover and parse plugin manifest in given directory."""
        dir_path = Path(directory or Path.cwd()).resolve()
        if not self._is_path_whitelisted(dir_path):
            raise PermissionError(
                f"Security violation: path '{dir_path}' is outside whitelisted directories: {self.allowed_roots}"
            )

        for fname in self.MANIFEST_FILENAMES:
            candidate = dir_path / fname
            if candidate.is_file():
                try:
                    content = candidate.read_text(encoding="utf-8")
                    data = json.loads(content)
                    return PluginManifest.from_dict(data)
                except Exception as e:
                    sys.stderr.write(
                        f"Warning: Failed to parse plugin manifest '{candidate}': {e}\n"
                    )
                    return None
        return None

    def load_plugin(
        self, path_or_dir: Optional[Union[str, Path]] = None
    ) -> Optional[BasePlugin]:
        """Load and instantiate a project plugin from directory or manifest file.

        Loads code safely using module specs without mutating sys.path.
        """
        target = Path(path_or_dir or Path.cwd()).resolve()
        if not self._is_path_whitelisted(target):
            raise PermissionError(
                f"Security violation: path '{target}' is outside whitelisted directories: {self.allowed_roots}"
            )

        if target.is_dir():
            manifest = self.discover_manifest(target)
            project_root = target
        elif target.is_file():
            try:
                data = json.loads(target.read_text(encoding="utf-8"))
                manifest = PluginManifest.from_dict(data)
                project_root = target.parent
            except Exception as e:
                sys.stderr.write(
                    f"Warning: Corrupted manifest file '{target}': {e}\n"
                )
                return None
        else:
            return None

        if manifest is None:
            return None

        # Read and truncate project rules if configured
        rules_content = ""
        if manifest.rules_path:
            rules_file = (project_root / manifest.rules_path).resolve()
            if self._is_path_whitelisted(rules_file) and rules_file.is_file():
                raw_rules = rules_file.read_text(encoding="utf-8")
                rules_content = StructuralTruncator.truncate_text(
                    raw_rules, max_bytes=3072
                )

        context = ProjectContext(
            project_root=project_root,
            rules_content=rules_content,
            metadata=dict(manifest.metadata),
        )

        # Dynamic import of entrypoint if present
        if manifest.entrypoint and ":" in manifest.entrypoint:
            mod_rel, class_name = manifest.entrypoint.split(":", 1)
            if mod_rel.endswith(".py"):
                py_file = (project_root / mod_rel).resolve()
            else:
                py_file = (
                    project_root / (mod_rel.replace(".", "/") + ".py")
                ).resolve()

            if not self._is_path_whitelisted(py_file) or not py_file.is_file():
                sys.stderr.write(
                    f"Warning: Plugin entrypoint file '{py_file}' not found or not whitelisted.\n"
                )
                return None

            try:
                mod_name = f"_agent_plugin_{manifest.name}"
                spec = importlib.util.spec_from_file_location(mod_name, py_file)
                if spec is None or spec.loader is None:
                    sys.stderr.write(
                        f"Warning: Cannot build import spec for '{py_file}'.\n"
                    )
                    return None

                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                plugin_cls = getattr(module, class_name, None)
                if plugin_cls is None or not issubclass(plugin_cls, BasePlugin):
                    sys.stderr.write(
                        f"Warning: Class '{class_name}' does not inherit from BasePlugin.\n"
                    )
                    return None

                plugin_instance = plugin_cls(manifest=manifest, context=context)
            except Exception as e:
                sys.stderr.write(
                    f"Warning: Failed to load plugin entrypoint '{manifest.entrypoint}': {e}\n"
                )
                return None
        else:
            # Default fallback plugin when no custom class entrypoint is specified
            plugin_instance = BasePlugin(manifest=manifest, context=context)

        plugin_instance.on_load()
        self._active_plugins[manifest.name] = plugin_instance
        return plugin_instance

    def unload_plugin(self, name: str) -> None:
        """Deactivate and unload a plugin by name."""
        plugin = self._active_plugins.pop(name, None)
        if plugin:
            try:
                plugin.on_unload()
            except Exception as e:
                sys.stderr.write(
                    f"Warning: Error during plugin '{name}' on_unload(): {e}\n"
                )

    def get_plugin(self, name: str) -> Optional[BasePlugin]:
        """Get loaded plugin instance by name."""
        return self._active_plugins.get(name)

    def get_all_actions(self) -> List[ActionDefinition]:
        """Aggregate and deduplicate domain actions across all active plugins.

        Plugins with higher manifest priority take precedence on name collisions.
        """
        sorted_plugins = sorted(
            self._active_plugins.values(),
            key=lambda p: p.manifest.priority,
            reverse=True,
        )
        action_map: Dict[str, ActionDefinition] = {}
        for plugin in sorted_plugins:
            for act in plugin.get_actions():
                if act.name not in action_map:
                    action_map[act.name] = act
        return list(action_map.values())

    def discover_and_load_all(
        self, directory: Optional[Union[str, Path]] = None
    ) -> List[BasePlugin]:
        """Discover and load all plugins in a root directory and its immediate subdirectories."""
        target = Path(directory or Path.cwd()).resolve()
        if not self._is_path_whitelisted(target):
            raise PermissionError(
                f"Security violation: path '{target}' is outside whitelisted directories: {self.allowed_roots}"
            )

        loaded: List[BasePlugin] = []

        # Check target directory itself
        self_manifest = self.discover_manifest(target)
        if self_manifest:
            p = self.load_plugin(target)
            if p:
                loaded.append(p)

        # Check immediate subdirectories
        if target.is_dir():
            for item in sorted(target.iterdir()):
                if item.is_dir() and not item.name.startswith("."):
                    sub_manifest = self.discover_manifest(item)
                    if sub_manifest:
                        p = self.load_plugin(item)
                        if p:
                            loaded.append(p)

        return loaded

    def get_all_critics(self) -> List[CriticProtocol]:
        """Aggregate domain critics across all active plugins."""
        critics: List[CriticProtocol] = []
        for plugin in self._active_plugins.values():
            critics.extend(plugin.get_critics())
        return critics

    def get_project_rules(self, max_bytes: int = 3072) -> str:
        """Combine project rules from all active plugins bounded by context budget."""
        rules = [p.get_rules() for p in self._active_plugins.values() if p.get_rules()]
        combined = "\n\n".join(rules)
        return StructuralTruncator.truncate_text(combined, max_bytes=max_bytes)

    def trigger_before_plan(self, initial_state: Any, goal: Any) -> None:
        """Notify all active plugins before planning begins."""
        for plugin in self._active_plugins.values():
            try:
                plugin.on_before_plan(initial_state, goal)
            except Exception as e:
                sys.stderr.write(
                    f"Warning: Exception in plugin '{plugin.manifest.name}' on_before_plan: {e}\n"
                )

    def trigger_after_plan(self, plan: Optional[Any]) -> Optional[Any]:
        """Pipe generated plan through active plugins for observation or decoration."""
        current_plan = plan
        for plugin in self._active_plugins.values():
            try:
                res = plugin.on_after_plan(current_plan)
                if res is not None:
                    current_plan = res
            except Exception as e:
                sys.stderr.write(
                    f"Warning: Exception in plugin '{plugin.manifest.name}' on_after_plan: {e}\n"
                )
        return current_plan

    def trigger_critic_report(self, report: CriticReport) -> CriticReport:
        """Pipe critic report through active plugins for inspection or augmentation."""
        current_report = report
        for plugin in self._active_plugins.values():
            try:
                res = plugin.on_critic_report(current_report)
                if res is not None:
                    current_report = res
            except Exception as e:
                sys.stderr.write(
                    f"Warning: Exception in plugin '{plugin.manifest.name}' on_critic_report: {e}\n"
                )
        return current_report
