# Agent System - Operating Protocol & Guidelines

All AI agents in this repository MUST strictly follow these rules and standards.

---

## 1. Non-Negotiable Core Rules

1. **Domain-Agnostic Core**: `agent_system/` MUST remain 100% domain-agnostic. Specializations belong in adapters (`agent_system/reflection/adapters/`).
2. **Strict Context Budget (<3KB)**: Context payloads must be bounded by 3072 bytes (3KB) via `StructuralTruncator`. Never slice raw UTF-8 bytes directly.
3. **Concurrency-Safe Persistence**: SQLite MUST use `SQLiteStore` (`PRAGMA journal_mode=WAL;`, `PRAGMA busy_timeout=5000;`).
4. **In-Memory Reflection Before Output**: Run generation/code through `CriticEngine` & `SelfReflector` before handoff.
5. **Test-Driven Verification**: 100% tests must pass: `PYTHONPATH=. python3 -m pytest tests/ -v`.

---

## 2. Architecture Map

| Module | Purpose | Key Classes |
|---|---|---|
| [`agent_system.core`](file:///mnt/second_drive/Agent_system/agent_system/core/) | Contracts, protocols, session, safe truncator | `TaskGoal`, `Plan`, `ThoughtNode`, `StructuralTruncator` |
| [`agent_system.reasoning`](file:///mnt/second_drive/Agent_system/agent_system/reasoning/) | ToT/GoT DAG, $A^*$ Search, MCTS Planner | `ThoughtGraph`, `AStarPlanner`, `MCTSPlanner` |
| [`agent_system.reflection`](file:///mnt/second_drive/Agent_system/agent_system/reflection/) | Multi-stage Critic & self-reflection | `CriticEngine`, `PythonAstCritic`, `SelfReflector` |
| [`agent_system.memory`](file:///mnt/second_drive/Agent_system/agent_system/memory/) | 3-Tier memory: Episodic, Semantic, Scratchpad | `EpisodicMemory`, `SemanticMemory`, `WorkingScratchpad` |
| [`agent_system.skills`](file:///mnt/second_drive/Agent_system/agent_system/skills/) | Dynamic skill discovery & validation | `SkillRegistry`, `SkillDefinition` |
| [`agent_system.sdk`](file:///mnt/second_drive/Agent_system/agent_system/sdk/) | Pluggable SDK, scanner, ingestion & wizard | `BasePlugin`, `PluginRegistry`, `CodebaseScanner` |
| [`agent_system.distillation`](file:///mnt/second_drive/Agent_system/agent_system/distillation/) | Offline prompt optimization | `DistillationEngine`, `PromptCandidate` |
| [`agent_system.mcp`](file:///mnt/second_drive/Agent_system/agent_system/mcp/) | Zero-dep MCP stdio server & tools dispatcher | `MCPServer`, `CognitiveToolsDispatcher` |
| [`agent_system.cli`](file:///mnt/second_drive/Agent_system/agent_system/cli/) | CLI with UNIX pipe support | `agent_system.cli.main` (`init`, `plan`, `critic`, `mcp`, `scan`) |

---

## 3. Command Reference

```bash
# Run unit tests
PYTHONPATH=. python3 -m pytest tests/ -v

# Codebase scan & brownfield onboarding
agent-system scan --root .
agent-system init --auto

# Model Context Protocol (MCP) server
agent-system mcp

# CLI planning / critic / reflect
python3 -m agent_system.cli.main plan --initial state.json --goal-key is_ready
cat script.py | python3 -m agent_system.cli.main critic --file -
python3 -m agent_system.cli.main reflect --file draft.py --output-code
```
