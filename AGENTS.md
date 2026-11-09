# Agent System - Operating Protocol & Guidelines

All AI agents in this repository MUST strictly follow these rules and standards.

---

## 1. Non-Negotiable Core Rules

1. **Domain-Agnostic Core**: `agent_system/` MUST remain 100% domain-agnostic. Specializations belong in adapters (`agent_system/reflection/adapters/`).
2. **Strict Context Budget (<3KB)**: Context payloads must be bounded by 3072 bytes (3KB) via `StructuralTruncator`. Never slice raw UTF-8 bytes directly.
3. **Concurrency-Safe Persistence**: SQLite MUST use `SQLiteStore` (`PRAGMA journal_mode=WAL;`, `PRAGMA busy_timeout=5000;`).
4. **In-Memory Reflection Before Output**: Run generation/code through `CriticEngine` & `SelfReflector` before handoff.
5. **Test-Driven Verification**: 100% tests must pass: `/usr/bin/python3.11 -m pytest -v`.

---

## 2. Autonomous Adaptive Reflexion Protocol
- Bất kỳ lỗi phát sinh (test fail, build break, critic < 100): Agent tự động thực thi chu trình Reflexion từ skill `adaptive-self-healing-agent` (RCA -> Reflect -> Auto-retry max 3 lần -> Record recipe).
- Không yêu cầu người dùng can thiệp trừ khi đã thử 3 lần không thành công (HITL escalation).

---

## 3. Hierarchical Sub-Agent Token Optimization (Bắt buộc Phân cấp & Tiết kiệm Token)
- **Model chính trong session là Người quản lý cuối (Lead Architect):**
  - Chuyên trách: Lập kế hoạch tổng thể (ToT/GoT DAG), phân tách bài toán, giao việc, tổng hợp báo cáo và nghiệm thu chất lượng cuối cùng.
  - Không trực tiếp làm việc chân tay (chạy test, đọc file log hàng trăm dòng, quét file, sửa lặt vặt).
- **Mỗi tác vụ là 1 Sub-agent độc lập (Parallel / Isolated Tasks):**
  - Tách mọi công việc thành các sub-agent độc lập, chạy song song để tối đa hóa tốc độ và giữ context window session < 3KB.
- **Quy tắc phân bổ Model cho Sub-agent:**
  - **`flash_lite` (Việc tay chân):** Quét file (`find`, `grep`), chạy test runner, đọc log/trace lỗi, tra cứu bộ nhớ (`agent_memory_search`).
  - **`flash` (Triển khai & Kiểm thử):** Viết code tính năng, vá bug cụ thể, viết unit test, kiểm tra định dạng.
  - **`inherit` / `pro` (Đặc thù cấp cao):** Chỉ dành cho thẩm định kiến trúc trừu tượng hoặc audit bảo mật chuyên sâu.

---

## 4. Architecture Map

| Module | Purpose | Key Classes |
|---|---|---|
| [`agent_system.core`](file:///mnt/second_drive/SKILL/agent_system/core/) | Contracts, protocols, session, safe truncator | `TaskGoal`, `Plan`, `ThoughtNode`, `StructuralTruncator` |
| [`agent_system.reasoning`](file:///mnt/second_drive/SKILL/agent_system/reasoning/) | ToT/GoT DAG, $A^*$ Search, MCTS Planner | `ThoughtGraph`, `AStarPlanner`, `MCTSPlanner` |
| [`agent_system.reflection`](file:///mnt/second_drive/Agent_system/agent_system/reflection/) | Multi-stage Critic & self-reflection | `CriticEngine`, `PythonAstCritic`, `SelfReflector` |
| [`agent_system.memory`](file:///mnt/second_drive/Agent_system/agent_system/memory/) | 3-Tier memory: Episodic, Semantic, Scratchpad | `EpisodicMemory`, `SemanticMemory`, `WorkingScratchpad` |
| [`agent_system.skills`](file:///mnt/second_drive/Agent_system/agent_system/skills/) | Dynamic skill discovery & validation | `SkillRegistry`, `SkillDefinition` |
| [`agent_system.sdk`](file:///mnt/second_drive/Agent_system/agent_system/sdk/) | Pluggable SDK, scanner, ingestion & wizard | `BasePlugin`, `PluginRegistry`, `CodebaseScanner` |
| [`agent_system.distillation`](file:///mnt/second_drive/Agent_system/agent_system/distillation/) | Offline prompt optimization | `DistillationEngine`, `PromptCandidate` |
| [`agent_system.mcp`](file:///mnt/second_drive/Agent_system/agent_system/mcp/) | Zero-dep MCP stdio server & tools dispatcher | `MCPServer`, `CognitiveToolsDispatcher` |
| [`agent_system.cli`](file:///mnt/second_drive/Agent_system/agent_system/cli/) | CLI with UNIX pipe support | `agent_system.cli.main` (`init`, `plan`, `critic`, `mcp`, `scan`) |
| [`tri_modal_router`](file:///mnt/second_drive/SKILL/tri_modal_router/) | Multi-tier execution routing | `TriModalRouter`, `ExecutionTier` |
| [`data_pipeline`](file:///mnt/second_drive/SKILL/data_pipeline/) | Streaming CSV chunking & DuckDB worker | `QuoteAwareChunker`, `DuckDBWorker` |
| [`distributed_queue`](file:///mnt/second_drive/SKILL/distributed_queue/) | Celery distributed task dispatcher & circuit breaker | `TaskDispatcher`, `celery_app` |
| [`memory_layer`](file:///mnt/second_drive/SKILL/memory_layer/) | 3-Tier vector & episodic memory | `MemoryAPI`, `AgentHooks`, `KnowledgeRetriever` |

---

## 5. Command Reference

```bash
# Run unit tests
/usr/bin/python3.11 -m pytest -v

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
