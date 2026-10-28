# Agent System (`agent_system`)

> **Domain-Agnostic Cognitive Agent Framework** trang bị năng lực nhận thức cấp cao (High-Level Cognitive Reasoning) cho AI Agents và các hệ thống tự hành.

Hệ thống được thiết kế độc lập 100% (domain-agnostic), thuần Python, có khả năng chạy offline đạt độ trễ cực nhanh (<100ms), bảo vệ giới hạn context window (<3KB) không làm rách UTF-8 / vỡ JSON, và an toàn concurrency đa luồng / liên tiến trình.

---

## 🏛️ Kiến trúc 5 Trụ cột Nhận thức

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        AI Agent / Orchestrator                         │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │
      ┌────────────────────────────┼────────────────────────────┐
      ▼                            ▼                            ▼
┌──────────────┐          ┌──────────────────┐          ┌──────────────┐
│  Reasoning   │          │  Reflection &    │          │ 3-Tier       │
│  & Planning  │          │  Critic Loop     │          │ Memory Engine│
│ ──────────── │          │ ──────────────── │          │ ──────────── │
│ • ToT/GoT DAG│          │ • CriticProtocol │          │ • Episodic   │
│ • Cycle Det. │          │ • PythonAstCritic│          │ • Semantic   │
│ • A* Search  │          │ • SelfReflector  │          │   (FTS5/BM25)│
│ • MCTS UCT   │          │ • Oscillation Det│          │ • Scratchpad │
└──────────────┘          └──────────────────┘          └──────────────┘
      │                            │                            │
      └────────────────────────────┼────────────────────────────┘
                                   ▼
          ┌────────────────────────────────────────────────┐
          │      Dynamic Skills & Offline Distillation     │
          │ ────────────────────────────────────────────── │
          │ • Whitelisted SkillRegistry (SKILL.md)         │
          │ • StructuralTruncator (Safe UTF-8/JSON <3KB)   │
          │ • Teacher-to-Student Prompt Distillation       │
          └────────────────────────────────────────────────┘
```

1. **Lập luận & Quy hoạch (Reasoning & Planning):**
   - **ThoughtGraph (ToT/GoT DAG):** Quản lý cây và đồ thị tư duy, hỗ trợ rẽ nhánh và ghép nhánh (fusion), tích hợp thuật toán phát hiện chu trình (Cycle Detection).
   - **$A^*$ Planner:** Tìm kiếm đường đi ngắn nhất, chi phí tối ưu trên không gian trạng thái tất định.
   - **MCTS Planner:** Tìm kiếm Monte Carlo Tree Search với công thức UCT cho không gian ngẫu nhiên và mô phỏng rollout.

2. **Tự phản tỉnh & Thẩm định đa tầng (Reflection & Critic):**
   - **CriticProtocol:** Giao diện thẩm định độc lập ngôn ngữ xuất ra `CriticReport` và `DiagnosticItem`.
   - **PythonAstCritic:** Adapter kiểm tra tĩnh cú pháp Python, cấm import nguy hiểm (`pdb`, `eval`), kiểm tra type annotations mà không gây crash trên artifact khác.
   - **SelfReflector:** Vòng lặp tự sửa code/artifact trong bộ nhớ với giới hạn an toàn ($N \le 3$) và phát hiện dao động (oscillation detection).

3. **Bộ nhớ 3 tầng chịu tải cao (Concurrency-Hardened 3-Tier Memory):**
   - **Episodic Memory:** Lưu vết thực thi và củng cố công thức sửa lỗi (`recovery_recipes`).
   - **Semantic Memory:** Đánh chỉ mục văn bản, tìm kiếm FTS5 + BM25 ranking; tự động chuyển sang fallback Pure-Python BM25 nếu môi trường thiếu FTS5.
   - **Working Scratchpad:** Quản lý ngữ cảnh tạm thời cô lập theo từng phiên (`session`).
   - **SQLiteStore:** Cấu hình `PRAGMA journal_mode=WAL;` và `PRAGMA busy_timeout=5000;` chống database lock khi chạy song song.

4. **Quản lý Kỹ năng Động (Dynamic Skill Registry):**
   - Tự động nạp kỹ năng từ `SKILL.md` qua whitelist thư mục và kiểm tra schema frontmatter.
   - Tiêm context vào prompt với cơ chế bảo vệ `<3KB` bằng `StructuralTruncator`.

5. **Chưng cất Prompt Ngoại tuyến (Batch Prompt Distillation):**
   - Tối ưu hóa prompt theo phương pháp Teacher-to-Student từ các execution traces.
   - Hoạt động tách biệt ở chế độ batch, không gây chậm trễ runtime.

---

## 🚀 Cài đặt & Khởi động nhanh

### Yêu cầu môi trường
- Python 3.9 trở lên
- Không yêu cầu bắt buộc bất kỳ external LLM API nào để chạy core engine.

### Cài đặt thư viện
```bash
cd /mnt/second_drive/Agent_system
pip install -e .
```

---

## 💻 Sử dụng Python SDK

```python
from agent_system.reasoning.astar import AStarPlanner
from agent_system.reasoning.transition import ActionDefinition, StateMachineTransitionModel, StateNode
from agent_system.reflection.critic import CriticEngine
from agent_system.reflection.adapters.python_ast import PythonAstCritic
from agent_system.reflection.reflector import SelfReflector
from agent_system.memory.semantic import SemanticMemory

# 1. Tìm đường tối ưu với A* Planner
initial_state = StateNode("init", {"extracted": False, "loaded": False})
actions = [
    ActionDefinition("extract", cost=1.0, preconditions={"extracted": False}, effects={"extracted": True}),
    ActionDefinition("load", cost=1.0, preconditions={"extracted": True, "loaded": False}, effects={"loaded": True}),
]
model = StateMachineTransitionModel(actions)
planner = AStarPlanner(model)
plan = planner.plan(initial_state, lambda s: s.get("loaded") is True)
print("Plan steps:", [s.action_type for s in plan.steps])

# 2. Tự sửa code với SelfReflector
critic = CriticEngine([PythonAstCritic()])
reflector = SelfReflector(critic)
result = reflector.reflect_and_patch("import pdb\ndef hello(): pass")
print("Patched artifact:\n", result.final_artifact)

# 3. Tìm kiếm ngữ nghĩa BM25 (<3KB budget)
semantic = SemanticMemory()
semantic.index_document("guide_1", "Hướng dẫn triển khai cognitive agent với A* và reflection")
results = semantic.search("cognitive agent", top_k=1)
print("Found doc:", results[0].content)
```

---

## 🛠️ Sử dụng CLI (`agent-system`)

Hỗ trợ đầy đủ tương thích với UNIX pipeline (`stdin` / `stdout`) và quản lý session liên lệnh:

```bash
# 1. Kiểm tra phiên bản và trợ giúp
agent-system --help
agent-system --version

# 2. Thẩm định mã nguồn (Critic) qua stdin hoặc file
cat draft.py | agent-system critic --file -

# 3. Tự phản tỉnh và sửa mã lỗi
agent-system reflect --file draft.py --output-code > clean.py

# 4. Quản lý phiên làm việc liên tiến trình
agent-system session set --id task_01 --key status --value "in_progress"
agent-system session get --id task_01

# 5. Tìm kiếm bộ nhớ ngữ nghĩa
agent-system memory search --query "quy trình phục hồi lỗi" --top-k 3

# 6. Nạp ngữ cảnh kỹ năng động dưới 3KB
agent-system skill inject --names "code-auditor" --max-bytes 3072
```

---

## 🧪 Chạy Test Suite

```bash
PYTHONPATH=. python3 -m pytest tests/ -v
```

100% test cases (41/41 unit & integration tests) vượt qua với thời gian thực thi dưới 0.3 giây.
