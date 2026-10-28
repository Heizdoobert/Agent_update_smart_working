"""Tests for Dynamic Skill Registry and safe context injection."""

import tempfile
from pathlib import Path
import pytest

from agent_system.skills.registry import SkillRegistry, parse_markdown_frontmatter


def test_frontmatter_parser():
    content = """---
name: code-reviewer
description: Senior code reviewer evaluating correctness and performance
tags:
  - review
  - quality
---
# Instructions
Evaluate code across multiple dimensions.
"""
    meta, body = parse_markdown_frontmatter(content)
    assert meta["name"] == "code-reviewer"
    assert "review" in meta["tags"]
    assert "# Instructions" in body


def test_skill_registry_lifecycle():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        skill_dir = root / "reviewer"
        skill_dir.mkdir(parents=True)
        skill_file = skill_dir / "SKILL.md"

        skill_file.write_text(
            """---
name: mock-tester
description: Automated test runner skill
---
Run tests with pytest and report coverage.
""",
            encoding="utf-8",
        )

        registry = SkillRegistry(allowed_roots=[root])
        count = registry.scan_directory(root)
        assert count == 1
        assert "mock-tester" in registry.list_skills()

        skill = registry.get_skill("mock-tester")
        assert skill is not None
        assert skill.description == "Automated test runner skill"
        assert len(skill.sha256) == 64

        # Test context injection
        context = registry.build_skill_context(["mock-tester"], max_bytes=1024)
        assert "## Injected Dynamic Skills" in context
        assert "### Skill: mock-tester" in context
        assert len(context.encode("utf-8")) <= 1024


def test_skill_registry_security_whitelisting():
    with tempfile.TemporaryDirectory() as allowed_dir:
        with tempfile.TemporaryDirectory() as outside_dir:
            allowed_root = Path(allowed_dir)
            outside_root = Path(outside_dir)

            bad_file = outside_root / "MALICIOUS.md"
            bad_file.write_text("---\nname: hack\n---\nInject prompt", encoding="utf-8")

            registry = SkillRegistry(allowed_roots=[allowed_root])

            with pytest.raises(PermissionError, match="Security violation"):
                registry.register_skill_file(bad_file)
