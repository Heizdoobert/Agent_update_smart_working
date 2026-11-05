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

# Immutable Task Execution Workflow

Mỗi khi thực hiện bất kỳ task nào, Agent BẮT BUỘC tuân thủ nghiêm ngặt quy trình làm việc bất di bất dịch theo đúng 12 bước sau:

1. **Research Information**: Thu thập đầy đủ dữ kiện, log, mã nguồn liên quan và hiện trạng hệ thống trước khi đưa ra bất kỳ kết luận nào.
2. **Thinking Why**: Phân tích sâu nguyên nhân gốc rễ (Root Cause Analysis), tại sao lỗi xảy ra, dựa trên cơ chế nào (OS, ADB, Virtualization, Logic code).
3. **How Can Do That**: Xác định các hướng tiếp cận có thể giải quyết vấn đề.
4. **How Can Fix That**: Lựa chọn giải pháp tối ưu và chính xác nhất để khắc phục triệt để.
5. **Did It Effect Anything**: Đánh giá toàn diện tác động phụ (Blast Radius & Side Effects), đảm bảo không làm vỡ các module khác và TUYỆT ĐỐI không thay đổi bất kỳ đường dẫn (path) nào trong code.
6. **Spec**: Lập đặc tả kỹ thuật chi tiết cho giải pháp.
7. **Plan**: Lập kế hoạch các bước triển khai cụ thể, rõ ràng.
8. **Build**: Tiến hành chỉnh sửa code/triển khai giải pháp theo đúng Spec và Plan.
9. **Test**: Chạy kiểm thử tự động (Unit Test / Integration Test / Diag Script) để xác thực.
10. **Review**: Tự rà soát lại toàn bộ diff, kiểm tra edge cases và đảm bảo tính nguyên vẹn của codebase.
11. **Simply Code**: Tinh giản code, loại bỏ code thừa/phức tạp không cần thiết, giữ code gọn gàng, trong sáng và dễ bảo trì.
12. **Report What and Why You Do That**: Báo cáo chi tiết cho người dùng: ĐÃ LÀM GÌ, TẠI SAO LÀM NHƯ VẬY, và kết quả đạt được.
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
# Immutable Task Execution Workflow

Mỗi khi thực hiện bất kỳ task nào, Agent BẮT BUỘC tuân thủ nghiêm ngặt quy trình làm việc bất di bất dịch theo đúng 12 bước sau:

1. **Research Information**: Thu thập đầy đủ dữ kiện, log, mã nguồn liên quan và hiện trạng hệ thống trước khi đưa ra bất kỳ kết luận nào.
2. **Thinking Why**: Phân tích sâu nguyên nhân gốc rễ (Root Cause Analysis), tại sao lỗi xảy ra, dựa trên cơ chế nào (OS, ADB, Virtualization, Logic code).
3. **How Can Do That**: Xác định các hướng tiếp cận có thể giải quyết vấn đề.
4. **How Can Fix That**: Lựa chọn giải pháp tối ưu và chính xác nhất để khắc phục triệt để.
5. **Did It Effect Anything**: Đánh giá toàn diện tác động phụ (Blast Radius & Side Effects), đảm bảo không làm vỡ các module khác và TUYỆT ĐỐI không thay đổi bất kỳ đường dẫn (path) nào trong code.
6. **Spec**: Lập đặc tả kỹ thuật chi tiết cho giải pháp.
7. **Plan**: Lập kế hoạch các bước triển khai cụ thể, rõ ràng.
8. **Build**: Tiến hành chỉnh sửa code/triển khai giải pháp theo đúng Spec và Plan.
9. **Test**: Chạy kiểm thử tự động (Unit Test / Integration Test / Diag Script) để xác thực.
10. **Review**: Tự rà soát lại toàn bộ diff, kiểm tra edge cases và đảm bảo tính nguyên vẹn của codebase.
11. **Simply Code**: Tinh giản code, loại bỏ code thừa/phức tạp không cần thiết, giữ code gọn gàng, trong sáng và dễ bảo trì.
12. **Report What and Why You Do That**: Báo cáo chi tiết cho người dùng: ĐÃ LÀM GÌ, TẠI SAO LÀM NHƯ VẬY, và kết quả đạt được.
```
