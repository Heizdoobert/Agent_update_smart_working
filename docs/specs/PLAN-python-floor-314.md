# PLAN: python-floor-314 — 3.9 → 3.14 + apply 397 pyupgrade

> Spec: `SPEC-python-floor-314.md` (4 OQ chốt: floor 3.14 / CI ["3.14"] / UP015 xem tay / giữ future annotations)
> Trạng thái: 🟡 CHỜ "GO" · Ước lượng: 25–35 phút, 1–2 commits

## Execution Steps (thứ tự bắt buộc)

### Step 1 — Config: `requires-python` + ruff target
**File:** `pyproject.toml`
- `requires-python = ">=3.9"` → `">=3.14"`
- `[tool.ruff]` `target-version = "py39"` → `"py314"`
**Verify:** `.venv/bin/python -c "import tomllib; d=tomllib.load(open('pyproject.toml','rb')); print(d['project']['requires-python'], d['tool']['ruff']['target-version'])"`
→ `>=3.14 py314`

### Step 2 — Xem tay 1 lỗi UP015 TRƯỚC khi auto-fix (tránh ruff đổi behavior)
```bash
uvx ruff check agent_system/ tests/ --select UP015 --target-version py314
```
- Nếu `zip(a, b)` an-tàng thêm `strict=True` (2 sequence luôn cùng độ dài) → sửa tay.
- Nếu `strict=True` có thể đổi behavior (degree khác nhau) → giữ + `# noqa: UP015` 1 dòng có lý do.
**Verify:** `ruff --select UP015` → 0 hoặc 1 noqa có lý do.

### Step 3 — Auto-fix 396 lỗi UP
```bash
uvx ruff check agent_system/ tests/ --select UP --target-version py314 --fix
```
**Verify:** `ruff --select UP` → 0 lỗi. **Ngay sau đó chạy test** (Step 7) — nếu đỏ là UP fix đổi behavior, revert step này.

### Step 4 — Ruff recheck toàn bộ (E,F,W,I + UP)
```bash
uvx ruff check agent_system/ tests/
```
**Verify:** All checks passed. Nếu I001 (import order) do xóa `typing` import → `ruff --fix` thêm.

### Step 5 — CI: matrix → ["3.14"]
**File:** `.github/workflows/ci.yml`
- `lint` + `mypy` job: `python-version: "3.11"` → `"3.14"`
- `test` matrix: `python: ["3.9", "3.12"]` → `python: ["3.14"]`
**Verify:** YAML parse + 3 job đều 3.14.

### Step 6 — Test unit MỚI: `tests/test_python_floor.py`
```python
"""Guard: codebase requires Python >= 3.14.

Two assertions:
1. sys.version_info — fail sớm nếu ai chạy bằng Python < 3.14.
2. Runtime `X | Y` union (PEP 604) — chứng minh codebase đang trên
   floor cho phép syntax này (3.9/3.10 không có).
"""
import sys

def test_python_floor_is_at_least_3_14():
    assert sys.version_info >= (3, 14), (
        f"agent-system requires Python >= 3.14, running {sys.version_info.major}.{sys.version_info.minor}"
    )

def test_pep604_union_runtime_supported():
    # PEP 604 (X | Y at runtime) — 3.10+; trên 3.14 chắc chắn OK.
    x: int | str = 5
    assert isinstance(x, int)
    y: None | float = None
    assert y is None
```
**Verify:** test pass trên 3.14.

### Step 7 — VERIFY TOÀN BỘ (dừng nếu đỏ)
```bash
uv run --no-project --python 3.14 --with pytest python -m pytest tests/ -q
#   mong: 165 passed (164 cũ + 1 test_python_floor... thực ra +2 tests)
uvx mypy agent_system/ --ignore-missing-imports --no-strict-optional --follow-imports=silent
#   mong: Success (annotation py314 vẫn hợp lệ với mypy)
uvx ruff check agent_system/ tests/
#   mong: All checks passed
```
**Lưu ý:** suite cũ 164 + 2 test mới = **166**. Chỉnh expectation: `166 passed`.

### Step 8 — `docs/lint-baseline.md`: đóng pyupgrade
Thêm section: "Pyupgrade — ĐÃ XỬ LÝ (floor 3.14)": bảng 397 lỗi → 0 + commit SHA + note "requires-python >=3.14".

### Step 9 — `features.json` F-009 + COMMIT
```python
# F-009: python-floor-314, status done sau Step 7 xanh + commit SHA
```
```bash
git add -A
git commit -m "python-floor-314 (F-009): requires-python >=3.14, ruff target py314, apply 397 pyupgrade (UP), CI matrix 3.14, +test_python_floor guard"
```
Flip F-009 → done + SHA, amend.

## Rollback
- Step 3 (UP auto-fix) đỏ → `git checkout -- agent_system/ tests/` revert, debug từng file.
- Bước fail 3 lần → dừng + báo anh + evidence, không tiếp tục.

## Definition of Done
1. `pyproject.toml`: `>=3.14` + ruff `py314`
2. `ruff check` → All checks passed (0 UP)
3. `pytest tests/ -q` trên 3.14 → **166 passed**
4. `mypy` → 0 errors
5. `ci.yml` matrix `["3.14"]`, 3 job 3.14
6. `features.json` F-009 done + SHA
7. `docs/lint-baseline.md` pyupgrade đóng
8. 1–2 commits, không push

## Open Items (không làm module này)
- Pilot `--strict` mypy → follow-up
- Push remote → chờ anh

## Risks
| Rủi ro | Xác suất | Mitigation |
|---|---|---|
| UP auto-fix đổi behavior (UP015 `strict`) | Thấp | Step 2 xem tay trước; Step 7 test bắt |
| Xóa `typing` import → I001 | Trung bình | Step 4 ruff --fix |
| mypy không hiểu annotation py314 | Rất thấp | mypy flag baseline đã ignore; Step 7 verify |
| AI chạy repo bằng 3.9 thật → vỡ | Thấp (anh dev 3.14) | test_python_floor fail RÕ "requires 3.14" |
