# Implementation Plan: Standalone Agent Cognitive Framework (`agent_system`)

## Overview
Xây dựng **Agent Cognitive Framework** độc lập, domain-agnostic trong `Agent_system` nhằm trang bị năng lực nhận thức cấp cao cho AI Agents (Antigravity, Claude Code, Cursor) và các kỹ sư tự động hóa. Hệ thống kế thừa và chuẩn hóa các tinh hoa kiến trúc từ Knit (ToT/GoT, MCTS, In-Memory Self-Reflection, 3-Tier Memory, Dynamic Skills, Prompt Distillation) nhưng loại bỏ hoàn toàn các phụ thuộc đặc thù vào game/Airtest/Unity. Hệ thống hỗ trợ 100% offline thuần Python (sub-second latency), có cơ chế phòng thủ concurrency WAL mode, chống hỏng UTF-8/JSON khi giới hạn context <3KB, và cung cấp cả Python SDK lẫn CLI toolkit tương thích UNIX pipes.

## Architecture Decisions
- **Decoupled Contracts & Extensibility:** Mọi module giao tiếp qua dataclass và Protocol chuẩn (`ThoughtGraph`, `CriticProtocol`, `ActionSpace`, `MemoryItem`). Không hardcode bất kỳ giả định ngôn ngữ nào trong core.
- **Language-Agnostic Critic with Pluggable Adapters:** Core engine chỉ xử lý `CriticReport` và `DiagnosticItem`. Các kiểm tra cú pháp cụ thể (như Python AST) được triển khai qua adapter `PythonAstCritic`.
- **Hybrid Planning Engine ($A^*$ + MCTS):** Sử dụng $A^*$ Search cho không gian trạng thái tất định (nhanh, tối ưu toán học) và MCTS Planner cho không gian ngẫu nhiên/rollout.
- **Concurrency-Hardened 3-Tier Memory:** SQLite với `WAL mode` và `busy_timeout=5000` chống database lock khi nhiều agent chạy song song; FTS5 semantic search có fallback Pure-Python BM25; `StructuralTruncator` bảo vệ tính toàn vẹn UTF-8 và JSON trong hạn mức <3KB.
- **Stateful CLI via Session Tokens & UNIX Pipes:** Giải quyết vấn đề stateless giữa các tiến trình CLI bằng session persistence (`~/.agent_system/sessions/`) hoặc đọc/ghi trực tiếp qua stdin/stdout.
- **Separation of Runtime Inference vs. Batch Distillation:** Module `agent_system.distillation` được định vị là công cụ batch ngoại tuyến, không ràng buộc vào yêu cầu sub-second của runtime engine.

## Task List

### Phase 1: Foundations & Core Contracts
- [x] Task 1: Project Scaffolding, Core Contracts & Structural Truncator
- [x] Task 2: Session Manager & Concurrency-Safe SQLite Store
- [x] Task 3: 3-Tier Memory System (Episodic, Semantic FTS5 + BM25 Fallback, Scratchpad)

### Checkpoint: Foundation & Memory Layer
- [x] Core data contracts instantiate and validate cleanly
- [x] SQLite runs concurrently with WAL mode under stress tests
- [x] FTS5 queries and pure-Python BM25 fallback return identical ranked results
- [x] StructuralTruncator truncates JSON/text without UTF-8 or syntax corruption

### Phase 2: Planning & Reasoning Engines
- [x] Task 4: Directed Acyclic Thought Graph (DAG) & Cycle Detection
- [x] Task 5: Deterministic $A^*$ Planner & Stochastic MCTS Planner

### Checkpoint: Reasoning & Planning Layer
- [x] ThoughtGraph detects and rejects cyclical thought paths
- [x] $A^*$ finds provably shortest path in deterministic graph
- [x] MCTS rollout produces optimal path under stochastic simulation

### Phase 3: Self-Reflection & Multi-Stage Critic
- [x] Task 6: Abstract Critic Protocol, Report Schema & PythonAstCritic Adapter
- [x] Task 7: In-Memory Self-Reflection Engine with Bounded Fix Loops

### Checkpoint: Reflection & Verification Layer
- [x] Critic evaluates artifacts and outputs structured diagnostic reports
- [x] PythonAstCritic detects AST violations without crashing on non-Python inputs
- [x] Self-reflection loop repairs violations within bounded $N \le 3$ iterations

### Phase 4: Dynamic Skills & Batch Prompt Distillation
- [x] Task 8: Dynamic Skill Registry with Safe Schema Validation & Whitelisting
- [x] Task 9: Batch Prompt Distillation Engine (Teacher-Student Optimizer)

### Checkpoint: Skills & Optimization Layer
- [x] SkillRegistry loads, validates, and injects skills <3KB safely
- [x] Malicious or unwhitelisted skill files are rejected with clear errors
- [x] Distiller evaluates prompt variants and produces compressed student prompt

### Phase 5: CLI Suite, Integration & Verification
- [x] Task 10: Unified CLI Interface (`agent-system`) with UNIX Pipes & Session Support
- [x] Task 11: End-to-End Integration Tests, Benchmarks & Comprehensive Documentation

### Checkpoint: Complete System Production Ready
- [x] All CLI commands work via terminal and UNIX pipe redirection
- [x] 100% unit and integration tests pass with `pytest`
- [x] Documentation and quickstart examples verified end-to-end

### Phase 6: Pluggable SDK & Interactive Onboarding Wizard (`agent_system.sdk`)
- [x] Task 12: Markdown Fence Preservation in StructuralTruncator & SDK Contracts
- [x] Task 13: Instance-Based PluginRegistry with Safe Dynamic Loader & Whitelisting
- [x] Task 14: Interactive Onboarding Wizard with Safe I/O & Rollback
- [x] Task 15: CLI Integration (`init` subcommand, interactive bootstrap & optional `--actions` fallback)
- [x] Task 16: End-to-End SDK Integration Tests & Documentation

### Checkpoint: SDK Pluggable Architecture Verified
- [x] Third-party project can plug-in domain actions/critics and plug-out seamlessly
- [x] Interactive wizard safely scaffolds unconfigured projects without blocking automated CLI pipes
- [x] Markdown rules are safely bounded (<3KB) without breaking code blocks
- [x] 100% of existing and new test suites pass cleanly

### Phase 7: Brownfield Codebase Scanner & Dual-Tier Knowledge Ingestion (`agent_system.sdk.scanner` & `ingestion`)
- [x] Task 17: Core Codebase Scanner & Project Manifest Contract (`agent_system/sdk/scanner.py`)
- [x] Task 18: Dual-Tier Knowledge Ingestion Engine (`agent_system/sdk/ingestion.py`)
- [x] Task 19: CLI Commands (`scan` & `init --auto`) in `agent_system/cli/main.py`
- [x] Task 20: Integration Tests, End-to-End Verification & Documentation Update

### Checkpoint: Brownfield Codebase Scanner & Ingestion Verified
- [x] CodebaseScanner extracts manifest, test commands, rules from Python, Node/TS, Rust, Go, Makefile
- [x] Tier 1 `.agent/rules.md` is strictly bounded to $\le 3072$ bytes and passes MarkdownRulesCritic
- [x] Tier 2 Semantic Memory indexes documentation sections chunked by H2 headings
- [x] `agent-system scan --json` outputs structured metadata in $<200$ms
- [x] `agent-system init --auto` runs non-interactively without prompt blocking
- [x] 100% of entire test suite (96/96 tests) passes

## Risks and Mitigations
| Risk | Impact | Mitigation |
|------|--------|------------|
| SQLite database locking during concurrent subagent access | High | Enforce `PRAGMA journal_mode=WAL;` and `busy_timeout=5000` with exponential backoff retry wrapper. |
| In-memory scratchpad state lost across CLI runs | Med | Implement file/SQLite session backing with `--session <id>` and standard UNIX JSON pipe support. |
| Non-Python artifacts failing AST critic | High | Make `CriticProtocol` abstract and place Python AST checking in `PythonAstCritic` adapter. |
| FTS5 unavailable in minimal Python environments | Med | Provide a pure-Python in-memory BM25 inverted index fallback. |
| Context truncation corrupting UTF-8 or JSON | High | Implement `StructuralTruncator` that respects unicode grapheme and JSON/line boundaries. |

## Open Questions
- None. (All architectural ambiguities resolved via `interview-me` and reconciled via `doubt-driven-development`).
