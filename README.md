# agent-system

Domain-agnostic agent engine: semantic + episodic memory (SQLite, optional fastembed vectors), critic and self-reflection loop, A*/MCTS planning, and a zero-dependency MCP server. Pairs with [FLOW_SKILL](../FLOW_SKILL), a Redis task engine with a cheap `claude -p` worker.

## Install (Linux, macOS, Windows)
Easiest: install both together from FLOW_SKILL (`./install.sh` / `.\install.ps1`, see its INSTALL.md): one venv, MCP registered, task engine wired.

Standalone:
```bash
pip install -e ".[embed]"        # drop [embed] for BM25-only memory (no model download)
agent-system install --target mcp   # register the MCP server in Claude Desktop, Cursor, Windsurf, Antigravity
agent-system doctor              # DB, embeddings, registered clients, flow-task bridge
```
`agent-system install` (default `--target all`) also writes the Universal Operating Protocol into `~/.claude/CLAUDE.md`, `~/.gemini/.../AGENTS.md`, `~/.cursorrules`, `~/.agent/rules.md` as a marked block (`<!-- agent-system:begin -->`) and never touches the rest of those files. Claude Code CLI: `claude mcp add agent-system -- agent-system mcp`.

Memory lives in `~/.agent_system/agent_system.db` (`AGENT_SYSTEM_DB_DIR` moves it; `AGENT_SYSTEM_NO_EMBED=1` forces BM25). `AGENT_SYSTEM_LLM_PATCH=1` lets `reflect` call a cheap Claude model for violations the rule patcher cannot fix.

## Wiring with FLOW_SKILL
- MCP tools `flow_task_submit` / `flow_task_status` queue work on the task engine (`flow-task` found next to this interpreter, on PATH, or via `FLOW_TASK_BIN`; absent = a clear error, nothing breaks).
- FLOW calls back into `agent-system memory search | index | recipe-record` around every task.

---

# Deterministic Token Engine (`token_engine/`)
### Installation
```bash
# Clone the repository (if not already)
cd /mnt/second_drive/Agent_system

# Set up a virtual environment and install the package in editable mode
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip setuptools
pip install -e .
```

## 🚀 Usage
```bash
# Run the CLI with a prompt (replace <your prompt> with your text)
source .venv/bin/activate
python -m token_engine.cli "<your prompt>"

# Allow the engine to exceed the token budget (override) when needed:
python -m token_engine.cli "<your prompt>" --allow-override
```

## 🛠️ How it works
- **Engine** (`engine.py`): Estimates token usage, enforces a configurable budget, and optionally overrides the limit.
- **Predictor** (`predictor.py`): Simple word‑count heuristic (replaceable with a ML model).
- **Rules** (`rules.py`): Defines the budget thresholds.
- **Audit** (`audit.py`): Logs each request as JSON‑lines and performs basic log rotation.
- **CLI** (`cli.py`): Provides a thin wrapper around the engine with an interactive confirmation step.

The component lives under `token_engine/` and can be imported as a Python SDK via `from token_engine import TokenEngine` for integration into larger agents.
