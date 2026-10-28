# Task List: Agent Cognitive Framework (`agent_system`)

## Task 1: Project Scaffolding, Core Contracts & Structural Truncator

**Description:** Thiết lập cấu trúc thư mục dự án chuẩn `agent_system`, file `pyproject.toml`, các dataclass cốt lõi (`ThoughtNode`, `Plan`, `ActionStep`, `CriticReport`, `DiagnosticItem`, `TraceRecord`) và module `StructuralTruncator` (cắt tỉa payload an toàn UTF-8 & JSON dưới giới hạn 3KB).

**Acceptance criteria:**
- [x] Cấu trúc package `agent_system` và `tests/` được khởi tạo đúng chuẩn Python module.
- [x] Các hợp đồng kiểu dữ liệu (contracts) được định nghĩa đầy đủ với Python `dataclasses` và `typing`.
- [x] `StructuralTruncator` cắt tỉa chuỗi text, JSON, và traceback không làm rách byte UTF-8 và không làm vỡ cấu trúc JSON cú pháp.

**Verification:**
- [x] Tests pass: `pytest tests/test_contracts.py`
- [x] Build succeeds: `python3 -m py_compile agent_system/core/contracts.py agent_system/core/truncator.py`
- [x] Manual check: Truncate chuỗi UTF-8 tiếng Việt và JSON object vượt quá 3KB, kiểm tra parse lại JSON thành công.

**Dependencies:** None

**Files likely touched:**
- `pyproject.toml`
- `agent_system/__init__.py`
- `agent_system/core/contracts.py`
- `agent_system/core/truncator.py`
- `tests/test_contracts.py`

**Estimated scope:** Medium (4 files)

---

## Task 2: Session Manager & Concurrency-Safe SQLite Store

**Description:** Xây dựng tầng kết nối lưu trữ SQLite với cơ chế chống tranh chấp (`WAL mode`, `busy_timeout=5000`) và `SessionManager` để quản lý trạng thái phiên làm việc liên tiến trình (persistent session tokens).

**Acceptance criteria:**
- [x] `SQLiteStore` tự động khởi tạo kết nối với cấu hình `PRAGMA journal_mode=WAL;` và `PRAGMA busy_timeout=5000;`.
- [x] Xử lý an toàn các giao dịch đồng thời (concurrency retry wrapper).
- [x] `SessionManager` cho phép tạo, tải, cập nhật và lưu trữ session context qua token ID.

**Verification:**
- [x] Tests pass: `pytest tests/test_storage.py`
- [x] Concurrency check: Kiểm tra nhiều tiến trình/thread cùng ghi đồng thời vào database mà không gặp `database is locked`.

**Dependencies:** Task 1

**Files likely touched:**
- `agent_system/storage/sqlite_store.py`
- `agent_system/core/session.py`
- `tests/test_storage.py`

**Estimated scope:** Medium (3 files)

---

## Task 3: 3-Tier Memory System (Episodic, Semantic FTS5 + BM25 Fallback, Scratchpad)

**Description:** Triển khai hoàn chỉnh bộ nhớ 3 tầng: Episodic Memory (lưu lịch sử hành động & công thức sửa lỗi), Semantic Memory (SQLite FTS5 + fallback pure-Python BM25 cho môi trường thiếu FTS5), và Working Scratchpad (quản lý ngữ cảnh tạm thời trong session).

**Acceptance criteria:**
- [x] `EpisodicMemory` ghi nhận và truy xuất các execution traces, recovery recipes theo thẻ `task_id` / `category`.
- [x] `SemanticMemory` đánh chỉ mục văn bản, tìm kiếm FTS5 + BM25 ranking với giới hạn tải <3KB context.
- [x] Khi FTS5 không khả dụng, hệ thống tự động chuyển sang fallback In-Memory BM25 mà không ném ngoại lệ.
- [x] `WorkingScratchpad` hỗ trợ context manager cho session cô lập.

**Verification:**
- [x] Tests pass: `pytest tests/test_memory.py`
- [x] Fallback check: Chạy test giả lập SQLite không có module FTS5 và xác nhận semantic search vẫn trả về kết quả chính xác.

**Dependencies:** Task 1, Task 2

**Files likely touched:**
- `agent_system/memory/episodic.py`
- `agent_system/memory/semantic.py`
- `agent_system/memory/scratchpad.py`
- `agent_system/memory/__init__.py`
- `tests/test_memory.py`

**Estimated scope:** Medium (5 files)

---

## Checkpoint: Foundation & Memory Layer
- [x] Tất cả unit test cho Contracts, Truncator, Storage và 3-Tier Memory chạy qua (`pytest tests/test_contracts.py tests/test_storage.py tests/test_memory.py`).
- [x] Concurrency an toàn dưới nhiều thread/process ghi đồng thời.
- [x] Context payload được kiểm soát chặt chẽ dưới 3KB mà không rách ký tự.

---

## Task 4: Directed Acyclic Thought Graph (DAG) & Cycle Detection

**Description:** Xây dựng cấu trúc đồ thị tư duy `ThoughtGraph` cho Tree/Graph of Thoughts (ToT/GoT) hỗ trợ đa nhánh, phát hiện và ngăn chặn vòng lặp vô tận (cycle detection), cùng các thao tác ghép nhánh/tỉa nhánh.

**Acceptance criteria:**
- [x] `ThoughtGraph` quản lý các `ThoughtNode`, biểu diễn quan hệ cha-con và đa cha (multi-parent fusion).
- [x] Tự động phát hiện chu trình (cycle detection) và ném lỗi hoặc phạt điểm khi xuất hiện cạnh quay vòng $A \to B \to A$.
- [x] Hỗ trợ serialize/deserialize đồ thị ra JSON chuẩn.

**Verification:**
- [x] Tests pass: `pytest tests/test_thought_graph.py`
- [x] Cycle check: Kiểm tra đồ thị có vòng lặp bị chặn ngay lập tức.

**Dependencies:** Task 1

**Files likely touched:**
- `agent_system/reasoning/graph.py`
- `tests/test_thought_graph.py`

**Estimated scope:** Small (2 files)

---

## Task 5: Deterministic $A^*$ Planner & Stochastic MCTS Planner

**Description:** Triển khai 2 bộ lập kế hoạch nhận thức: $A^*$ Search cho không gian trạng thái tất định (tối ưu hóa heuristic toán học) và MCTS Planner cho không gian xác suất/rollout với công thức UCT.

**Acceptance criteria:**
- [x] Giao diện `ActionSpace` và `TransitionModel` chuẩn cho cả chế độ offline và mở rộng.
- [x] `AStarPlanner` tìm đường đi ngắn nhất, chi phí tối ưu trên đồ thị trạng thái tất định.
- [x] `MCTSPlanner` thực hiện Selection, Expansion, Simulation (Rollout), và Backpropagation dựa trên điểm số UCT.
- [x] Cho phép định nghĩa hàm heuristic tùy chỉnh (path length, risk penalty, prerequisite readiness).

**Verification:**
- [x] Tests pass: `pytest tests/test_planners.py`
- [x] Performance check: Cả hai planner hoàn thành dưới 100ms trên đồ thị thử nghiệm chuẩn.

**Dependencies:** Task 1, Task 4

**Files likely touched:**
- `agent_system/reasoning/transition.py`
- `agent_system/reasoning/astar.py`
- `agent_system/reasoning/mcts.py`
- `agent_system/reasoning/__init__.py`
- `tests/test_planners.py`

**Estimated scope:** Medium (5 files)

---

## Checkpoint: Reasoning & Planning Layer
- [x] $A^*$ và MCTS đều chạy thành công trên các kịch bản test đơn vị.
- [x] Đồ thị tư duy DAG bảo toàn tính không chu trình.
- [x] Thời gian giải bài toán heuristic đạt mức sub-second (<100ms).

---

## Task 6: Abstract Critic Protocol, Report Schema & PythonAstCritic Adapter

**Description:** Xây dựng hệ thống thẩm định chuẩn `CriticProtocol` độc lập ngôn ngữ, cơ chế tính điểm (0-100), xuất `CriticReport` cấu trúc chi tiết, và hiện thực hóa adapter `PythonAstCritic` để kiểm tra tĩnh mã Python.

**Acceptance criteria:**
- [x] `CriticProtocol` định nghĩa phương thức `validate(artifact, context) -> CriticReport`.
- [x] `CriticReport` trả về trạng thái `PASS` / `REJECT`, điểm số (0-100), và danh sách `DiagnosticItem` có mã lỗi, dòng, và đề xuất sửa.
- [x] `PythonAstCritic` kiểm tra các tiêu chuẩn tĩnh Python (cấm hardcode, kiểm tra import, contract invariants) mà không gây crash trên artifact không phải Python.

**Verification:**
- [x] Tests pass: `pytest tests/test_critic.py`
- [x] Robustness check: Đưa chuỗi text, JSON hoặc YAML vào `PythonAstCritic` và kiểm tra xử lý graceful thay vì `SyntaxError`.

**Dependencies:** Task 1

**Files likely touched:**
- `agent_system/reflection/critic.py`
- `agent_system/reflection/adapters/python_ast.py`
- `agent_system/reflection/__init__.py`
- `tests/test_critic.py`

**Estimated scope:** Medium (4 files)

---

## Task 7: In-Memory Self-Reflection Engine with Bounded Fix Loops

**Description:** Xây dựng vòng lặp tự phản biện và vá lỗi trong bộ nhớ (`SelfReflector`). Đánh giá bản nháp qua Critic, tự động áp dụng các công thức sửa lỗi tất định (Fix Recipes), đảm bảo giới hạn vòng lặp $N \le 3$ và kiểm tra bảo toàn bất biến (invariant checking).

**Acceptance criteria:**
- [x] `SelfReflector` chạy vòng lặp phản tỉnh: Generate -> Critic -> Reflect -> Patch -> Re-evaluate.
- [x] Tự động dừng sau tối đa 3 vòng lặp ($N \le 3$) để tránh lặp vô tận.
- [x] Phát hiện hiện tượng dao động (oscillation detection) khi sửa lỗi này sinh lỗi kia.
- [x] Trả về artifact đã sửa cùng lịch sử phản tỉnh chi tiết.

**Verification:**
- [x] Tests pass: `pytest tests/test_reflection.py`
- [x] Oscillation check: Kiểm tra cơ chế tự ngắt khi gặp luật xung đột nhau.

**Dependencies:** Task 6

**Files likely touched:**
- `agent_system/reflection/reflector.py`
- `tests/test_reflection.py`

**Estimated scope:** Small (2 files)

---

## Checkpoint: Reflection & Verification Layer
- [x] Critic tổng quát hoạt động ổn định trên nhiều loại artifact.
- [x] Vòng lặp phản tỉnh tự động sửa được các lỗi cơ bản và dừng an toàn trong tối đa 3 chu kỳ.

---

## Task 8: Dynamic Skill Registry with Safe Schema Validation & Whitelisting

**Description:** Xây dựng `SkillRegistry` tự động phát hiện, tải và quản lý các kỹ năng từ file markdown (`SKILL.md`), có cơ chế whitelist thư mục, kiểm tra schema frontmatter và trích xuất ngữ cảnh tinh gọn <3KB.

**Acceptance criteria:**
- [ ] Quét và nạp các dynamic skills từ thư mục cấu hình.
- [ ] Kiểm tra tính toàn vẹn và bảo mật (whitelist thư mục, validate schema YAML frontmatter).
- [ ] Trích xuất context tiêm vào prompt với payload được kiểm soát chặt chẽ <3KB.

**Verification:**
- [ ] Tests pass: `pytest tests/test_skills.py`
- [ ] Security check: Thử nạp skill từ đường dẫn không hợp lệ hoặc frontmatter sai cú pháp, đảm bảo bị từ chối an toàn.

**Dependencies:** Task 1

**Files likely touched:**
- `agent_system/skills/registry.py`
- `agent_system/skills/__init__.py`
- `tests/test_skills.py`

**Estimated scope:** Small (3 files)

---

## Task 9: Batch Prompt Distillation Engine (Teacher-Student Optimizer)

**Description:** Xây dựng module ngoại tuyến `agent_system.distillation` để tối ưu hóa prompt qua phương pháp Teacher-to-Student, chưng cất kinh nghiệm từ các vết thực thi (traces) thành student prompt tinh gọn.

**Acceptance criteria:**
- [ ] Thu thập và cấu trúc hóa các execution traces thành dataset huấn luyện / benchmark.
- [ ] Hỗ trợ đánh giá điểm số của các biến thể prompt trên tập test case.
- [ ] Tách biệt hoàn toàn khỏi runtime sub-second engine, có CLI riêng cho tác vụ batch.

**Verification:**
- [ ] Tests pass: `pytest tests/test_distiller.py`

**Dependencies:** Task 1, Task 3

**Files likely touched:**
- `agent_system/distillation/distiller.py`
- `agent_system/distillation/__init__.py`
- `tests/test_distiller.py`

**Estimated scope:** Small (3 files)

---

## Checkpoint: Skills & Optimization Layer
- [ ] Quản lý skill động an toàn, chống prompt injection cục bộ.
- [ ] Engine tối ưu prompt chạy độc lập ở chế độ batch không ảnh hưởng runtime.

---

## Task 10: Unified CLI Interface (`agent-system`) with UNIX Pipes & Session Support

**Description:** Xây dựng giao diện dòng lệnh hợp nhất `agent-system` với các lệnh con: `plan`, `reflect`, `critic`, `memory`, `skill`, `distill`, `session`. Hỗ trợ pipeline UNIX (`stdin`/`stdout`) và tham số `--session <id>`.

**Acceptance criteria:**
- [ ] CLI hỗ trợ các subcommand: `plan`, `reflect`, `critic`, `memory`, `skill`, `distill`, `session`.
- [ ] Hỗ trợ đọc input từ `stdin` và xuất JSON ra `stdout` để ghép pipeline bash (e.g. `cat input.json | agent-system critic`).
- [ ] Hỗ trợ cờ `--session` để duy trì trạng thái qua nhiều câu lệnh CLI liên tiếp.

**Verification:**
- [ ] Tests pass: `pytest tests/test_cli.py`
- [ ] CLI manual verification: Chạy thử `agent-system --help` và các subcommand cơ bản trên terminal.

**Dependencies:** Tasks 1-9

**Files likely touched:**
- `agent_system/cli/main.py`
- `agent_system/cli/__init__.py`
- `tests/test_cli.py`

**Estimated scope:** Medium (3 files)

---

## Task 11: End-to-End Integration Tests, Benchmarks & Comprehensive Documentation

**Description:** Viết kịch bản kiểm thử tích hợp toàn diện (E2E Integration Tests), đo lường benchmark hiệu năng (độ trễ và bộ nhớ), và hoàn thiện tài liệu hướng dẫn sử dụng (`README.md`, `CLAUDE.md`, tài liệu kiến trúc).

**Acceptance criteria:**
- [ ] Toàn bộ chu trình từ Planning -> Reflection -> Critic -> Memory -> Storage chạy mượt mà trong bài test E2E.
- [ ] Đo lường độ trễ: Chu kỳ planning và critic nội bộ hoàn thành < 100ms.
- [ ] File `README.md` và `CLAUDE.md` hướng dẫn đầy đủ cách cài đặt, sử dụng Python SDK và CLI commands.

**Verification:**
- [ ] Full suite pass: `pytest tests/` (100% pass)
- [ ] CLI check: `agent-system --version` và các luồng mẫu thực thi không lỗi.

**Dependencies:** Tasks 1-10

**Files likely touched:**
- `tests/test_e2e.py`
- `README.md`
- `CLAUDE.md`

**Estimated scope:** Medium (3 files)

---

## Final Checkpoint: Complete System Production Ready
- [ ] 100% test cases pass trên toàn bộ test suite.
- [ ] Hệ thống hoạt động độc lập hoàn toàn, không có dependency nào của game Knit hay Airtest.
- [ ] Sẵn sàng để các AI Agent khác gọi qua Python SDK hoặc CLI.
