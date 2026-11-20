# FEATURE_MAP — Agent System (verification-harness)

Bản đồ tính năng + cách verify. Agent đọc file này để biết: tính năng nào, entry point ở đâu, làm sao xác nhận nó "Working" (không phải chỉ "build pass").

## Entry Points

| Surface | Entry | Ghi chú |
|---|---|---|
| CLI | `python -m agent_system.cli.main <cmd>` | hoặc `agent-system <cmd>` (console script) |
| MCP server | `agent-system mcp` | JSON-RPC 2.0 stdio |
| Python API | `from agent_system import ...` | `CriticEngine`, `AStarPlanner`, `MemoryLayer`… |
| Plugin SDK | `agent_system/sdk/` | `PluginRegistry`, `installer` |
| Doctor | `agent-system doctor [--json]` | health report |

## Flows (mỗi flow có Verification)

### F-1 Plan (A* / MCTS)
- **Entry:** `agent-system plan --initial <json> --actions <json> --goal-key K --goal-value V --method astar|mcts`
- **Contract:** `ActionDefinition{name, cost, preconditions, effects}`; state = dict phẳng.
- **Verification:** `bash scripts/verify/verify_cli.sh` → check `06_plan_astar.log` phải có JSON `plan_id` + `steps[]`. **Empty log = FAIL.**

### F-2 Critic (audit)
- **Entry:** `agent-system critic --file <path> --language auto|python|json|markdown|manifest`
- **Contract:** output JSON `{summary, diagnostics, suggestions}`, score 0–100.
- **Verification:** `05_critic.log` phải có `"summary": "...PASS (Score: 100.0/100)"`.

### F-3 Memory (semantic + episodic)
- **Entry:** `agent-system memory index|search|recipe-record|recipe-get`
- **Verification:** `memory search` trả ≥1 kết quả cho query đã index; `recipe-get` trả recipe đã record. (Chưa tự-động — chạy tay, ghi evidence.)

### F-4 Skill (discovery + injection)
- **Entry:** `agent-system skill list|get|inject`
- **Verification:** `03_skill_list.log` có danh sách skill; `skill inject` trả bounded context.

### F-5 Session (token mgmt)
- **Entry:** `agent-system session list|get|set|delete`
- **Verification:** `04_session_list.log` chạy sạch; `session set` + `get` round-trip đúng giá trị.

### F-6 Doctor (health)
- **Entry:** `agent-system doctor [--json]`
- **Verification:** `02_doctor.log` có các dòng `OK`/`warn` cho memory DB, embeddings, mcp-clients, flow-task.

### F-7 Reflect (self-repair)
- **Entry:** `agent-system reflect --file <path> --max-iterations N [--output-code]`
- **Verification:** code lỗi được patch; `--output-code` trả code sửa; max 5 iterations.

## Definition of Done (DoD) — BẮT BUỘC

| Domain | "Working" nghĩa là | CHUYỂN TỐI THIỂU (không đủ = chưa Done) |
|---|---|---|
| **CLI** | command chạy đúng + output đúng contract + evidence log không rỗng | "build pass" / import không lỗi |
| **Perf** | dưới ngưỡng (ví dụ plan < 200ms cho 2-state) + có số đo | "chạy được" |
| **UI** | user flow hoàn thành end-to-end + screenshot/evidence | "render không crash" |
| **Memory** | data round-trip đúng (write→read) | "DB tạo được" |

> **Quy tắc cứng:** một tính năng chỉ "Done" khi có **evidence không rỗng** + **contract đúng** + **commit SHA** (xem `.agent/rules.md` §8 + `docs/SESSION_RITUAL.md`).
