# Agent System - Operating Protocol & Guidelines

Welcome to the **Agent System (`agent_system`)** repository. All AI agents working in this repository MUST strictly follow these rules, architecture standards, and operating protocols.

---

## 1. Non-Negotiable Core Rules

1. **Domain-Agnostic Core**:
   - The core framework under `agent_system/` MUST remain 100% domain-agnostic.
   - Never introduce hardcoded game, GUI, or platform-specific dependencies into the core engine. All specializations belong in adapters (`agent_system/reflection/adapters/`).

2. **Strict Context Budget (<3KB)**:
   - Any context injection or retrieved semantic memory payload must be bounded by 3072 bytes (3KB) using `StructuralTruncator`.
   - Never slice raw UTF-8 bytes directly (`[:3072]`); always preserve unicode character and JSON structural integrity.

3. **Concurrency-Safe Persistence**:
   - All SQLite access MUST use `SQLiteStore` configured with `PRAGMA journal_mode=WAL;` and `PRAGMA busy_timeout=5000;`.
   - Never open raw unconfigured sqlite connections that could trigger database locking across concurrent agents.

4. **In-Memory Reflection Before Output**:
   - When generating or refactoring code/plans, run through `CriticEngine` and `SelfReflector` to ensure zero AST/rule violations before final handoff.

5. **Test-Driven Verification**:
   - Every change must be verified by running the test suite:
     ```bash
     PYTHONPATH=. python3 -m pytest tests/ -v
     ```
   - 100% of tests must pass before concluding any task.

---

## 2. Architecture Map

| Module | Purpose | Key Classes |
|---|---|---|
| [`agent_system.core`](file:///mnt/second_drive/Agent_system/agent_system/core/) | Standard contracts, protocols, session management, and safe truncator | `TaskGoal`, `Plan`, `ThoughtNode`, `CriticReport`, `StructuralTruncator`, `SessionManager` |
| [`agent_system.reasoning`](file:///mnt/second_drive/Agent_system/agent_system/reasoning/) | Tree/Graph of Thoughts (ToT/GoT DAG), $A^*$ Search, and MCTS Planner | `ThoughtGraph`, `AStarPlanner`, `MCTSPlanner`, `StateMachineTransitionModel` |
| [`agent_system.reflection`](file:///mnt/second_drive/Agent_system/agent_system/reflection/) | Multi-stage Critic Engine and in-memory self-reflection auto-patcher | `CriticEngine`, `SchemaCritic`, `PythonAstCritic`, `SelfReflector` |
| [`agent_system.memory`](file:///mnt/second_drive/Agent_system/agent_system/memory/) | 3-Tier memory: Episodic (traces), Semantic (FTS5 + BM25), Scratchpad | `EpisodicMemory`, `SemanticMemory`, `WorkingScratchpad` |
| [`agent_system.skills`](file:///mnt/second_drive/Agent_system/agent_system/skills/) | Dynamic skill discovery, path whitelisting, and schema validation | `SkillRegistry`, `SkillDefinition` |
| [`agent_system.distillation`](file:///mnt/second_drive/Agent_system/agent_system/distillation/) | Offline Teacher-Student batch prompt optimization | `DistillationEngine`, `PromptCandidate` |
| [`agent_system.cli`](file:///mnt/second_drive/Agent_system/agent_system/cli/) | Unified command-line interface with UNIX pipe support | `agent_system.cli.main` (`plan`, `critic`, `reflect`, `memory`, `skill`, `session`) |

---

## 3. Command Reference

```bash
# Run unit tests
PYTHONPATH=. python3 -m pytest tests/ -v

# Run CLI planning
python3 -m agent_system.cli.main plan --initial state.json --actions actions.json --goal-key is_ready

# Run CLI code audit / critic
cat script.py | python3 -m agent_system.cli.main critic --file -

# Run CLI self-reflection
python3 -m agent_system.cli.main reflect --file draft.py --output-code
```
