"""Dynamic Skill Registry with filesystem whitelisting and safe frontmatter parsing."""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from agent_system.core.truncator import StructuralTruncator


@dataclass
class SkillDefinition:
    name: str
    description: str
    instructions: str
    path: str
    sha256: str
    tags: List[str] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


def parse_markdown_frontmatter(content: str) -> Tuple[Dict[str, Any], str]:
    """Parse YAML-like frontmatter delimited by --- lines at start of file."""
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, content

    frontmatter_lines = []
    body_start_idx = -1
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            body_start_idx = i + 1
            break
        frontmatter_lines.append(lines[i])

    if body_start_idx == -1:
        return {}, content

    metadata: Dict[str, Any] = {}
    current_key: Optional[str] = None

    for line in frontmatter_lines:
        raw = line.strip()
        if not raw or raw.startswith("#"):
            continue

        if ":" in raw:
            key, val = raw.split(":", 1)
            key = key.strip()
            val = val.strip()
            current_key = key
            if not val:
                metadata[key] = []
            elif val.startswith("[") and val.endswith("]"):
                # Simple list parse
                items = [x.strip().strip("'\"") for x in val[1:-1].split(",") if x.strip()]
                metadata[key] = items
            else:
                metadata[key] = val.strip("'\"")
        elif raw.startswith("- ") and current_key and isinstance(metadata.get(current_key), list):
            metadata[current_key].append(raw[2:].strip().strip("'\""))

    body = "\n".join(lines[body_start_idx:]).strip()
    return metadata, body


class SkillRegistry:
    """Safe dynamic skill repository preventing unauthorized file access and injection."""

    def __init__(self, allowed_roots: Optional[List[Union[str, Path]]] = None):
        self.allowed_roots = [
            Path(r).resolve() for r in (allowed_roots or [Path.cwd()])
        ]
        self._skills: Dict[str, SkillDefinition] = {}

    def _is_path_whitelisted(self, path: Path) -> bool:
        resolved = path.resolve()
        for root in self.allowed_roots:
            try:
                resolved.relative_to(root)
                return True
            except ValueError:
                continue
        return False

    def register_skill_file(self, skill_path: Union[str, Path]) -> SkillDefinition:
        p = Path(skill_path).resolve()
        if not self._is_path_whitelisted(p):
            raise PermissionError(
                f"Security violation: skill path '{p}' is outside whitelisted directories: {self.allowed_roots}"
            )

        if not p.is_file():
            raise FileNotFoundError(f"Skill file not found: {p}")

        content = p.read_text(encoding="utf-8")
        sha256 = hashlib.sha256(content.encode("utf-8")).hexdigest()

        meta, body = parse_markdown_frontmatter(content)
        name = meta.get("name") or p.parent.name
        description = meta.get("description") or ""

        if not name:
            raise ValueError(f"Skill file '{p}' must define a 'name' in frontmatter or directory.")

        skill = SkillDefinition(
            name=name,
            description=description,
            instructions=body,
            path=str(p),
            sha256=sha256,
            tags=meta.get("tags") if isinstance(meta.get("tags"), list) else [],
            parameters=meta.get("parameters", {}),
            metadata=meta,
        )

        self._skills[name] = skill
        return skill

    def scan_directory(self, dir_path: Union[str, Path]) -> int:
        p = Path(dir_path).resolve()
        if not self._is_path_whitelisted(p):
            raise PermissionError(f"Directory '{p}' is not within whitelisted roots.")

        count = 0
        for skill_file in p.rglob("SKILL.md"):
            self.register_skill_file(skill_file)
            count += 1
        return count

    def get_skill(self, name: str) -> Optional[SkillDefinition]:
        return self._skills.get(name)

    def list_skills(self) -> List[str]:
        return sorted(self._skills.keys())

    def build_skill_context(
        self, skill_names: List[str], max_bytes: int = StructuralTruncator.DEFAULT_MAX_BYTES
    ) -> str:
        """Construct a compact markdown context block for prompt injection, strictly bounded <3KB."""
        sections: List[str] = []
        for name in skill_names:
            skill = self.get_skill(name)
            if not skill:
                continue
            section = f"### Skill: {skill.name}\n**Description:** {skill.description}\n\n{skill.instructions}"
            sections.append(section)

        combined = "\n\n---\n\n".join(sections)
        if not combined:
            return ""

        header = "## Injected Dynamic Skills\n\n"
        payload = header + combined
        return StructuralTruncator.truncate_text(payload, max_bytes=max_bytes)
