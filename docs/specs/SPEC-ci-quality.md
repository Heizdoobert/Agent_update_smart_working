# Spec: ci-quality — Hàng rào tĩnh + CI xanh 3 OS (Module 3/7)

> Trạng thái: 🟡 CHỜ DUYỆT · Map: `CAPABILITY_MAP.md` (đã duyệt) · Phụ thuộc: `cleanup` (xong)
> Nguồn chuẩn: THIẾT Bước 1 (§18.2: strict type + lint có hướng dẫn sửa), Mục 2 Tầng 1, §22.2 (CI gate)

## Objective
Xây **Tầng 1 Trust Pyramid** thật: lint + type-check tự động chặn lựa chọn sai ở compile-time; CI xanh trên ubuntu/macos/windows × Python 3.9/3.12. Đây là **gate tin cậy** — mọi module sau chỉ chạy trên nền CI xanh.

## Scope — IN

| # | Việc | Bằng chứng gap |
|---|---|---|
| Q1 | Thêm `ruff` config (lint + format rules, target py311) — **phase 1: fix all errors hiện có** | không có `ruff.toml`/`.ruff.toml`; CI chỉ chạy pytest |
| Q2 | Thêm `mypy` — **phase 2: non-strict baseline** (đếm lỗi, freeze bằng `# mypy: disable` chỉ khi cần), strict toàn cục = goal dài hạn, KHÔNG bắt buộc module này | không có mypy.ini; `pyproject` 0 tham chiếu |
| Q3 | CI workflow: thêm job `lint` (ruff check + ruff format --check) chạy TRƯỚC `test`; giữ matrix 3 OS × 2 Python | `ci.yml` hiện: 1 job test |
| Q4 | Fix các lỗi lint/type mà ruff+mypy phát hiện trong `agent_system/` (chỉnh code tối thiểu, không refactor lớn) | chưa chạy nên chưa biết — **số lỗi thật sẽ được ghi vào `docs/lint-baseline.md`** |
| Q5 | `.github/workflows/ci.yml`: thêm `pip install ruff mypy` + 2 lệnh check | — |

## Scope — OUT
- Không bật mypy `--strict` toàn cục (sẽ vỡ hàng trăm dòng — để module metrics-kpi track baseline giảm dần)
- Không đổi API/đường dẫn (quy tắc 12-bước bước 5)
- Không đụng `Archive/`

## Commands
```bash
cd /mnt/second_drive/Agent_system
uv tool install ruff            # hoặc: uv run --with ruff ruff --version
uv run --no-project --python 3.11 --with ruff ruff check agent_system/ tests/
uv run --no-project --python 3.11 --with ruff ruff format --check agent_system/ tests/
uv run --no-project --python 3.11 --with mypy mypy agent_system/ --ignore-missing-imports --no-strict-optional
# test sau khi fix
uv run --no-project --python 3.11 --with pytest python -m pytest tests/ -q
```

## Testing Strategy
| Mức | Cách | Acceptance |
|---|---|---|
| Lint | `ruff check` + `ruff format --check` | **0 errors** |
| Type | `mypy` (non-strict) | số lỗi ghi vào `docs/lint-baseline.md`; **không tăng** so baseline cuối module |
| Test | pytest toàn suite | 0 failed / 0 error (baseline cleanup: 115 passed) |
| CI-local | chạy đúng 2 lệnh trong `ci.yml` job lint | pass local trước khi push |
| CI-real | (chỉ khi anh push) GitHub Actions 3 OS | 3/3 green |

## Boundaries
- **Always:** 1 commit 1 nhóm fix; sau mỗi fix chạy test; baseline file commit kèm
- **Ask first:** thêm dependency runtime (ruff/mypy chỉ dev-deps trong CI — OK không cần hỏi); đổi logic code >10 dòng để fix type error
- **Never:** suppress lỗi bằng `# noqa` hàng loạt (mỗi noqa phải có lý do 1 dòng); bỏ test để lint xanh; push

## Success Criteria
1. `ruff check agent_system/ tests/` → 0 errors
2. `mypy agent_system/` → baseline ghi nhận, count ≤ baseline cuối (phải có `docs/lint-baseline.md`)
3. `ci.yml` có job `lint` chạy trước `test`
4. pytest suite xanh
5. Không file nào trong `agent_system/` đổi hành vi (test suite chứng minh)

## Open Questions
1. ruff rule set: chọn `E,F,I,W` (an toàn) hay thêm `UP,B,SIM` (nhiều fix hơn)? (mặc định: E,F,I,W + `UP` cho py311)
2. mypy: baseline non-strict hay bắt đầu `--strict` cho 2 module mới nhất (`flow.py`, `doctor.py`) làm pilot? (mặc định: non-strict toàn cục + pilot strict 2 file)
3. Có push lên GitHub để CI thật chạy không? (nếu repo có remote — check `git remote -v`)
