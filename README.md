# Agent System

Cognitive engine cho AI agent. CLI + MCP server zero-dependency. Memory 3 tầng, planning A*/MCTS, critic + reflection loop.

## Cài đặt

Python **>=3.14** (floor — 3.9–3.13 không chạy).

```bash
pip install -e ".[embed]"     # [embed] = vector search (fastembed); bỏ nếu chỉ BM25
agent-system install --target mcp   # đăng ký MCP: Claude Desktop, Cursor, Windsurf, Antigravity
agent-system doctor              # health: DB, embeddings, clients, flow-task bridge
```

Env:
- `AGENT_SYSTEM_DB_DIR` — đổi chỗ DB (mặc định `~/.agent_system/agent_system.db`)
- `AGENT_SYSTEM_NO_EMBED=1` — ép BM25
- `AGENT_SYSTEM_LLM_PATCH=1` — `reflect` gọi Claude vá lỗi rule-patcher không vá được

## Core flow

Plan (A*/MCTS), Critic score, Reflect vá lỗi (<=5 vòng), Output. Mọi output qua Critic trước khi bàn giao.

## Modules

| | |
|---|---|
| `core/` | contracts, truncator (budget <3KB), session |
| `reasoning/` | AStarPlanner, MCTSPlanner, ThoughtGraph |
| `reflection/` | CriticEngine + adapters, SelfReflector |
| `memory/` | Episodic (recipe), Semantic (FTS5 BM25 + opt vectors), Scratchpad |
| `skills/` | scan + inject `SKILL.md` |
| `sdk/` | codebase scanner, onboarding wizard |
| `mcp/` | stdio server, JSON-RPC 2.0 |
| `cli/` | init, scan, mcp, plan, critic, reflect, memory, skill, session |
| `flow.py` | bridge FLOW_SKILL task engine |

## FLOW_SKILL

MCP tools: `flow_task_submit` / `flow_task_status`, `flow_plan_create` / `flow_plan_approve` / `flow_plan_status`.
`flow_plan_approve` = cổng OK của người. Sau đó mới chạy sub-agents song song.

## Test

```bash
pytest tests/    # 167 passed, Python 3.14 (2026-11-23)
```

## Docs

- `docs/PROJECT_MAP.md` · `docs/specs/` · `docs/failure-taxonomy.md`
- `CAPABILITY_MAP.md` — map 7 module + specs
- `Archive/bigdata-v04/` — đã archive, không phải phần chạy
