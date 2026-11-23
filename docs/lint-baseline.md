# Lint & Type Baseline (module `ci-quality` + `mypy-fix` + `python-floor-314`, 2026-11-20)

## Ruff (CI GATE — `ruff check` phải 0 errors)

- Ruleset: **E, F, W, I, UP** (UP bật sau khi nâng floor `requires-python >= 3.14`, F-009)
- `target-version = "py314"`, `line-length = 140`
- Per-file-ignore `E501` cho 4 file chứa long natural-language strings (MCP tool schemas, wizard prose) + `tests/*`
- **Trạng thái: ✅ All checks passed (0 UP errors)**

Đã fix trong module này:
- 146 lỗi auto-fix an-tàng (unused imports, isort, whitespace)
- **F821 `CriticReport`** — `agent_system/sdk/contracts.py:89` dùng annotation `CriticReport` không import (latent bug, chỉ sống nhờ `from __future__ import annotations`) → đã import
- **F841 `ss_list`** — `agent_system/cli/main.py:566` gán biến không dùng (F841 false-positive cho `add_parser` side-effect) → bỏ gán

## Mypy — ĐÃ ĐÓNG BASELINE (2026-11-20, module `mypy-fix`)

`mypy agent_system/ --ignore-missing-imports --no-strict-optional --follow-imports=silent` → **Success: no issues found in 46 source files**

| Lỗi cũ (9) | File | Fix |
|---|---|---|
| M1 `truncator.py:106` assignment | `core/truncator.py` | rename `candidate` → `candidate_dict` (naming collision, không phải bug) |
| M2 `mcp/tools.py:311` assignment | `mcp/tools.py` | annotate `planner: AStarPlanner \| MCTSPlanner` |
| M3 `cli/main.py:140` assignment | `cli/main.py` | annotate union (site 2) |
| M4-M7 `mcp/tools.py:348-356` arg-type (4) | `mcp/tools.py` | `critics: List[CriticProtocol] = []` (import `CriticProtocol`) |
| M8-M9 `cli/main.py:656/662` attr-defined | `cli/main.py` | dashboard `cmd_metrics` chuẩn hóa mọi entry thành `Metric` (bỏ dict ad-hoc) |

**CI gate:** `.github/workflows/ci.yml` có job `mypy` (blocking, giữa `lint` → `test`). Mypy đỏ = chặn merge.

**Follow-up (KHÔNG làm trong module này, chốt 2026-11-20):**
- Pilot `--strict` cho `metrics.py` + `flow.py` — làm sau 1–2 tuần gate chạy ổn.
- Bật `--strict` toàn cục — goal dài hạn.

## Mypy (baseline cũ — đã xóa, giữ lịch sử)

`mypy agent_system/ --ignore-missing-imports --no-strict-optional` → **7 errors in 3 files**:

| File:line | Lỗi | Loại |
|---|---|---|
| `core/truncator.py:106` | `dict` gán vào var type `list` | **latent bug** (union) |
| `mcp/tools.py:311` | `AStarPlanner` gán vào var type `MCTSPlanner` | union |
| `mcp/tools.py:348-356` | list `PythonAstCritic` vs `CriticProtocol` (4 lỗi) | polymorphism |
| `cli/main.py:127` | `AStarPlanner` vs `MCTSPlanner` | union |

**Quyết định:** KHÔNG fix 7 lỗi này trong module `ci-quality` (chúng cần đổi type annotation + có thể đổi runtime behavior — nằm ngoài "gate tin cậy"). Ghi lại đây để module sau / anh quyết. 4/7 là **polymorphism đúng cách** (dùng protocol), 3/7 cần xem union type.

## Pyupgrade — ĐÃ XỬ LÝ (2026-11-20, module `python-floor-314` / F-009)

Nâng `requires-python` 3.9 → **3.14** + ruff `target-version` py39 → py314 + bật rule `UP` vào gate. **397 lỗi UP → 0:**

| Mã | Count | Fix |
|---|---|---|
| UP006 `List[X]`→`list[X]` | 215 | ruff auto-fix (usage) + F401 (xóa import typing) |
| UP045 `Dict[X]`→`dict[X]` | 104 | ruff auto-fix + F401 |
| UP035 `typing.X` deprecated | 63 | usage→lowercase + F401 xóa import (30 file) |
| UP007 `Union`→`\|` | 11 | ruff auto-fix |
| UP043 `list()` unnecessary | 2 | ruff auto-fix |
| UP042 `(str, Enum)`→`StrEnum` | 1 | `CriticStatus` → `enum.StrEnum` (chỉ dùng `.value`/`==`, an-tàng) |
| UP015 `open` mode `"r"` | 1 | ruff auto-fix (xóa mode, mặc định "r") |

**Test guard mới:** `tests/test_python_floor.py` (3 tests) — `sys.version_info >= (3,14)` + PEP 604 runtime + built-in generics. Suite **167 passed trên 3.14**.

**CI:** matrix test 3.9+3.12 → **3.14** (đúng bản dev); lint + mypy job 3.11 → 3.14.
