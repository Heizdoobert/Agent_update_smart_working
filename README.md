# Agent System

Cognitive engine for AI agents. CLI + zero-dependency MCP server. 3-tier memory, A*/MCTS planning, critic + reflection loop.

## Install

Python **>=3.14** (floor — 3.9–3.13 won't run).

```bash
pip install -e ".[embed]"     # [embed] = vector search (fastembed); drop if BM25 only
agent-system install --target mcp   # register MCP: Claude Desktop, Cursor, Windsurf, Antigravity
agent-system doctor              # health: DB, embeddings, clients, flow-task bridge
```

Env:
- `AGENT_SYSTEM_DB_DIR` — move DB (default `~/.agent_system/agent_system.db`)
- `AGENT_SYSTEM_NO_EMBED=1` — force BM25
- `AGENT_SYSTEM_LLM_PATCH=1` — `reflect` calls Claude to patch what rule-patcher can't

## Core flow

Plan (A*/MCTS), Critic score, Reflect (<=5 rounds), Output. Every output passes Critic before delivery.

## Modules

| | |
|---|---|
| `core/` | contracts, truncator (<3KB budget), session |
| `reasoning/` | AStarPlanner, MCTSPlanner, ThoughtGraph |
| `reflection/` | CriticEngine + adapters, SelfReflector |
| `memory/` | Episodic (recipe), Semantic (FTS5 BM25 + opt vectors), Scratchpad |
| `skills/` | scan + inject `SKILL.md` |
| `sdk/` | codebase scanner, onboarding wizard |
| `mcp/` | stdio server, JSON-RPC 2.0 |
| `cli/` | init, scan, mcp, plan, critic, reflect, memory, skill, session |
| `flow.py` | FLOW_SKILL task-engine bridge |

## FLOW_SKILL

MCP tools: `flow_task_submit` / `flow_task_status`, `flow_plan_create` / `flow_plan_approve` / `flow_plan_status`.
`flow_plan_approve` = human gate. Sub-agents run in parallel only after approval.

## Test

```bash
pytest tests/    # 167 passed, Python 3.14 (2026-11-23)
```

## Docs

- `QUICKSTART.md` — install + usage (verified commands)
- `docs/PROJECT_MAP.md` · `docs/specs/` · `docs/failure-taxonomy.md`
- `CAPABILITY_MAP.md` — 7-module map + specs
- `Archive/bigdata-v04/` — archived, not part of runtime
