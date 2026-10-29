# Agent System - Hierarchical Project Map

This document provides a modular index of `Agent_system` for hierarchical context loading (Level 2/3). AI agents should selectively load only the sections relevant to their immediate task.

---

## 1. Core Architecture (`agent_system/core/`)
**Purpose:** Pure abstractions, domain-agnostic contracts, session state, and context safety.
- **Key Files:**
  - [`contracts.py`](file:///mnt/second_drive/Agent_system/agent_system/core/contracts.py): Base dataclasses (`TaskGoal`, `Plan`, `ThoughtNode`, `CriticReport`, `DiagnosticItem`).
  - [`protocols.py`](file:///mnt/second_drive/Agent_system/agent_system/core/protocols.py): Runtime checkable interfaces (`PlannerProtocol`, `CriticProtocol`, `MemoryProtocol`).
  - [`session.py`](file:///mnt/second_drive/Agent_system/agent_system/core/session.py): Cross-tool session token persistence via `SessionManager`.
  - [`truncator.py`](file:///mnt/second_drive/Agent_system/agent_system/core/truncator.py): `StructuralTruncator` ensuring strict $\le 3072$ bytes (<3KB) UTF-8 and Markdown/JSON block integrity.
- **Invariants:** 100% domain-agnostic; no external dependencies.

---

## 2. Reasoning & Planning Engine (`agent_system/reasoning/`)
**Purpose:** Non-linear thought exploration (Tree/Graph of Thoughts) and deterministic pathfinding.
- **Key Files:**
  - [`graph.py`](file:///mnt/second_drive/Agent_system/agent_system/reasoning/graph.py): `ThoughtGraph` maintaining a Directed Acyclic Graph (DAG) with cycle detection and thought fusion.
  - [`astar.py`](file:///mnt/second_drive/Agent_system/agent_system/reasoning/astar.py): `AStarPlanner` for optimal pathfinding under known state-action models.
  - [`mcts.py`](file:///mnt/second_drive/Agent_system/agent_system/reasoning/mcts.py): `MCTSPlanner` with Monte Carlo Tree Search rollouts for stochastic/complex decision spaces.
  - [`transition.py`](file:///mnt/second_drive/Agent_system/agent_system/reasoning/transition.py): `ActionDefinition`, `StateNode`, and transition model primitives.
- **Patterns:** State immutability; hashing and equality based on state dictionary keys.

---

## 3. Reflection & Critic Engine (`agent_system/reflection/`)
**Purpose:** Multi-stage static evaluation and in-memory self-repair loops before output.
- **Key Files:**
  - [`critic.py`](file:///mnt/second_drive/Agent_system/agent_system/reflection/critic.py): `CriticEngine` orchestrating aggregated evaluations across registered critics.
  - [`reflector.py`](file:///mnt/second_drive/Agent_system/agent_system/reflection/reflector.py): `SelfReflector` executing iterative auto-patching loops (max 3 iterations) to achieve 100/100 score.
  - [`adapters/python_ast.py`](file:///mnt/second_drive/Agent_system/agent_system/reflection/adapters/python_ast.py): `PythonAstCritic` detecting syntax errors, forbidden builtins (`eval`, `exec`, `breakpoint`), and type hints.
  - [`adapters/config_rules.py`](file:///mnt/second_drive/Agent_system/agent_system/reflection/adapters/config_rules.py): `MarkdownRulesCritic` (budget & fence validation) and `PluginManifestCritic`.
- **Invariants:** Reflection happens entirely in RAM; write to disk only after achieving green status.

---

## 4. 3-Tier Memory System (`agent_system/memory/`)
**Purpose:** Long-term and short-term knowledge persistence across sessions.
- **Key Files:**
  - [`episodic.py`](file:///mnt/second_drive/Agent_system/agent_system/memory/episodic.py): `EpisodicMemory` storing problem-recovery recipes (`recipe-record`, `recipe-get`).
  - [`semantic.py`](file:///mnt/second_drive/Agent_system/agent_system/memory/semantic.py): `SemanticMemory` with SQLite FTS5 BM25 search and fallback to pure-Python in-memory BM25.
  - [`scratchpad.py`](file:///mnt/second_drive/Agent_system/agent_system/memory/scratchpad.py): `WorkingScratchpad` for transient session-scoped key-value state.
- **Invariants:** Thread-safe SQLite WAL mode via `SQLiteStore` (`busy_timeout=5000`).

---

## 5. Dynamic Skills Management (`agent_system/skills/`)
**Purpose:** Modular capability discovery and progressive context prompt injection.
- **Key Files:**
  - [`registry.py`](file:///mnt/second_drive/Agent_system/agent_system/skills/registry.py): `SkillRegistry` scanning, validating, and injecting `SKILL.md` definitions.
  - [`parser.py`](file:///mnt/second_drive/Agent_system/agent_system/skills/parser.py): Zero-dependency YAML frontmatter parser for skill metadata.

---

## 6. Pluggable SDK & Brownfield Onboarding (`agent_system/sdk/`)
**Purpose:** Extensibility framework, automated codebase scanning, and dual-tier knowledge ingestion.
- **Key Files:**
  - [`contracts.py`](file:///mnt/second_drive/Agent_system/agent_system/sdk/contracts.py): `BasePlugin`, `PluginManifest`, `EventBus`, and lifecycle hooks.
  - [`registry.py`](file:///mnt/second_drive/Agent_system/agent_system/sdk/registry.py): `PluginRegistry` supporting multi-plugin precedence, sandbox isolation, and merged rules.
  - [`scanner.py`](file:///mnt/second_drive/Agent_system/agent_system/sdk/scanner.py): `CodebaseScanner` detecting manifests across Python, Node/TS, Go, Rust, Make.
  - [`ingestion.py`](file:///mnt/second_drive/Agent_system/agent_system/sdk/ingestion.py): `KnowledgeIngester` synthesizing Tier 1 rules (`.agent/rules.md` $\le 3072$ bytes) and chunking Tier 2 semantic docs.
  - [`wizard.py`](file:///mnt/second_drive/Agent_system/agent_system/sdk/wizard.py): `OnboardingWizard` 4-question interactive or non-interactive scaffolding.

---

## 7. Model Context Protocol (MCP) Server (`agent_system/mcp/`)
**Purpose:** Native agent connectivity for Claude Desktop, Cursor, Antigravity, and Windsurf.
- **Key Files:**
  - [`server.py`](file:///mnt/second_drive/Agent_system/agent_system/mcp/server.py): Zero-dependency JSON-RPC 2.0 stdio server compliant with MCP `2024-11-05`.
  - [`tools.py`](file:///mnt/second_drive/Agent_system/agent_system/mcp/tools.py): `CognitiveToolsDispatcher` exposing 8 core cognitive tools with sub-second execution.
- **Invariants:** `sys.stdout` carries exclusively newline-delimited JSON-RPC; all logs route to `sys.stderr`.

---

## 8. Offline Prompt Distillation (`agent_system/distillation/`)
**Purpose:** Offline candidate generation, evaluation, and compression of system prompts.
- **Key Files:**
  - [`engine.py`](file:///mnt/second_drive/Agent_system/agent_system/distillation/engine.py): `DistillationEngine` optimizing prompt variants against test suites.

---

## 9. CLI Tooling & Pipeline (`agent_system/cli/`)
**Purpose:** CLI interface with UNIX pipe support (`init`, `scan`, `mcp`, `plan`, `critic`, `reflect`, `memory`, `skill`, `session`).
- **Key File:**
  - [`main.py`](file:///mnt/second_drive/Agent_system/agent_system/cli/main.py): Single entry point for `agent-system` binary.
