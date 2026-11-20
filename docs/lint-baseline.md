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

## Mypy (ghi nhận, KHÔNG là CI gate ở bước này)

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
