# PLAN: mypy-fix — 9 lỗi → 0 + CI gate blocking

> Spec: `SPEC-mypy-fix.md` (đã duyệt, 3 OQ chốt: blocking / rename / không pilot)
> Trạng thái: 🟡 CHỜ "GO" để thực thi · Ước lượng: 30–45 phút, 1–2 commits

## Execution Steps (thứ tự bắt buộc)

### Step 1 — M1: rename biến `candidate` trong dict branch của `truncate_json`
**File:** `agent_system/core/truncator.py` · **Dòng:** 101–124 (dict branch)
**Thay đổi:** `candidate` → `candidate_dict` (tất cả chỗ dùng trong dict branch).
**KHÔNG:** đụng list branch (line 84–99) — branch đó tự洽, không đổi gì.
**Vì sao:** naming collision khiến mypy narrowing nhầm; rename = mypy hiểu đúng, code byte-identical về hành vi.
**Verify:** `mypy` không còn báo `truncator.py:106`.

### Step 2 — M2+M3: annotate union cho `planner`
**File 1:** `agent_system/mcp/tools.py` · dòng ~308 (trước `if method == "mcts":`)
**File 2:** `agent_system/cli/main.py` · dòng ~137 (trước `if args.method == "mcts":`)
**Thay đổi:** thêm 1 dòng annotation ngay trước if:
```python
planner: AStarPlanner | MCTSPlanner
```
Cả 2 file đã import `AStarPlanner` + `MCTSPlanner` (đã verify ở site) — không cần thêm import.
**Vì sao:** mypy narrow theo assignment đầu tiên (MCTS) rồi gặp AStar → union type là intent thật (cả 2 cùng `.plan()`).
**Verify:** mypy không còn 2 lỗi `assignment`.

### Step 3 — M4–M7: annotate `critics: List[CriticProtocol]`
**File:** `agent_system/mcp/tools.py` · dòng 344 (`critics = []` → `critics: List[CriticProtocol] = []`)
**Import cần thêm:** `from agent_system.core.contracts import CriticProtocol` (check imports đầu file trước — có thể đã có).
**Vì sao:** list chứa 4 loại critic khác nhau (polymorphism đúng) — annotation hẹp `PythonAstCritic` là bug annotation.
**Verify:** mypy không còn 4 lỗi `arg-type`.

### Step 4 — M8+M9: chuẩn hóa dashboard trong `cmd_metrics`
**File:** `agent_system/cli/main.py` · `cmd_metrics` (block dash)
**Thay đổi:**
- Bỏ entry dict ad-hoc `{"name": "flow_retry_ceiling", ...}` → thay bằng `Metric(name="flow_retry_ceiling", value=float(FLOW_RETRY_CEILING), level="safe", action=...)`
- JSON output: mọi entry đã là `Metric` → `[d.to_dict() for d in dash]` (không cần union check)
- Text table: `d.to_dict()` thống nhất (bỏ `isinstance(d, dict)` check)
**KHÔNG đổi:** 8 key name, giá trị, level, action text — consumer (`tests/test_metrics.py`, `KPI_DASHBOARD.md`) phải không thấy khác biệt.
**Verify:** `metrics --json` vẫn 8 key + `metrics` text không đổi về nội dung + mypy không còn 2 lỗi `attr-defined`.

### Step 5 — CI: thêm job `mypy` (blocking)
**File:** `.github/workflows/ci.yml`
**Thay đổi:** chèn job mới giữa `lint` và `test`:
```yaml
  mypy:
    needs: lint
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: pip install mypy
      - name: Mypy gate (non-strict baseline flags)
        run: mypy agent_system/ --ignore-missing-imports --no-strict-optional --follow-imports=silent
```
`test` job: thêm `needs: [lint, mypy]`.
**Blocking:** mặc định CI = red job blocks merge (không cần flag thêm).

### Step 6 — `docs/lint-baseline.md`: đóng baseline mypy
**Thêm section:** "Mypy — ĐÃ ĐÓNG (2026-11-20, module mypy-fix)" + bảng 9 lỗi → 0 + commit SHA.
**Thêm note:** pilot `--strict` = follow-up (sau 1–2 tuần gate chạy ổn).

### Step 7 — `features.json`: thêm F-008
**Nội dung:** id F-008, name "mypy-fix — 9→0 type errors + blocking CI gate", status "in_progress" (flip "done" sau khi Step 8 xong + commit SHA).
**Acceptance:** 8 tiêu chí = Success Criteria của spec.
**Verification:** `mypy ... ; pytest tests/ -q ; ruff check ...`.

### Step 8 — VERIFY TOÀN BỘ (không skip)
Chạy **theo thứ tự**, dừng nếu bất kỳ bước nào đỏ:
```bash
uvx mypy agent_system/ --ignore-missing-imports --no-strict-optional --follow-imports=silent
#   mong đợi: "Found 0 errors"
uv run --no-project --python 3.11 --with pytest python -m pytest tests/ -q
#   mong đợi: "150 passed"
uvx ruff check agent_system/ tests/
#   mong đợi: "All checks passed!"
.venv/bin/python -m agent_system.cli.main metrics --json | .venv/bin/python -c "
import json, sys
d = json.load(sys.stdin)
assert len(d) == 8, f'expected 8, got {len(d)}'
names = {x['name'] for x in d}
assert 'flow_retry_ceiling' in names and 'context_usage_pct' in names
print('metrics contract OK — 8 keys intact')"
```

### Step 9 — COMMIT
```bash
git add -A
git commit -m "mypy-fix: 9 type errors -> 0 (rename truncator, union planner, CriticProtocol list, metrics Metric), add blocking mypy CI gate, close baseline, add F-008"
```
Flip F-008 → done + ghi commit SHA vào `features.json` + commit amend (hoặc commit 2 nhỏ).

## Rollback Plan
Mỗi step là 1 patch nhỏ, độc lập. Nếu step nào đỏ:
- Step 1–4 (code fixes): `git checkout -- <file>` để revert step đó, debug riêng.
- Step 5 (CI): revert job mới, giữ 9→0 fix trong code.
- Bước nào fail 3 lần → dừng, báo anh + evidence, KHÔNG tiếp tục.

## Definition of Done (từ spec, nhắc lại)
1. `mypy` → **Found 0 errors**
2. `pytest tests/ -q` → **150 passed / 0 failed**
3. `ruff check` → All checks passed
4. `metrics --json` → 8 key nguyên vẹn (flow_retry_ceiling + context_usage_pct có mặt)
5. `ci.yml` có 3 job: lint → mypy → test (mypy blocking)
6. `docs/lint-baseline.md` cập nhật (mypy = 0, baseline đóng, note pilot follow-up)
7. `features.json` F-008 = done + commit SHA + evidence
8. 1 commit (hoặc ≤2) cho module này, không push

## Open Items (không làm trong module này)
- Pilot `--strict` cho `metrics.py` + `flow.py` → follow-up sau 1–2 tuần
- Pyupgrade 357 lỗi (UP rules) → spec riêng, cần drop `requires-python` 3.9 → 3.10
- Push remote → chờ anh quyết

## Risks
| Rủi ro | Xác suất | Mitigation |
|---|---|---|
| Rename `candidate` đụng nhầm chỗ ngoài dict branch | Thấp | grep `candidate` trước khi đổi; chỉ rename trong dict branch (line 101–124) |
| Annotation union `AStarPlanner \| MCTSPlanner` vi phạm Python 3.9 syntax | TRUNG BÌNH | 3.9 không support `X | Y` runtime — nhưng annotation **không evaluate** khi có `from __future__ import annotations` (cả 2 file đã có) → an toàn. Nếu không, dùng `Union[AStarPlanner, MCTSPlanner]` |
| Đổi dashboard sang `Metric` thay dict → output JSON khác | Thấp | Step 8 verify 8 key + names; nếu khác → rollback step 4 |
| CI job mypy fail trên GitHub (version mypy lệch) | Thấp | CI dùng `pip install mypy` (latest) — flags non-strict nên ổn định; nếu lệch, pin version trong CI |
