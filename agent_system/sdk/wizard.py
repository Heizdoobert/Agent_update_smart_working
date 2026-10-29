"""Interactive Project Onboarding Wizard for Agent System SDK."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Callable, List, Optional, Union


def _pascal_case(name: str) -> str:
    """Convert snake_case or identifier to PascalCase."""
    parts = name.replace("-", "_").split("_")
    return "".join(p.capitalize() for p in parts if p)


class OnboardingWizard:
    """Guided terminal onboarding wizard for bootstrapping project SDK plugins."""

    def __init__(
        self,
        target_dir: Optional[Union[str, Path]] = None,
        stdin: Any = None,
        stdout: Any = None,
    ) -> None:
        self.target_dir = Path(target_dir or Path.cwd()).resolve()
        self.stdin = stdin if stdin is not None else sys.stdin
        self.stdout = stdout if stdout is not None else sys.stdout
        self._created_paths: List[Path] = []

    def is_needed(self) -> bool:
        """Check if project currently lacks SDK plugin configuration."""
        manifest = self.target_dir / "agent_plugin.json"
        agent_dir = self.target_dir / ".agent"
        return not (manifest.is_file() or agent_dir.is_dir())

    def is_interactive(self) -> bool:
        """Check if environment supports interactive TTY prompting."""
        if os.environ.get("AGENT_SYSTEM_NO_WIZARD", "").lower() in (
            "1",
            "true",
            "yes",
        ):
            return False

        stdin_isatty = getattr(self.stdin, "isatty", lambda: False)()
        stdout_isatty = getattr(self.stdout, "isatty", lambda: False)()
        return bool(stdin_isatty and stdout_isatty)

    def _print(self, text: str = "") -> None:
        self.stdout.write(text + "\n")
        self.stdout.flush()

    def _ask(
        self,
        question: str,
        default: str = "",
        validator: Optional[Callable[[str], bool]] = None,
        error_msg: str = "Invalid input. Please try again.",
    ) -> str:
        prompt = f"{question} [{default}]: " if default else f"{question}: "
        while True:
            self.stdout.write(prompt)
            self.stdout.flush()
            line = self.stdin.readline()
            if not line:
                raise EOFError("Input stream closed prematurely.")
            val = line.strip()
            if not val and default:
                return default
            if validator:
                if validator(val):
                    return val
                self._print(f"Error: {error_msg}")
            else:
                return val

    def _rollback(self) -> None:
        """Clean up any files or directories created during this session."""
        for path in reversed(self._created_paths):
            try:
                if path.is_file():
                    path.unlink(missing_ok=True)
                elif path.is_dir() and not any(path.iterdir()):
                    path.rmdir()
            except Exception:
                pass
        self._created_paths.clear()

    def run(self) -> bool:
        """Execute interactive 4-question onboarding and scaffold project files."""
        self._print("=" * 60)
        self._print("🚀 Agent System Project Setup Wizard")
        self._print("=" * 60)

        try:
            # 1. Project Name & Domain
            def _validate_identifier(s: str) -> bool:
                return bool(s and s.isidentifier())

            default_name = self.target_dir.name.replace("-", "_").lower()
            if not default_name.isidentifier():
                default_name = "my_project"

            project_name = self._ask(
                "1. Project Name (valid Python identifier)",
                default=default_name,
                validator=_validate_identifier,
                error_msg="Name must be a valid Python identifier (letters, digits, underscores, no leading digit).",
            )

            # 2. Operating Prompt Rules
            rules_summary = self._ask(
                "2. Operating Prompt Rules summary (guidelines for the AI Agent)",
                default="Follow clean architecture, enforce type annotations, and maintain test coverage.",
            )

            # 3. Custom Actions
            actions_raw = self._ask(
                "3. Custom domain action names (comma-separated, optional)",
                default="init_step, execute_step",
            )
            raw_action_tokens = [
                a.strip() for a in actions_raw.split(",") if a.strip()
            ]
            action_names = [a for a in raw_action_tokens if a.isidentifier()]

            # 4. Domain Critic Requirements
            critic_req = self._ask(
                "4. Domain critic criteria (e.g. strict_types, clean_code)",
                default="strict_types",
            )

            self._print("\n📦 Scaffolding project SDK files...")

            # Directory: .agent/
            agent_dir = self.target_dir / ".agent"
            if not agent_dir.exists():
                agent_dir.mkdir(parents=True, exist_ok=True)
                self._created_paths.append(agent_dir)

            # File 1: .agent/rules.md
            rules_file = agent_dir / "rules.md"
            rules_md = (
                f"# Project Operating Rules: {project_name}\n\n"
                f"## Core Guidelines\n"
                f"- {rules_summary}\n\n"
                f"## Critic Expectations\n"
                f"- Enforce compliance with `{critic_req}` criteria before handoff.\n"
            )
            rules_file.write_text(rules_md, encoding="utf-8")
            self._created_paths.append(rules_file)

            # File 2: agent_plugin.json
            class_name = f"{_pascal_case(project_name)}Plugin"
            manifest = {
                "name": project_name,
                "version": "0.1.0",
                "description": f"Domain SDK plugin for {project_name}",
                "entrypoint": f"plugin:{class_name}",
                "rules_path": ".agent/rules.md",
                "actions": action_names,
                "critics": [critic_req] if critic_req else [],
                "metadata": {"scaffolded_by": "agent-system-wizard"},
            }
            manifest_file = self.target_dir / "agent_plugin.json"
            manifest_file.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
            self._created_paths.append(manifest_file)

            # File 3: plugin.py
            actions_code = ""
            for a in action_names:
                actions_code += (
                    f"            ActionDefinition(\n"
                    f'                name="{a}",\n'
                    f"                cost=1.0,\n"
                    f'                preconditions={{"ready": True}},\n'
                    f'                effects={{"{a}_done": True}},\n'
                    f"            ),\n"
                )

            plugin_code = (
                f'"""Project Plugin for {project_name}."""\n\n'
                f"from __future__ import annotations\n\n"
                f"from typing import List\n"
                f"from agent_system.core.contracts import CriticProtocol\n"
                f"from agent_system.reasoning.transition import ActionDefinition\n"
                f"from agent_system.sdk.contracts import BasePlugin\n\n\n"
                f"class {class_name}(BasePlugin):\n"
                f"    def on_load(self) -> None:\n"
                f'        """Hook called when plugin loads."""\n'
                f"        pass\n\n"
                f"    def on_unload(self) -> None:\n"
                f'        """Hook called when plugin unloads."""\n'
                f"        pass\n\n"
                f"    def get_actions(self) -> List[ActionDefinition]:\n"
                f"        return [\n"
                f"{actions_code}"
                f"        ]\n\n"
                f"    def get_critics(self) -> List[CriticProtocol]:\n"
                f"        return []\n"
            )
            plugin_file = self.target_dir / "plugin.py"
            plugin_file.write_text(plugin_code, encoding="utf-8")
            self._created_paths.append(plugin_file)

            self._print("✅ Successfully configured project SDK!")
            self._print(f"   Created: {rules_file.relative_to(self.target_dir)}")
            self._print(f"   Created: {manifest_file.relative_to(self.target_dir)}")
            self._print(f"   Created: {plugin_file.relative_to(self.target_dir)}\n")
            return True

        except (KeyboardInterrupt, EOFError):
            self._print("\n⚠️  Setup aborted by user. Cleaning up...")
            self._rollback()
            return False
        except Exception as e:
            self._print(f"\n❌ Error during setup: {e}. Cleaning up...")
            self._rollback()
            return False
