"""Automated installer and configuration generator for AI Agent environments.

Installs Universal System Instructions and MCP Server configurations into
Claude Desktop, Cursor, Windsurf, Claude Code, and global agent rules.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional

UNIVERSAL_SYSTEM_INSTRUCTION = """# Universal Agent Cognitive Operating Protocol

All AI Agents working in this environment MUST strictly follow this Operating Protocol:

---

## 0. First-Time Workspace Bootstrap
- Check if the current workspace contains `.agent/rules.md` or `agent_plugin.json`.
- If missing, run `agent-system init --auto --root .` (or invoke MCP tool `agent_init_auto`) to scaffold Level 1 rules and semantic memory before performing any other task.

## 1. Before Starting Any Work (Tra cứu trước khi làm)
- Retrieve domain knowledge: Run `agent-system memory search --query "<keywords>" --top-k 3` (or invoke MCP `agent_memory_search`).
- Lookup bug recovery recipes: Run `agent-system memory recipe-get --key "<error_key>"` (or invoke MCP `agent_memory_recipe_get`).
- Never guess APIs, dependencies, or conventions when context is already indexed.

## 2. Reasoning & Planning (Lập kế hoạch phi tuyến tính)
- For non-trivial or multi-step tasks, synthesize optimal paths via A* or MCTS: Run `agent-system plan --initial state.json --goal-key <key>` (or invoke MCP `agent_plan`).
- Maintain Directed Acyclic Graph (DAG) invariants; avoid rigid linear guesswork.

## 3. In-Memory Self-Reflection & Static Audit (Thẩm định trước khi commit)
- Before writing critical files or committing changes, audit artifacts through `agent-system critic --file <path>` (or invoke MCP `agent_critic`).
- Auto-repair violations in RAM with `agent-system reflect` (or MCP `agent_reflect`) until achieving 100/100 score before writing to disk.

## 4. Strict Context Budget (<3KB) & Episodic Memory
- Bound all active prompt context under 3072 bytes (<3KB) via Structural Truncation.
- After resolving an issue, record the solution into Episodic Memory: Run `agent-system memory recipe-record --key "<key>" --recipe "<solution>"` (or invoke MCP `agent_memory_recipe_record`).
- Communicate with concise, professional technical Vietnamese, and include clickable links (`file:///...`).
"""


def get_claude_desktop_config_path() -> Optional[Path]:
    """Resolve OS-specific path for Claude Desktop configuration file."""
    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA")
        return Path(appdata) / "Claude" / "claude_desktop_config.json" if appdata else None
    elif sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    else:
        return Path.home() / ".config" / "Claude" / "claude_desktop_config.json"


def get_cursor_config_path() -> Path:
    """Resolve default path for Cursor MCP configuration file."""
    return Path.home() / ".cursor" / "mcp.json"


def get_antigravity_config_path() -> Path:
    """Resolve default path for Antigravity (AGY CLI / Gemini) MCP configuration file."""
    return Path.home() / ".gemini" / "config" / "mcp_config.json"


def get_windsurf_config_path() -> Path:
    """Resolve default path for Windsurf MCP configuration file."""
    return Path.home() / ".codeium" / "windsurf" / "mcp_config.json"


def get_mcp_server_entry(command: str = "agent-system") -> Dict[str, Any]:
    """Return standard MCP server configuration dictionary."""
    return {
        "command": command,
        "args": ["mcp"],
    }


def inject_mcp_config(config_path: Path, server_name: str = "agent-system") -> bool:
    """Safely inject or update MCP server entry in a client JSON config file."""
    config_path.parent.mkdir(parents=True, exist_ok=True)
    data: Dict[str, Any] = {}

    if config_path.is_file():
        try:
            content = config_path.read_text(encoding="utf-8").strip()
            if content:
                data = json.loads(content)
        except Exception:
            data = {}

    if "mcpServers" not in data or not isinstance(data["mcpServers"], dict):
        data["mcpServers"] = {}

    data["mcpServers"][server_name] = get_mcp_server_entry()
    config_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return True


def install_agent_environment(
    target: str = "all",
    dry_run: bool = False,
    override_instruction: Optional[str] = None,
) -> Dict[str, Any]:
    """Install System Instructions and MCP configurations for agent clients."""
    instruction = (override_instruction or UNIVERSAL_SYSTEM_INSTRUCTION).strip() + "\n"
    results: Dict[str, Any] = {
        "mcp_installed": [],
        "rules_installed": [],
        "dry_run": dry_run,
    }

    # 0. MCP Configuration for Antigravity (AGY CLI)
    if target in ("all", "agy", "antigravity", "mcp"):
        agy_path = get_antigravity_config_path()
        results["mcp_installed"].append(
            {"client": "Antigravity (AGY CLI)", "path": str(agy_path), "status": "PENDING" if dry_run else "SUCCESS"}
        )
        if not dry_run:
            inject_mcp_config(agy_path)

    # 1. MCP Configuration for Claude Desktop
    if target in ("all", "claude", "mcp"):
        claude_path = get_claude_desktop_config_path()
        if claude_path:
            results["mcp_installed"].append(
                {"client": "Claude Desktop", "path": str(claude_path), "status": "PENDING" if dry_run else "SUCCESS"}
            )
            if not dry_run:
                inject_mcp_config(claude_path)

    # 2. MCP Configuration for Cursor
    if target in ("all", "cursor", "mcp"):
        cursor_path = get_cursor_config_path()
        results["mcp_installed"].append(
            {"client": "Cursor", "path": str(cursor_path), "status": "PENDING" if dry_run else "SUCCESS"}
        )
        if not dry_run:
            inject_mcp_config(cursor_path)

    # 3. MCP Configuration for Windsurf
    if target in ("all", "windsurf", "mcp"):
        windsurf_path = get_windsurf_config_path()
        results["mcp_installed"].append(
            {"client": "Windsurf", "path": str(windsurf_path), "status": "PENDING" if dry_run else "SUCCESS"}
        )
        if not dry_run:
            inject_mcp_config(windsurf_path)

    # 4. Global System Instructions / Rules
    if target in ("all", "rules", "agy", "antigravity"):
        rules_targets = [
            Path.home() / ".gemini" / "config" / "rules" / "AGENTS.md",
            Path.home() / ".claude" / "CLAUDE.md",
            Path.home() / ".cursorrules",
            Path.home() / ".agent" / "rules.md",
        ]
        for rp in rules_targets:
            results["rules_installed"].append(
                {"path": str(rp), "bytes": len(instruction.encode("utf-8")), "status": "PENDING" if dry_run else "SUCCESS"}
            )
            if not dry_run:
                rp.parent.mkdir(parents=True, exist_ok=True)
                rp.write_text(instruction, encoding="utf-8")

    return results
