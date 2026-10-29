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
- [x] Quét và nạp các dynamic skills từ thư mục cấu hình.
- [x] Kiểm tra tính toàn vẹn và bảo mật (whitelist thư mục, validate schema YAML frontmatter).
- [x] Trích xuất context tiêm vào prompt với payload được kiểm soát chặt chẽ <3KB.

**Verification:**
- [x] Tests pass: `pytest tests/test_skills.py`
- [x] Security check: Thử nạp skill từ đường dẫn không hợp lệ hoặc frontmatter sai cú pháp, đảm bảo bị từ chối an toàn.

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
- [x] Thu thập và cấu trúc hóa các execution traces thành dataset huấn luyện / benchmark.
- [x] Hỗ trợ đánh giá điểm số của các biến thể prompt trên tập test case.
- [x] Tách biệt hoàn toàn khỏi runtime sub-second engine, có CLI riêng cho tác vụ batch.

**Verification:**
- [x] Tests pass: `pytest tests/test_distiller.py`

**Dependencies:** Task 1, Task 3

**Files likely touched:**
- `agent_system/distillation/distiller.py`
- `agent_system/distillation/__init__.py`
- `tests/test_distiller.py`

**Estimated scope:** Small (3 files)

---

## Checkpoint: Skills & Optimization Layer
- [x] Quản lý skill động an toàn, chống prompt injection cục bộ.
- [x] Engine tối ưu prompt chạy độc lập ở chế độ batch không ảnh hưởng runtime.

---

## Task 10: Unified CLI Interface (`agent-system`) with UNIX Pipes & Session Support

**Description:** Xây dựng giao diện dòng lệnh hợp nhất `agent-system` với các lệnh con: `plan`, `reflect`, `critic`, `memory`, `skill`, `distill`, `session`. Hỗ trợ pipeline UNIX (`stdin`/`stdout`) và tham số `--session <id>`.

**Acceptance criteria:**
- [x] CLI hỗ trợ các subcommand: `plan`, `reflect`, `critic`, `memory`, `skill`, `distill`, `session`.
- [x] Hỗ trợ đọc input từ `stdin` và xuất JSON ra `stdout` để ghép pipeline bash (e.g. `cat input.json | agent-system critic`).
- [x] Hỗ trợ cờ `--session` để duy trì trạng thái qua nhiều câu lệnh CLI liên tiếp.

**Verification:**
- [x] Tests pass: `pytest tests/test_cli.py`
- [x] CLI manual verification: Chạy thử `agent-system --help` và các subcommand cơ bản trên terminal.

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
- [x] Toàn bộ chu trình từ Planning -> Reflection -> Critic -> Memory -> Storage chạy mượt mà trong bài test E2E.
- [x] Đo lường độ trễ: Chu kỳ planning và critic nội bộ hoàn thành < 100ms.
- [x] File `README.md` và `CLAUDE.md` hướng dẫn đầy đủ cách cài đặt, sử dụng Python SDK và CLI commands.

**Verification:**
- [x] Full suite pass: `pytest tests/` (100% pass)
- [x] CLI check: `agent-system --version` và các luồng mẫu thực thi không lỗi.

**Dependencies:** Tasks 1-10

**Files likely touched:**
- `tests/test_e2e.py`
- `README.md`
- `CLAUDE.md`

**Estimated scope:** Medium (3 files)

---

## Final Checkpoint: Complete System Production Ready
- [x] 100% test cases pass trên toàn bộ test suite.
- [x] Hệ thống hoạt động độc lập hoàn toàn, không có dependency nào của game Knit hay Airtest.
- [x] Sẵn sàng để các AI Agent khác gọi qua Python SDK hoặc CLI.

---

# Phase 6: Pluggable SDK & Interactive Onboarding Wizard (`agent_system.sdk`)

## Task 12: Markdown Fence Preservation in StructuralTruncator & SDK Contracts

**Description:** Nâng cấp `StructuralTruncator` tự động đóng code fence markdown (` ``` `) khi cắt chuỗi <3KB, và xây dựng các hợp đồng giao diện cốt lõi cho SDK trong `agent_system/sdk/contracts.py` (`PluginManifest`, `BasePlugin`, `ProjectContext`).

**Acceptance criteria:**
- [x] `StructuralTruncator.truncate_text` phát hiện số lượng dấu markdown code fence lẻ và tự động thêm `\n```\n` trước chuỗi hậu tố `...[TRUNCATED]`.
- [x] `BasePlugin` khai báo chuẩn xác `get_actions() -> List[ActionDefinition]`, `get_critics() -> List[CriticProtocol]`, và `get_rules() -> str`.
- [x] `PluginManifest` định nghĩa đầy đủ metadata cấu hình (tên, version, description, entrypoint, rules_path).

**Verification:**
- [x] Tests pass: `pytest tests/test_sdk_contracts.py tests/test_contracts.py`
- [x] Manual check: Truncate đoạn markdown chứa code block dài >3KB, kiểm tra khối code block kết thúc bằng ```` ``` ```` hợp lệ.

**Dependencies:** None (kế thừa từ Phase 1-5)

**Files likely touched:**
- `agent_system/core/truncator.py`
- `agent_system/sdk/__init__.py`
- `agent_system/sdk/contracts.py`
- `tests/test_sdk_contracts.py`

**Estimated scope:** Small (3-4 files)

---

## Task 13: Instance-Based PluginRegistry with Safe Dynamic Loader & Whitelisting

**Description:** Hiện thực hóa `PluginRegistry` theo mô hình instance độc lập (tránh đột biến singleton toàn cục), tự động phát hiện `agent_plugin.json`, nạp động class kế thừa `BasePlugin` bằng `importlib.util.spec_from_file_location` với kiểm tra an toàn thư mục (chống ACE & Module Shadowing).

**Acceptance criteria:**
- [x] `PluginRegistry` chỉ nạp các file plugin nằm bên trong Project Root đã được xác thực, không chèn CWD vào `sys.path`.
- [x] Không chia sẻ trạng thái mutable toàn cục giữa các instance registry khác nhau.
- [x] Xử lý an toàn khi file manifest hoặc code plugin bị lỗi cú pháp: ghi log cảnh báo và fallback về chế độ thuần Core (Plug-out an toàn).

**Verification:**
- [x] Tests pass: `pytest tests/test_sdk_registry.py`
- [x] Security check: Thử nạp plugin trỏ ra ngoài project root, kiểm tra bị từ chối với ngoại lệ `PermissionError`.

**Dependencies:** Task 12

**Files likely touched:**
- `agent_system/sdk/registry.py`
- `tests/test_sdk_registry.py`

**Estimated scope:** Medium (2-3 files)

---

## Task 14: Interactive Onboarding Wizard with Safe I/O & Rollback

**Description:** Xây dựng `OnboardingWizard` tại `agent_system/sdk/wizard.py` để phỏng vấn tương tác 4 câu hỏi định hình dự án, validate tên định danh hợp lệ (`str.isidentifier()`), bắt an toàn `KeyboardInterrupt`/`EOFError`, và sinh trọn gói cấu trúc `.agent/rules.md`, `agent_plugin.json`, cùng `plugin.py`.

**Acceptance criteria:**
- [x] Hỏi 4 câu hỏi thiết lập: (1) Project Name, (2) Prompt Rules summary, (3) Custom Actions, (4) Critic requirements.
- [x] Xác thực tính hợp lệ của identifier (tên biến, tên action Python); từ chối các ký tự đặc biệt nguy hiểm.
- [x] Bắt ngoại lệ khi người dùng hủy (Ctrl+C / Ctrl+D) và dọn dẹp sạch các file rác đang ghi dở.

**Verification:**
- [x] Tests pass: `pytest tests/test_sdk_wizard.py`
- [x] Simulation check: Giả lập stdin trong test case, kiểm tra các file sinh ra có cú pháp Python và JSON hoàn toàn hợp lệ.

**Dependencies:** Task 12, Task 13

**Files likely touched:**
- `agent_system/sdk/wizard.py`
- `tests/test_sdk_wizard.py`

**Estimated scope:** Medium (2-3 files)

---

## Task 15: CLI Integration (`init` Subcommand, Interactive Bootstrap & Optional `--actions`)

**Description:** Tích hợp SDK vào giao diện dòng lệnh: bổ sung subcommand `agent-system init`, kích hoạt wizard an toàn khi chạy root command `agent-system` không kèm tham số trong terminal tương tác (TTY), và cập nhật `cmd_plan` để tham số `--actions` là tùy chọn khi plugin đã cung cấp action.

**Acceptance criteria:**
- [x] Lệnh `agent-system init` kích hoạt trực tiếp `OnboardingWizard`.
- [x] Chạy `agent-system` gốc trong terminal TTY chưa cấu hình plugin sẽ gợi ý/kích hoạt wizard; tuyệt đối KHÔNG chặn các lệnh con (`critic`, `session`, `plan`, `memory`, `skill`) hoặc khi chạy qua pipe/subagent.
- [x] Lệnh `agent-system plan` tự động lấy actions từ plugin nếu không truyền flag `--actions`.

**Verification:**
- [x] Tests pass: `pytest tests/test_cli_sdk.py tests/test_cli.py`
- [x] Pipe check: `cat script.py | agent-system critic` chạy trơn tru, không bao giờ bị wizard chặn.

**Dependencies:** Task 13, Task 14

**Files likely touched:**
- `agent_system/cli/main.py`
- `tests/test_cli_sdk.py`
- `tests/test_cli.py`

**Estimated scope:** Medium (3 files)

---

## Task 16: End-to-End SDK Integration Tests & Documentation

**Description:** Xây dựng kịch bản kiểm thử E2E hoàn chỉnh từ lúc khởi tạo dự án -> nạp plugin -> tiêm rules dự án (<3KB) -> lập kế hoạch với custom action -> kiểm định với custom critic -> tháo plugin (plug-out), đồng thời cập nhật tài liệu hướng dẫn (`README.md`, `GEMINI.md`).

**Acceptance criteria:**
- [x] Kịch bản E2E kiểm tra toàn bộ vòng đời Plug-in và Plug-out thành công 100%.
- [x] Tài liệu `README.md` và `GEMINI.md` bổ sung hướng dẫn chi tiết cách viết plugin và sử dụng lệnh `agent-system init`.
- [x] 100% test cases (toàn bộ các test cũ + test mới) vượt qua.

**Verification:**
- [x] Full suite pass: `PYTHONPATH=. pytest tests/ -v` (toàn bộ 100% tests pass).
- [x] Static Critic Audit: Toàn bộ code mới đạt điểm 100/100 qua `CriticEngine`.

**Dependencies:** Tasks 12-15

**Files likely touched:**
- `tests/test_sdk_e2e.py`
- `README.md`
- `GEMINI.md`

**Estimated scope:** Medium (3 files)

---

## Final Checkpoint: Pluggable SDK & Wizard Verified
- [x] Toàn bộ 5 task mới hoàn thành trọn vẹn với đầy đủ unit test.
- [x] Không có bất kỳ vi phạm AST, kiểu dữ liệu hay rò rỉ trạng thái toàn cục.
- [x] Toàn bộ test suite pass 100%.

---

# Phase 7: Brownfield Codebase Scanner & Dual-Tier Knowledge Ingestion

## Task 17: Core Codebase Scanner & Project Manifest Contract

**Description:** Xây dựng module `agent_system.sdk.scanner` với dataclass `ProjectManifest` và lớp `CodebaseScanner`. Quét cấu trúc file manifests và configs (`package.json`, `pyproject.toml`, `setup.py`, `Cargo.toml`, `go.mod`, `Makefile`), tài liệu (`README.md`, `CONTRIBUTING.md`, `docs/**/*.md`), nhận diện ngôn ngữ, test framework, build commands, và trích xuất quy chuẩn coding conventions. Xử lý an toàn ngoại lệ (giới hạn đọc tối đa 50KB mỗi file, chống crash do file lỗi hoặc không có quyền truy cập).

**Acceptance criteria:**
- [x] `CodebaseScanner` phát hiện chính xác stack Python, Node/TS, Rust, Go, Makefile.
- [x] Phân tích và trích xuất các heading `# ` / `## ` và bullet rules từ tài liệu markdown.
- [x] Xử lý mượt mà khi repo rỗng hoặc file bị hỏng UTF-8.

**Verification:**
- [x] Tests pass: `PYTHONPATH=. python3 -m pytest tests/test_sdk_scanner.py -v`
- [x] Build succeeds: `python3 -m py_compile agent_system/sdk/scanner.py`
- [x] Manual check: Chạy scanner trên chính thư mục `Agent_system`, kiểm tra output `manifest.to_dict()` chứa đầy đủ thông tin Python, pytest, và các file docs.

**Dependencies:** None

**Files likely touched:**
- `agent_system/sdk/scanner.py`
- `tests/test_sdk_scanner.py`

**Estimated scope:** Small (2 files)

---

## Task 18: Dual-Tier Knowledge Ingestion Engine

**Description:** Xây dựng module `agent_system.sdk.ingestion` với lớp `KnowledgeIngester`. Nhận vào `ProjectManifest`, tổng hợp Tầng 1: file luật `.agent/rules.md` (kèm symlink `AGENTS.md`) và `agent_plugin.json`, đảm bảo trần ngân sách ngữ cảnh $\le 3072$ bytes qua `StructuralTruncator` và vượt qua `MarkdownRulesCritic`. Tổng hợp Tầng 2: chia nhỏ các file tài liệu theo đề mục H2 (`## `) và nạp vào `SemanticMemory` (SQLite Store) với metadata nguồn gốc.

**Acceptance criteria:**
- [x] File `.agent/rules.md` sinh ra có dung lượng $\le 3072$ bytes và đạt điểm tối đa trên `MarkdownRulesCritic`.
- [x] Toàn bộ các chunk tài liệu được index vào `SemanticMemory` và tìm kiếm được qua `search()`.
- [x] Quá trình nạp đảm bảo tính idempotent (không nhân bản trùng lặp nếu chạy lại).

**Verification:**
- [x] Tests pass: `PYTHONPATH=. python3 -m pytest tests/test_sdk_ingestion.py -v`
- [x] Build succeeds: `python3 -m py_compile agent_system/sdk/ingestion.py`
- [x] Manual check: Kiểm tra dung lượng `.agent/rules.md` sinh ra và query thử từ khóa trong `SemanticMemory`.

**Dependencies:** Task 17

**Files likely touched:**
- `agent_system/sdk/ingestion.py`
- `tests/test_sdk_ingestion.py`

**Estimated scope:** Small (2 files)

---

## Task 19: CLI Commands (`scan` & `init --auto`) in `agent_system/cli/main.py`

**Description:** Bổ sung lệnh CLI `scan` với tùy chọn `--root PATH` và `--json` (xuất JSON chuẩn hóa cho AI Agent CLI đọc trong phiên ngầm). Bổ sung tùy chọn `--auto` cho lệnh `agent-system init` để chạy quy trình phân tích và nạp tri thức 2 tầng tự động không tương tác (non-interactive mode), hỗ trợ cờ `--root` và `--rules-path`.

**Acceptance criteria:**
- [x] `python3 -m agent_system.cli.main scan --json` xuất ra JSON hợp lệ chứa cấu trúc của `ProjectManifest`.
- [x] `python3 -m agent_system.cli.main init --auto` hoàn thành việc scaffold và nạp memory tự động không yêu cầu nhập tay terminal prompt.
- [x] Tương thích hoàn toàn với UNIX pipe và xử lý mã thoát (exit code 0 / 1) chuẩn xác.

**Verification:**
- [x] Tests pass: `PYTHONPATH=. python3 -m pytest tests/test_cli_scan.py -v`
- [x] Build succeeds: `python3 -m py_compile agent_system/cli/main.py`
- [x] Manual check: `python3 -m agent_system.cli.main scan --json | python3 -m json.tool`

**Dependencies:** Tasks 17, 18

**Files likely touched:**
- `agent_system/cli/main.py`
- `agent_system/sdk/wizard.py`
- `tests/test_cli_scan.py`

**Estimated scope:** Medium (3 files)

---

## Task 20: Integration Verification, Critic Audit & Documentation Update

**Description:** Chạy kiểm thử tích hợp toàn diện trên một mock brownfield repository mô phỏng dự án thực tế; thẩm định toàn bộ code mới qua `CriticEngine` (100/100 điểm, không vi phạm AST hay phong cách code); cập nhật tài liệu `README.md`, `CLAUDE.md`, `CHANGELOG.md` và `docs/decisions/`.

**Acceptance criteria:**
- [x] 100% test cases (cũ + mới, $\ge 90$ tests) vượt qua thành công trên `pytest`.
- [x] Đạt điểm 100/100 trên toàn bộ file code mới qua `CriticEngine`.
- [x] Tài liệu `CHANGELOG.md` và `README.md` cập nhật hướng dẫn sử dụng lệnh `scan` và `init --auto`.

**Verification:**
- [x] Full suite pass: `PYTHONPATH=. python3 -m pytest tests/ -v`
- [x] Critic pass: `python3 -m agent_system.cli.main critic --file agent_system/sdk/scanner.py`

**Dependencies:** Tasks 17-19

**Files likely touched:**
- `tests/test_sdk_brownfield_e2e.py`
- `CHANGELOG.md`
- `README.md`

**Estimated scope:** Medium (3 files)

---

## Checkpoint: Brownfield Codebase Scanner & Ingestion Verified
- [x] CodebaseScanner trích xuất chính xác manifest, test commands, rules từ nhiều stack.
- [x] Tier 1 `.agent/rules.md` đạt $\le 3072$ bytes và 100/100 MarkdownRulesCritic.
- [x] Tier 2 Semantic Memory nạp thành công các doc chunks theo đề mục H2.
- [x] Lệnh `agent-system scan --json` phản hồi dưới 200ms.
- [x] 100% test suite pass toàn diện.

---

# Phase 8: Zero-Dependency Model Context Protocol (MCP) Server

## Task 21: JSON-RPC 2.0 Stdio Protocol Engine

**Description:** Xây dựng module `agent_system/mcp/server.py` với lớp `MCPServer`. Triển khai vòng lặp đọc/ghi JSON-RPC 2.0 qua `sys.stdin`/`sys.stdout`, hỗ trợ các phương thức chuẩn `initialize`, `notifications/initialized`, `ping`. Chuyển toàn bộ stderr/logs để giữ sạch luồng stdio.

**Acceptance criteria:**
- [x] Phản hồi đúng chuẩn JSON-RPC 2.0 cho `initialize` với version `"2024-11-05"` và server info.
- [x] Xử lý mượt mà `ping` và các notification không yêu cầu response.
- [x] Trả về mã lỗi JSON-RPC chuẩn (`-32700`, `-32601`, `-32602`) khi request sai định dạng.

**Verification:**
- [x] Tests pass: `PYTHONPATH=. python3 -m pytest tests/test_mcp_server.py -k test_mcp_handshake -v`
- [x] Build succeeds: `python3 -m py_compile agent_system/mcp/server.py`

**Dependencies:** None

**Files likely touched:**
- `agent_system/mcp/__init__.py`
- `agent_system/mcp/server.py`
- `tests/test_mcp_server.py`

**Estimated scope:** Small (3 files)

---

## Task 22: Cognitive Tools Dispatcher & Schema Declarations

**Description:** Xây dựng module `agent_system/mcp/tools.py` định nghĩa schema JSON Schema cho 8 công cụ: `agent_plan`, `agent_critic`, `agent_reflect`, `agent_memory_search`, `agent_memory_recipe_record`, `agent_memory_recipe_get`, `agent_scan`, `agent_init_auto`. Thực thi trực tiếp qua các engine in-memory.

**Acceptance criteria:**
- [x] `tools/list` trả về danh sách 8 công cụ với inputSchema chuẩn.
- [x] `tools/call` thực thi chính xác từng công cụ và trả về định dạng `{"content": [{"type": "text", "text": "..."}]}`.
- [x] Tự động bọc lỗi an toàn thành `isError: true` khi tham số không hợp lệ.

**Verification:**
- [x] Tests pass: `PYTHONPATH=. python3 -m pytest tests/test_mcp_server.py -k test_mcp_tools -v`
- [x] Build succeeds: `python3 -m py_compile agent_system/mcp/tools.py`

**Dependencies:** Task 21

**Files likely touched:**
- `agent_system/mcp/tools.py`
- `agent_system/mcp/server.py`
- `tests/test_mcp_server.py`

**Estimated scope:** Medium (3 files)

---

## Task 23: CLI Subcommand `mcp` & Stdio Pipe Integration Tests

**Description:** Tích hợp subcommand `mcp` vào `agent_system/cli/main.py`. Tạo bài test tích hợp `tests/test_mcp_e2e.py` dùng `subprocess.Popen` giao tiếp song công (bidirectional stdio) để kiểm tra tương thích thực tế như một MCP Client.

**Acceptance criteria:**
- [x] Lệnh `agent-system mcp` khởi động server và lắng nghe qua stdin.
- [x] Test E2E mô phỏng handshake client-server thành công trọn vẹn qua tiến trình subprocess.

**Verification:**
- [x] Tests pass: `PYTHONPATH=. python3 -m pytest tests/test_mcp_e2e.py -v`
- [x] Build succeeds: `python3 -m py_compile agent_system/cli/main.py`

**Dependencies:** Tasks 21, 22

**Files likely touched:**
- `agent_system/cli/main.py`
- `tests/test_mcp_e2e.py`

**Estimated scope:** Small (2 files)

---

## Task 24: Critic Audit, Documentation & Release Verification

**Description:** Thẩm định 100/100 điểm qua `CriticEngine` cho toàn bộ code mới; cập nhật `README.md`, `CLAUDE.md`, `CHANGELOG.md` với hướng dẫn cấu hình MCP cho Claude Desktop / Cursor. Đảm bảo toàn bộ test suite pass 100%.

**Acceptance criteria:**
- [x] 100% test cases ($\ge 100$ tests) pass trên `pytest`.
- [x] Đạt điểm 100/100 trên toàn bộ file code mới qua `CriticEngine`.
- [x] `README.md` có hướng dẫn cấu hình JSON cho Claude Desktop và Cursor.

**Verification:**
- [x] Full suite pass: `PYTHONPATH=. python3 -m pytest tests/ -v`
- [x] Critic pass: `python3 -m agent_system.cli.main critic --file agent_system/mcp/server.py`

**Dependencies:** Tasks 21-23

**Files likely touched:**
- `README.md`
- `CHANGELOG.md`

**Estimated scope:** Small (2 files)

---

## Checkpoint: MCP Server Protocol Verified
- [x] Toàn bộ 4 task MCP hoàn thành trọn vẹn.
- [x] Tương thích 100% chuẩn MCP 2024-11-05.
- [x] Zero runtime dependencies ngoài standard library.
- [x] 100% test suite pass toàn diện.

