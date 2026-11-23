# Lint & Type Baseline (module `ci-quality`, 2026-11-20)

## Ruff (CI GATE — `ruff check` phải 0 errors)

- Ruleset: **E, F, W, I** (safe cho `requires-python>=3.9`)
- `line-length = 140`
- Per-file-ignore `E501` cho 4 file chứa long natural-language strings (MCP tool schemas, wizard prose) + `tests/*`
- **Trạng thái: ✅ All checks passed**

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

## Pyupgrade (UP006/UP035/UP045 = 357 lỗi)

Không chạy vì cần **đổi `requires-python` từ 3.9 → 3.10+** (đổ bớt floor). Để riêng làm follow-up khi anh sẵn sàng nâng Python tối thiểu.
