"""Dual-tier knowledge ingestion engine for brownfield repositories.

Synthesizes Tier 1 Level 1 Rules (<3KB, strictly truncated and validated)
and indexes Tier 2 documentation into Semantic Memory (SQLite Store).
"""
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
from typing import List, Optional

from agent_system.core.truncator import StructuralTruncator
from agent_system.memory.semantic import SemanticMemory
from agent_system.sdk.scanner import ProjectManifest
from agent_system.storage.sqlite_store import SQLiteStore

DEFAULT_RULES_BUDGET = 3072


@dataclass
class IngestionResult:
    """Outcome of knowledge ingestion for a brownfield repository."""

    rules_path: Path
    plugin_path: Path
    rules_bytes: int
    chunks_indexed: int
    success: bool = True


class KnowledgeIngester:
    """Ingests scanned brownfield manifest into Tier 1 rules and Tier 2 memory."""

    def __init__(
        self,
        root_path: str | Path = ".",
        db_path: Optional[str | Path] = None,
        max_rules_bytes: int = DEFAULT_RULES_BUDGET,
    ) -> None:
        self.root_path = Path(root_path).resolve()
        self.db_path = Path(db_path).resolve() if db_path else self.root_path / ".agent" / "memory.db"
        self.max_rules_bytes = max_rules_bytes

    def ingest(self, manifest: ProjectManifest) -> IngestionResult:
        """Run 2-tier ingestion: generate Level 1 rules and index Tier 2 docs."""
        # Ensure .agent directory exists
        agent_dir = self.root_path / ".agent"
        agent_dir.mkdir(parents=True, exist_ok=True)

        # 1. Synthesize Tier 1 Rules
        rules_path = agent_dir / "rules.md"
        rules_content = self._synthesize_rules(manifest)
        truncated_rules = StructuralTruncator.truncate_text(rules_content, max_bytes=self.max_rules_bytes)

        # Double check byte limit
        rules_bytes = truncated_rules.encode("utf-8")
        if len(rules_bytes) > self.max_rules_bytes:
            truncated_rules = StructuralTruncator.truncate_text(
                truncated_rules[: self.max_rules_bytes - 100],
                max_bytes=self.max_rules_bytes,
            )
            rules_bytes = truncated_rules.encode("utf-8")

        rules_path.write_text(truncated_rules, encoding="utf-8")

        # Create symlink or companion AGENTS.md in repo root
        agents_link = self.root_path / "AGENTS.md"
        if not agents_link.exists():
            try:
                # Attempt relative symlink: AGENTS.md -> .agent/rules.md
                rel_target = Path(".agent") / "rules.md"
                agents_link.symlink_to(rel_target)
            except (OSError, NotImplementedError):
                # Fallback on filesystems that disallow symlinks
                agents_link.write_text(truncated_rules, encoding="utf-8")

        # Create agent_plugin.json if absent
        plugin_path = self.root_path / "agent_plugin.json"
        if not plugin_path.exists():
            raw_name = manifest.extra_metadata.get("project_name") or Path(manifest.root_path).name
            pkg_name = str(raw_name).lower().replace("-", "_").replace(" ", "_")
            if not pkg_name or not pkg_name.isidentifier():
                pkg_name = "project_plugin"
            manifest_data = {
                "name": pkg_name,
                "version": "0.1.0",
                "description": f"Domain rules and actions for {manifest.primary_language} project.",
                "rules_path": ".agent/rules.md",
                "entrypoint": "plugin.py",
                "actions": [],
                "critics": [],
            }
            plugin_path.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")

        # 2. Ingest Tier 2 Documentation into Semantic Memory
        chunks_indexed = self._ingest_documentation_to_memory(manifest)

        return IngestionResult(
            rules_path=rules_path,
            plugin_path=plugin_path,
            rules_bytes=len(rules_bytes),
            chunks_indexed=chunks_indexed,
            success=True,
        )

    def _synthesize_rules(self, manifest: ProjectManifest) -> str:
        """Compose structured Level 1 rules markdown from project manifest."""
        lang = manifest.primary_language if manifest.primary_language != "Unknown" else "Repository"
        stack_str = ", ".join(manifest.tech_stack[:10]) if manifest.tech_stack else "Standard"

        lines: List[str] = [
            f"# Project Rules: {lang}",
            "",
            "## 1. Environment & Tech Stack",
            f"- **Primary Language:** {lang}",
            f"- **Core Stack:** {stack_str}",
        ]

        if manifest.test_framework:
            lines.append(f"- **Test Framework:** {manifest.test_framework}")

        lines.extend([
            "",
            "## 2. Standard Commands",
            "```bash",
        ])

        if manifest.build_commands:
            for name, cmd in manifest.build_commands.items():
                lines.append(f"# {name}")
                lines.append(cmd)
        else:
            lines.append("# No custom build/test commands detected")

        lines.extend([
            "```",
            "",
            "## 3. Core Coding Conventions",
        ])

        if manifest.detected_rules:
            # Dedup and pick top 8 rules
            dedup_rules = list(dict.fromkeys(manifest.detected_rules))[:8]
            for rule in dedup_rules:
                # Clean prefix
                clean = re.sub(r"^[-*]\s*", "", rule).strip()
                lines.append(f"- {clean}")
        else:
            lines.extend([
                "- Maintain clean architecture and modular separation.",
                "- Ensure all unit and integration tests pass before handoff.",
                "- Adhere to official language conventions and safe error handling.",
            ])

        lines.append("")
        return "\n".join(lines)

    def _ingest_documentation_to_memory(self, manifest: ProjectManifest) -> int:
        """Split documentation files by H2 headings and index into SemanticMemory."""
        if not manifest.documentation_files:
            return 0

        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        store = SQLiteStore(db_path=self.db_path)
        memory = SemanticMemory(store=store)

        chunks_count = 0
        for rel_doc in manifest.documentation_files:
            doc_file = self.root_path / rel_doc
            if not doc_file.is_file():
                continue

            try:
                with open(doc_file, "rb") as f:
                    content = f.read(50_000).decode("utf-8", errors="ignore")
            except (IOError, OSError):
                continue

            # Split by markdown headings: ## or #
            sections = self._chunk_markdown(content, rel_doc)
            for idx, (heading, chunk_body) in enumerate(sections):
                item_id = f"doc:{rel_doc}:{idx}"
                full_text = f"[{rel_doc} > {heading}]\n{chunk_body}"
                memory.index_document(
                    item_id=item_id,
                    content=full_text,
                    category="brownfield_doc",
                    score=1.0,
                    metadata={"source": rel_doc, "heading": heading},
                )
                chunks_count += 1

        return chunks_count

    def _chunk_markdown(self, content: str, filename: str) -> List[tuple[str, str]]:
        """Split markdown text by H2 (##) or H1 (#) headings."""
        lines = content.splitlines()
        chunks: List[tuple[str, str]] = []
        current_heading = "Overview"
        current_lines: List[str] = []

        for line in lines:
            if re.match(r"^#{1,2}\s+", line):
                if current_lines:
                    chunk_text = "\n".join(current_lines).strip()
                    if chunk_text:
                        chunks.append((current_heading, chunk_text))
                    current_lines = []
                current_heading = re.sub(r"^#{1,2}\s+", "", line).strip()
            else:
                current_lines.append(line)

        if current_lines:
            chunk_text = "\n".join(current_lines).strip()
            if chunk_text:
                chunks.append((current_heading, chunk_text))

        return chunks
