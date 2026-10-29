# Changelog

All notable changes to the `agent-system` framework will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.2.0] - 2026-10-29

### Added
- **Pluggable SDK Architecture (`agent_system.sdk`)**:
  - `BasePlugin`, `PluginManifest`, and `ProjectContext` contracts for external project extensibility.
  - `PluginRegistry` with safe dynamic module loader using `importlib.util.spec_from_file_location` and strict Path Whitelisting.
  - Multi-plugin support with priority-based conflict resolution and deduplication on Action names.
  - Plugin Hook Event Bus: added `on_before_plan`, `on_after_plan`, and `on_critic_report` hooks to `BasePlugin`.
- **Interactive Project Onboarding Wizard (`agent_system.sdk.wizard`)**:
  - `OnboardingWizard` with safe I/O (`isatty` checks) and automated rollback on `KeyboardInterrupt`/`EOFError`.
  - Scaffolding of `.agent/rules.md`, `agent_plugin.json`, and template `plugin.py`.
  - Added CLI subcommand `agent-system init`.
- **Configuration & Rules Critic Adapters (`agent_system.reflection.adapters.config_rules`)**:
  - `MarkdownRulesCritic` validating top-level headings, even markdown code fences, and context byte budgets.
  - `PluginManifestCritic` validating manifest JSON schema, Python identifiers, SemVer format, and rules path.
- **Top-level CLI Entrypoints**:
  - Added `agent_system/__main__.py` and `agent_system/cli/__main__.py` supporting `python3 -m agent_system` and `python3 -m agent_system.cli`.
- **Architecture Decision Records (ADRs)**:
  - Documented ADR-001 through ADR-004 in `docs/decisions/`.

### Changed
- **Markdown Code Fence Preservation in StructuralTruncator**:
  - Automatically detects odd markdown code fences (` ``` `) when truncating under 3KB and appends a closing fence before `...[TRUNCATED]`.
- **CLI Planning Action Fallback**:
  - Parameter `--actions` in `agent-system plan` is now optional; automatically falls back to actions supplied by the active project plugin.
- **Lazy CLI Import**:
  - Refactored `agent_system/cli/__init__.py` with lazy `__getattr__` to eliminate `runpy` RuntimeWarnings.

### Optimized
- **BM25 Search & Indexing Performance**:
  - Replaced $O(N)$ doc length summing in `PurePythonBM25.add_document` with $O(1)$ accumulator `total_doc_len` (4.18x speedup on 10,000 docs).
  - Implemented targeted term cleanup in document updates (27.70x speedup on 1,000 updates).
- **MCTS UCT Node Selection**:
  - Precomputed parent visit log factor at the parent node level, eliminating redundant `math.log` calls across children.

---

## [0.1.0] - 2026-10-28

### Added
- **Core Cognitive Architecture (`agent_system.core`)**:
  - Data contracts: `TaskGoal`, `Plan`, `ActionStep`, `ThoughtNode`, `CriticReport`, `DiagnosticItem`, `TraceRecord`.
  - `StructuralTruncator` for unicode-safe and JSON-syntactic truncation (<3KB).
  - Cross-process `SessionManager`.
- **Reasoning Engines (`agent_system.reasoning`)**:
  - Directed Acyclic Thought Graph (`ThoughtGraph`) with cycle detection and node fusion.
  - Deterministic $A^*$ Planner (`AStarPlanner`).
  - Stochastic Monte Carlo Tree Search (`MCTSPlanner`).
  - Discrete `StateMachineTransitionModel` and hashable `StateNode`.
- **Reflection & Critic Engine (`agent_system.reflection`)**:
  - Composite `CriticEngine` and `SchemaCritic`.
  - `PythonAstCritic` auditing AST syntax, type annotations, and forbidden calls.
  - `SelfReflector` with bounded loop ($N \le 3$) and oscillation detection.
- **3-Tier Memory & Storage (`agent_system.memory`, `agent_system.storage`)**:
  - `EpisodicMemory` for execution traces and recovery recipes.
  - Hybrid `SemanticMemory` (SQLite FTS5 with pure-Python BM25 fallback).
  - `WorkingScratchpad` with fine-grained per-session locking.
  - Concurrency-hardened `SQLiteStore` (`PRAGMA journal_mode=WAL;` and `busy_timeout=5000;`).
- **Dynamic Skills & Batch Prompt Distillation (`agent_system.skills`, `agent_system.distillation`)**:
  - `SkillRegistry` with filesystem whitelisting and YAML frontmatter parsing.
  - `DistillationEngine` for offline Teacher-Student prompt optimization.
- **Unified CLI (`agent_system.cli`)**:
  - Subcommands: `plan`, `critic`, `reflect`, `memory`, `skill`, `session`.
  - Standard UNIX pipe (`stdin`/`stdout`) support.
