"""`agent-system doctor`: one-screen health report. Every check is read-only and offline."""

from __future__ import annotations

import importlib.util
import json
import os
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict, List

from agent_system import __version__, flow
from agent_system.sdk import installer
from agent_system.storage.sqlite_store import SQLiteStore


def _registered(path: Path) -> bool:
    try:
        return "agent-system" in json.loads(path.read_text(encoding="utf-8")).get("mcpServers", {})
    except Exception:
        return False


def run() -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []

    def add(name: str, ok: bool, detail: str, required: bool = True) -> None:
        checks.append({"name": name, "ok": ok, "detail": detail, "required": required})

    add("python", sys.version_info >= (3, 9), sys.version.split()[0])
    add("version", True, __version__)
    try:
        store = SQLiteStore()
        with sqlite3.connect(store.db_path) as c:
            rows = c.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
        add("memory-db", True, f"{store.db_path} ({rows} rows)")
    except Exception as e:
        add("memory-db", False, str(e)[:200])
    has_embed = importlib.util.find_spec("fastembed") is not None and os.environ.get("AGENT_SYSTEM_NO_EMBED") != "1"
    add("embeddings", has_embed, "fastembed" if has_embed else "BM25 only (pip install 'agent-system[embed]')", required=False)

    clients = {
        "claude-desktop": installer.get_claude_desktop_config_path(),
        "cursor": installer.get_cursor_config_path(),
        "antigravity": installer.get_antigravity_config_path(),
        "windsurf": installer.get_windsurf_config_path(),
    }
    reg = [n for n, p in clients.items() if p and _registered(p)]
    add("mcp-clients", bool(reg), ", ".join(reg) or "none registered (agent-system install)", required=False)
    add("llm-patcher", True, "on" if os.environ.get("AGENT_SYSTEM_LLM_PATCH") == "1" else "off (AGENT_SYSTEM_LLM_PATCH=1 to enable)", required=False)
    exe = flow.find()
    add("flow-task", bool(exe), exe or "not found: agent -> task engine bridge disabled", required=False)

    return {"ok": all(c["ok"] for c in checks if c["required"]), "checks": checks}


def render(report: Dict[str, Any]) -> str:
    lines = [f"{'OK ' if c['ok'] else ('FAIL' if c['required'] else 'warn')}  {c['name']:<12} {c['detail']}" for c in report["checks"]]
    return "\n".join(lines) + "\n"
