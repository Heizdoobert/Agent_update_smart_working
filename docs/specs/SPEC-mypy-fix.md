# Spec: mypy-fix — Dọn 9 lỗi type + đưa mypy thành gate (Module 8)

> Trạng thái: 🟡 CHỜ DUYỆT · Map: nối tiếp `ci-quality` (done, baseline 9 lỗi) · Phụ thuộc: `metrics-kpi` (done — nguồn 2 lỗi `attr-defined`)
> Nguồn chuẩn: THIẾT Mục 1639 (Trust Pyramid — Tầng 1: "Codebase/static" là tầng tin cậy CAO NHẤT), SPEC-ci-quality Q2 (mypy non-strict baseline — module này biến baseline thành 0)

## Objective
Đem mypy từ "ghi nhận baseline 9 lỗi" (ci-quality) xuống **0 lỗi** bằng sửa annotation tối thiểu (không đổi runtime), rồi **thăng mypy thành CI gate** để khóa lại — đúng Tầng 1 Trust Pyramid của THIẾT: sai type phải bị chặn TRƯỚC khi chạy, không phải phát hiện bằng test.

## Evidence — 9 lỗi thật (đo 2026-11-20, `mypy --ignore-missing-imports --no-strict-optional`)

| # | File:line | Mã | Bản chất | Phân loại |
|---|---|---|---|---|
| M1 | `core/truncator.py:106` | assignment | dict gán vào var type `list` (narrowing sai trong nhánh union) | 🔴 **latent bug thật** — sửa annotation/narrowing đúng |
| M2 | `mcp/tools.py:311` | assignment | `AStarPlanner` gán vào var `MCTSPlanner` | 🟡 union — annotate `planner: AStarPlanner \| MCTSPlanner` |
| M3 | `cli/main.py:140` | assignment | cùng M2 (copy-paste site) | 🟡 union — sửa cùng M2 |
| M4-M7 | `mcp/tools.py:348-356` (4 lỗi) | arg-type | list annotate hẹp (`PythonAstCritic`) nhưng append critic khác | 🟢 **polymorphism đúng** — annotate `List[CriticProtocol]` (đúng intent, không giấu gì) |
| M8-M9 | `cli/main.py:656,662` | attr-defined | union `Metric \| dict` trong `cmd_metrics` — `"object" has no attribute "to_dict"` | 🟡 **do code metrics-kpi** — chuẩn hóa dashboard luôn trả `Metric` (bỏ dict ad-hoc), hoặc `cast` đúng chỗ |

**Tóm:** 1 latent bug thật (M1), 5 union/annotation hẹp (M2-M7, M8-M9), 0 lỗi do thiếu import. KHÔNG có lỗi nào cần đổi logic.

## Scope — IN

| # | Việc | Bằng chứng |
|---|---|---|
| Y1 | Fix M1 (`truncator.py:106`) — narrowing/annotation đúng, KHÔNG bỏ type bằng `Any` | `mypy` không còn lỗi dòng đó; test truncator vẫn xanh |
| Y2 | Fix M2+M3 (2 site union planner) — annotate union type | 2 lỗi assignment biến mất |
| Y3 | Fix M4-M7 — `critics: List[CriticProtocol]` (import `CriticProtocol`) | 4 lỗi arg-type biến mất |
| Y4 | Fix M8-M9 — `cmd_metrics` dashboard: mọi entry là `Metric` (thay dict ad-hoc `flow_retry_ceiling` bằng `Metric(...)`); output JSON dùng `to_dict()` thống nhất | 2 lỗi attr-defined biến mất; `metrics --json` output GIỮ NGUYÊN 8 key |
| Y5 | Thêm job `mypy` vào `.github/workflows/ci.yml` (chạy sau `lint`, trước `test`), dùng chính config non-strict hiện tại | `ci.yml` có 3 job: lint → mypy → test |
| Y6 | Cập nhật `docs/lint-baseline.md`: mypy 9 → **0**, ghi loại bỏ baseline + ngày + commit | baseline file phản ánh thật |
| Y7 | Cập nhật `features.json`: thêm F-008 (mypy-fix) với acceptance + verification | features.json consistent |

## Scope — OUT
- **KHÔNG bật `--strict`** (sẽ bung hàng trăm lỗi `disallow-untyped-def` — đúng OUT của SPEC-ci-quality, giữ nguyên)
- **KHÔNG nâng `requires-python`** (việc của pyupgrade spec — riêng)
- **KHÔNG sửa pyupgrade 357 lỗi** (UP rules — cần drop py3.9, spec khác)
- **KHÔNG refactor logic** — chỉ annotation/type; mỗi fix ≤ 5 dòng
- **KHÔNG push** (đợi anh quyết riêng)

## Commands
```bash
cd /mnt/second_drive/Agent_system
uvx mypy agent_system/ --ignore-missing-imports --no-strict-optional --follow-imports=silent   # trước: 9, sau: 0
uv run --no-project --python 3.11 --with pytest python -m pytest tests/ -q                        # 150 passed
uvx ruff check agent_system/ tests/                                                                 # All checks passed
.venv/bin/python -m agent_system.cli.main metrics --json | .venv/bin/python -c "import json,sys; d=json.load(sys.stdin); assert len(d)==8 and {m['name'] for m in d} >= {'flow_retry_ceiling','context_usage_pct'}; print('metrics contract OK')"
```

## Testing Strategy
| Mức | Cách | Acceptance |
|---|---|---|
| Type | `mypy` (cùng flags baseline) | **0 errors** (trước: 9) |
| Regression | pytest toàn suite | **150 passed / 0 failed** (không test nào đổi) |
| Contract | `metrics --json` parse + 8 key + `flow_retry_ceiling` có mặt | output JSON GIỮ NGUYÊN cấu trúc (M8-M9 fix phải invisible với consumer) |
| Lint | `ruff check` | All checks passed (annotation mới không vi phạm E,F,W,I) |
| CI-local | 3 lệnh trong `ci.yml` job mới chạy tay local | 3/3 xanh trước khi cam kết |

## Boundaries
- **Always:** mỗi fix mypy = 1 patch nhỏ + chạy test ngay; giữ cùng flags mypy như baseline (đổi flags = đổi bài toán); fix M8-M9 phải giữ output JSON `metrics --json` byte-compatible về key
- **Ask first:** nếu muốn fix M1 bằng đổi logic (không chỉ type) → báo trước, cho xem diff; thêm mypy `--strict` cho file pilot; đổi CI job order
- **Never:** `# type: ignore` để né lỗi (tuyệt đối — 9 lỗi này đều fix được đúng cách); `Any` để xóa type; bỏ/làm yếu test để xanh; push

## Success Criteria
1. `mypy agent_system/ --ignore-missing-imports --no-strict-optional --follow-imports=silent` → **Found 0 errors**
2. `pytest tests/ -q` → **150 passed / 0 failed**
3. `ruff check` → All checks passed
4. `metrics --json` → 8 key, cấu trúc không đổi (consumer không vỡ)
5. `ci.yml` có job `mypy` (lint → mypy → test)
6. `docs/lint-baseline.md` cập nhật: mypy = 0, baseline đóng
7. `features.json` F-008 = done kèm commit SHA + evidence
8. Commit riêng cho module này (1 commit hoặc ≤2 commit nhóm fix)

## Open Questions — ĐÃ CHỐT (2026-11-20, Huy)
1. Mypy gate trong CI: **BLOCKING** (mypy đỏ = chặn merge). Chi phí = 0 vì mypy xanh; repo nội bộ 1 người commit.
2. M1 `truncator.py:106`: **KHÔNG phải latent bug** (đã đọc code thật: 2 branch list/dict tách biệt, list branch `return` trước — chỉ là naming collision của `candidate`). Fix = **rename biến** (`candidate_dict`), 0 đổi logic, 0 test mới. (Quy tắc chung vẫn giữ: nếu lỗi type lộ logic sai thật → được sửa logic + test mới, phải báo trước.)
3. Pilot `--strict`: **KHÔNG** trong module này — làm follow-up sau 1–2 tuần gate chạy ổn. Ghi vào `lint-baseline.md`.
