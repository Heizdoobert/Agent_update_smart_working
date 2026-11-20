# Spec: handoff — Bộ bàn giao phiên theo chuẩn THIẾT (Module 4/7)

> Trạng thái: 🟡 CHỜ DUYỆT · Map: `CAPABILITY_MAP.md` (đã duyệt) · Phụ thuộc: `ci-quality` (xong)
> Nguồn chuẩn: THIẾT Mục 11 (mất trạng thái phiên dài), §15.2 (Long-Running Harness), §18.5 (Bước 4), template §23.1–23.4

## Objective
Mỗi phiên agent mới **khôi phục 100% trạng thái** từ tệp — không đoán mò (Thiếu S3). Bộ handoff gồm 4 file chuẩn + 1 nghi thức bắt buộc. **`features.json` = chính 7 module của capability map** (đã duyệt) → spec sống của repo.

## Scope — IN

| # | Việc | Chi tiết |
|---|---|---|
| H1 | `features.json` ở root | Theo template §23.1: 7 features F-001..F-007 = 7 module (cleanup, docs-hygiene, ci-quality, handoff, error-taxonomy, verification-harness, metrics-kpi); mỗi feature: `status` (pending/done), `acceptance_criteria` (copy Success Criteria từ SPEC-*.md), `verification.command` + `evidence_required`, `dependencies` = cột "Phụ thuộc" của map |
| H2 | `claude-progress.txt` ở root | Theo template §23.2: ghi SESSION header, context %, feature in progress, steps completed, next, blockers, Git HEAD, evidence captured. **Cập nhật cuối mỗi phiên làm việc** |
| H3 | `todo.md` ở root | Theo template §23.3: Current Goal + Done/In Progress/Next/Notes; notes chứa 2 rule của THIẾT: "Keep wrong stuff in context", "Don't get few-shotted" |
| H4 | `docs/SESSION_RITUAL.md` — nghi thức bắt đầu phiên (3 bước, THIẾT §18.5) | 1) đọc `git log --oneline -10`  2) đọc `claude-progress.txt`  3) chạy health check: `uv run --no-project --python 3.11 --with pytest python -m pytest tests/ -q` + `uv run ... ruff check agent_system/` → chỉ khi xanh mới làm việc |
| H5 | Thêm 1 dòng vào `.agent/rules.md` (marked block agent-system) | "Mỗi phiên bắt đầu: chạy nghi thức SESSION_RITUAL.md" — KHÔNG viết lại 12 bước |
| H6 | `features.json` là nguồn: module nào done → cập nhật `status: done` + date + commit SHA (bằng chứng) | quy tắc: KHÔNG hỏi agent "xong chưa" — chỉ `features.json.status` + evidence là sự thật (THIẾT Mục 11 Vấn đề A) |

## Scope — OUT
- Không thay thế `CAPABILITY_MAP.md` (map = ranh giới; features.json = trạng thái thực thi)
- Không tự động tạo cron (đề xuất cron update progress = Open Question, cần anh duyệt)

## Commands
```bash
cd /mnt/second_drive/Agent_system
# verify JSON hợp lệ
python3 -m json.tool features.json > /dev/null && echo OK
# verify ritual chạy được
uv run --no-project --python 3.11 --with pytest python -m pytest tests/ -q
# verify 3 file tồn tại
ls features.json claude-progress.txt todo.md docs/SESSION_RITUAL.md
```

## Testing Strategy
| Mức | Cách | Acceptance |
|---|---|---|
| Schema | `python3 -m json.tool` + so mẫu template §23.1 | parse sạch; đủ 7 features; mỗi feature đủ 6 trường (id,name,status,priority,acceptance_criteria,verification) |
| Trạng thái thật | đối chiếu `status` với thực tế: cleanup=đang làm, còn lại pending | khớp |
| Ritual | chạy 3 lệnh trong SESSION_RITUAL.md theo đúng thứ tự | 3/3 pass |
| Session recovery (thử) | mở phiên mới giả lập: chỉ đọc 4 file → có thể nói đúng "đang làm gì, bước nào tới, blocker gì" không | checklist 3 câu trả lời đúng |

## Boundaries
- **Always:** progress file ghi **cuối** mỗi phiên; JSON không bao giờ ghi bằng markdown (THIẾT §15.2.2: model ít sửa bậy file JSON hơn MD); 1 phiên = 1 SESSION block append (không sửa lịch sử block cũ — append-only, THIẾT §14.3.1)
- **Ask first:** thêm cron tự động; đổi cấu trúc features.json sau khi đã có ≥1 feature done
- **Never:** ghi progress bằng cách rewrite block phiên cũ; đánh dấu `done` không có commit SHA + evidence

## Success Criteria
1. 4 file tồn tại đúng vị trí; JSON valid
2. `features.json` = 7 features khớp 1-1 với `CAPABILITY_MAP.md` (id, dependency)
3. Nghi thức 3 bước chạy pass
4. Test suite xanh
5. `cleanup` (F-001) có `status: done` + SHA + bằng chứng test khi module 1 kết thúc

## Open Questions
1. Có muốn tôi tự append block `claude-progress.txt` cuối mỗi phiên không (không cần anh nhắc)?
2. `todo.md` giữ ở root hay merge vào `claude-progress.txt` để bớt 1 file? (khuyến nghị: giữ 2 file — THIẾT tách riêng 2 vai trò: goal vs progress)
3. Cron tự động cập nhật KPI/progress mỗi tối? (để module metrics-kpi quyết định)
