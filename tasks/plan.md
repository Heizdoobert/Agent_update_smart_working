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
- [ ] Task 1: Project Scaffolding, Core Contracts & Structural Truncator
- [ ] Task 2: Session Manager & Concurrency-Safe SQLite Store
- [ ] Task 3: 3-Tier Memory System (Episodic, Semantic FTS5 + BM25 Fallback, Scratchpad)

### Checkpoint: Foundation & Memory Layer
- [ ] Core data contracts instantiate and validate cleanly
- [ ] SQLite runs concurrently with WAL mode under stress tests
- [ ] FTS5 queries and pure-Python BM25 fallback return identical ranked results
- [ ] StructuralTruncator truncates JSON/text without UTF-8 or syntax corruption

### Phase 2: Planning & Reasoning Engines
- [ ] Task 4: Directed Acyclic Thought Graph (DAG) & Cycle Detection
- [ ] Task 5: Deterministic $A^*$ Planner & Stochastic MCTS Planner

### Checkpoint: Reasoning & Planning Layer
- [ ] ThoughtGraph detects and rejects cyclical thought paths
- [ ] $A^*$ finds provably shortest path in deterministic graph
- [ ] MCTS rollout produces optimal path under stochastic simulation

### Phase 3: Self-Reflection & Multi-Stage Critic
- [ ] Task 6: Abstract Critic Protocol, Report Schema & PythonAstCritic Adapter
- [ ] Task 7: In-Memory Self-Reflection Engine with Bounded Fix Loops

### Checkpoint: Reflection & Verification Layer
- [ ] Critic evaluates artifacts and outputs structured diagnostic reports
- [ ] PythonAstCritic detects AST violations without crashing on non-Python inputs
- [ ] Self-reflection loop repairs violations within bounded $N \le 3$ iterations

### Phase 4: Dynamic Skills & Batch Prompt Distillation
- [ ] Task 8: Dynamic Skill Registry with Safe Schema Validation & Whitelisting
- [ ] Task 9: Batch Prompt Distillation Engine (Teacher-Student Optimizer)

### Checkpoint: Skills & Optimization Layer
- [ ] SkillRegistry loads, validates, and injects skills <3KB safely
- [ ] Malicious or unwhitelisted skill files are rejected with clear errors
- [ ] Distiller evaluates prompt variants and produces compressed student prompt

### Phase 5: CLI Suite, Integration & Verification
- [ ] Task 10: Unified CLI Interface (`agent-system`) with UNIX Pipes & Session Support
- [ ] Task 11: End-to-End Integration Tests, Benchmarks & Comprehensive Documentation

### Checkpoint: Complete System Production Ready
- [ ] All CLI commands work via terminal and UNIX pipe redirection
- [ ] 100% unit and integration tests pass with `pytest`
- [ ] Documentation and quickstart examples verified end-to-end

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
