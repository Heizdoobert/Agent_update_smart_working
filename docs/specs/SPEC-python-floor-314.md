# Spec: python-floor-314 — Nâng `requires-python` 3.9 → 3.14 + apply pyupgrade

> Trạng thái: 🟡 CHỜ DUYỆT · Map: nối tiếp `mypy-fix` (done) · Phụ thuộc: `mypy-fix` (done, mypy gate chạy)
> Nguồn: anh Huy duyệt (2026-11-20) — "yes, make plan with test unit to test all"
> Bối cảnh: dev venv đang chạy 3.14.4 thật; CI matrix 3.9+3.12 không cần giữ 3.9 nữa

## Objective
Nâng `requires-python` từ `>=3.9` lên `>=3.14` để (a) codebase được phép dùng syntax native 3.10+ (`X | Y`), (b) unblock **397 lỗi pyupgrade** (ruff `UP` rules — đang bị chặn bởi floor 3.9), (c) CI chạy đúng Python anh đang dev. Đây là **spec riêng** — không nằm trong `mypy-fix`.

## Evidence — 397 lỗi pyupgrade (đo 2026-11-20, `ruff --select UP --target-version py314`)

| Mã | Count | Ý nghĩa | Auto-fixable? |
|---|---|---|---|
| UP006 | 215 | `List[X]` → `list[X]` | ✅ |
| UP045 | 104 | `Dict[...]` → `dict[...]` | ✅ |
| UP035 | 63 | `Optional[X]` → `X \| None` | ✅ |
| UP007 | 11 | `Union[X, Y]` → `X \| Y` | ✅ |
| UP043 | 2 | Unnecessary `list()` call | ✅ |
| UP042 | 1 | Unnecessary `str()` call | ✅ |
| UP015 | 1 | `zip()` without `strict=` | ⚠️ (ruff gợi ý, cần xem) |

**Tổng: 397 lỗi, 396 auto-fix, 1 cần xem tay (UP015).**

## Scope — IN

| # | Việc | Bằng chứng |
|---|---|---|
| P1 | `pyproject.toml`: `requires-python = ">=3.14"` | `pyproject.toml` parse OK |
| P2 | `pyproject.toml`: ruff `target-version = "py314"` (thay `py39`) | ruff hiểu target |
| P3 | `ruff check agent_system/ tests/ --select UP --fix` — áp 396 lỗi auto-fix | `ruff --select UP` → 0 lỗi UP |
| P4 | Xem tay 1 lỗi UP015 (`zip` strict) — fix hoặc giữ với noqa có lý do | ruff clean |
| P5 | `.github/workflows/ci.yml`: matrix Python → `["3.14"]` (bỏ 3.9, 3.12); job lint + mypy chạy 3.11 → 3.14 | YAML valid |
| P6 | **Test unit mới**: `tests/test_python_floor.py` — assert `sys.version_info >= (3, 14)` + smoke test `X \| Y` runtime (chứng minh codebase đang chạy trên đúng floor) | test pass trên 3.14, fail nếu ai chạy 3.9 |
| P7 | Re-verify: 164 tests + mypy 0 + ruff clean (trên 3.14) | 3 lệnh xanh |
| P8 | `features.json` F-009 (python-floor-314) = done | JSON valid |
| P9 | `docs/lint-baseline.md`: cập nhật pyupgrade section (397 → 0) + note "floor 3.14" | baseline phản ánh |

## Scope — OUT
- **KHÔNG đổi API / CLI flags / file paths** (chỉ type syntax)
- **KHÔNG bỏ `from __future__ import annotations`** (harmless, tránh churn; ruff UP không bắt lỗi này)
- **KHÔNG sửa logic** (chỉ syntax modernization)
- **KHÔNG push** (chờ anh quyết)
- **KHÔNG nâng lên 3.15+** (3.14 là stable hiện tại; 3.15 chưa release)

## Commands
```bash
cd /mnt/second_drive/Agent_system
# trước: floor 3.9, 397 UP errors
uvx ruff check agent_system/ tests/ --select UP --target-version py314 2>&1 | grep -c UP
# sau P3: 0 UP errors
uvx ruff check agent_system/ tests/ --select UP --target-version py314
# verify
uv run --no-project --python 3.14 --with pytest python -m pytest tests/ -q
uvx mypy agent_system/ --ignore-missing-imports --no-strict-optional --follow-imports=silent
uvx ruff check agent_system/ tests/
```

## Testing Strategy
| Mức | Cách | Acceptance |
|---|---|---|
| Floor | `tests/test_python_floor.py` mới | `sys.version_info >= (3, 14)` + `int \| str` runtime OK |
| Regression | pytest toàn suite (164 + 1 mới = 165) trên **3.14** | 165 passed |
| Regression | pytest toàn suite trên **3.12** (tuỳ chọn, nếu uv có) | 165 passed (chứng minh code không lock 3.14-only) |
| Type | mypy (baseline flags) | 0 errors |
| Lint | ruff check (E,F,W,I + UP) | All checks passed |
| Contract | `metrics --json` 8 key, `plan astar/mcts`, `critic` | không đổi |

## Boundaries
- **Always:** sau `ruff --fix` UP → chạy test ngay; mỗi commit ≤ 2 (1 config + 1 code); UP015 xem tay
- **Ask first:** nếu ruff UP fix đổi runtime behavior (UP015 `strict=True` có thể thay đổi `zip` length behavior) → báo trước + test
- **Never:** sửa logic để "hỗ trợ" UP fix; bỏ test để xanh; push; dùng `# noqa` hàng loạt

## Success Criteria
1. `pyproject.toml`: `requires-python = ">=3.14"` + ruff `target-version = "py314"`
2. `ruff check agent_system/ tests/` → **All checks passed** (gồm 0 UP errors)
3. `pytest tests/ -q` trên 3.14 → **165 passed** (164 cũ + 1 `test_python_floor`)
4. `mypy` (baseline flags) → 0 errors
5. `ci.yml` matrix = `["3.14"]`, lint+mypy+test đều chạy 3.14
6. `features.json` F-009 = done + commit SHA
7. `docs/lint-baseline.md`: pyupgrade section = "397 → 0, floor 3.14"
8. 1–2 commits, không push

## Open Questions — ĐÃ CHỐT (2026-11-20, Huy)
1. Floor = **3.14** (chốt "yes")
2. CI matrix = **["3.14"]** (1 Python, đơn giản — dev + CI cùng 1 bản)
3. UP015 (`zip` strict) = **xem tay**, fix nếu an-tàng, giữ nếu đổi behavior
4. `from __future__ import annotations` = **giữ** (không xóa, tránh churn)
