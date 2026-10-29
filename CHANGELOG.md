# Changelog

All notable changes to the `agent-system` framework will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

## [0.4.2] - 2026-10-29

### Added
- **Antigravity (AGY CLI) Installer Integration**: Added `agent-system install --target agy` (or `--target antigravity`) to automatically configure `~/.gemini/config/mcp_config.json` and inject universal rules into `~/.gemini/config/rules/AGENTS.md`.

## [0.4.1] - 2026-10-29

### Added
- **Automated Client Installer (`agent_system.sdk.installer`)**: Added `agent-system install [--target {all,claude,cursor,windsurf,mcp,rules}] [--dry-run]` to automatically configure MCP server entries and inject Universal System Instructions across AI agent clients.
- **Inline JSON & Pipeline Flexibility**: Enhanced CLI `_read_input` to parse inline JSON strings directly in `--initial` and `--actions` without intermediate temporary files.
- **Multi-Format Critic Routing**: Auto-detection and routing for Markdown prompt rules (`MarkdownRulesCritic`) and plugin manifests (`PluginManifestCritic`) across CLI `agent-system critic` and MCP tool `agent_critic`.
- **Hierarchical Project Map (`docs/PROJECT_MAP.md`)**: Structured Level 2/3 summary index for selective context loading and subagent isolation.

### Optimized
- **Rules File Synchronization**: Updated Level 1 rules files (`CLAUDE.md`, `GEMINI.md`, `AGENTS.md`) to include `agent_system.mcp` and new CLI commands (`scan`, `mcp`, `install`), strictly bounded at 3,024 bytes (<3KB) with 100/100 `MarkdownRulesCritic` score.

## [0.4.0] - 2026-10-29

### Added
- **Zero-Dependency Model Context Protocol (MCP) Server (`agent_system.mcp`)**:
  - `MCPServer`: Compliant JSON-RPC 2.0 stdio engine adhering to MCP Protocol Version `2024-11-05` using 100% Python standard library (`sys`, `json`, `dataclasses`).
  - `CognitiveToolsDispatcher`: Dispatches 8 core cognitive tools (`agent_plan`, `agent_critic`, `agent_reflect`, `agent_memory_search`, `agent_memory_recipe_record`, `agent_memory_recipe_get`, `agent_scan`, `agent_init_auto`) directly in-memory with sub-second latency ($<5$ms).
  - CLI subcommand: `agent-system mcp [--root PATH]` enabling native plug-and-play tool execution for Claude Desktop, Cursor, Antigravity, and Windsurf.
  - Documented **ADR-006** (`docs/decisions/0006-zero-dependency-mcp-server-protocol.md`) and **SPEC-mcp-server** (`docs/specs/SPEC-mcp-server.md`).
- **End-to-End Bidirectional Stdio MCP Test**: Added `tests/test_mcp_e2e.py` testing subprocess stdio piping and JSON-RPC handshakes.

### Optimized
- **MCP Response Helper Simplification**: Unified JSON-RPC response construction across all server methods via `_json_result` and `_json_error`.
- **Shared Persistent Storage Instance**: Lazily cached `SQLiteStore` instance across memory tool executions in `CognitiveToolsDispatcher`, preventing file descriptor churn.

## [0.3.0] - 2026-10-29

### Added
- **Brownfield Codebase Scanner (`agent_system.sdk.scanner`)**:
  - `CodebaseScanner` and `ProjectManifest` contracts extracting tech stack, test frameworks, build commands, and coding conventions from Python, Node/TS, Rust, Go, and Makefile manifests.
  - Bounded markdown documentation parser with heading extraction and safe I/O (up to 50KB per doc).
- **Dual-Tier Knowledge Ingestion Engine (`agent_system.sdk.ingestion`)**:
  - `KnowledgeIngester` synthesizing Tier 1 rules (`.agent/rules.md` and companion `AGENTS.md`) strictly bounded to $\le 3072$ bytes via `StructuralTruncator` and scoring 100/100 on `MarkdownRulesCritic`.
  - Tier 2 Semantic Memory ingestion chunking documentation by H2 headings (`## `) into SQLite Store for deep on-demand retrieval.
- **CLI Commands for Brownfield Onboarding (`agent_system.cli.main`)**:
  - Added `agent-system scan [--root PATH] [--json]` for machine-readable JSON payloads (consumed by AI Agent CLIs) or human-readable project summaries.
  - Added `agent-system init --auto [--root PATH] [--json]` for non-interactive first-time onboarding of brownfield codebases.
- **ADR-005**: Documented Context Hierarchy and Active Budget Governance (<3KB) in `docs/decisions/0005-context-engineering-hierarchy-and-budget-governance.md`.
- **Context Budget Multi-Plugin Guard**: Added `max_bytes=3072` constraint and automatic `StructuralTruncator` trimming to `PluginRegistry.get_project_rules()`.

### Optimized
- **Rules Context Compression**: Re-engineered project rules (`CLAUDE.md`, `GEMINI.md`, `AGENTS.md`) down to 2824 bytes (strictly under 3KB limit), achieving 100/100 pass score on `MarkdownRulesCritic` with zero diagnostics.
- **Code Simplification & Refactoring**:
  - Unified plugin hook dispatching in `PluginRegistry` via `_dispatch_pipe`, eliminating repetitive try-except loops across event triggers.
  - Extracted `_build_rule_critic_report` in `config_rules.py`, removing duplicate status and suggestion construction between `MarkdownRulesCritic` and `PluginManifestCritic`.
  - Simplified JSON byte calculations in `StructuralTruncator` with dedicated `_json_bytes` helper.
  - Replaced lambda assignments with named functions in `cli/main.py` and `astar.py` (PEP 8 compliance).
  - Streamlined `ActionDefinition.is_applicable` using generator expression with `all()`.
  - Removed unused template imports from `OnboardingWizard` scaffolding.

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
