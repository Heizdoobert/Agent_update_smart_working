# Spec: error-taxonomy — Phân loại lỗi + quy trình đọc trace (Module 5/7)

> Trạng thái: 🟡 CHỜ DUYỆT · Map: `CAPABILITY_MAP.md` (đã duyệt) · Phụ thuộc: `handoff` (xong)
> Nguồn chuẩn: THIẾT Mục 17 (Error Analysis: Open + Axial Coding), template §17.5, §23.5, §22.3

## Objective
Dừng việc sửa prompt theo **cảm tính**. Thay bằng: đọc trace thật → gom nhóm lỗi → taxonomy 4–8 danh mục + tần suất → **tập trung sửa ở tầng tool/schema/harness** (đúng chỗ, THIẾT §17.4). Đây là vòng lặp cải tiến khoa học của hệ thống.

## Scope — IN

| # | Việc | Chi tiết |
|---|---|---|
| E1 | `docs/failure-taxonomy.md` — bảng 4–8 danh mục | Mỗi row: `ID (F01..F07)`, `category`, `description`, `frequency (%/count)`, `layer_to_fix (tool_schema/context_eng/harness/prompt_gate/aci_schema/orchestrator)`, `owner`, `status`. Khởi tạo từ template §17.5 (F01–F06) |
| E2 | `docs/trace-log/` — nơi dump trace | Mỗi incident/session fail = 1 file `YYYY-MM-DD-<slug>.md`: header (context %, model, feature id) + trace + **nguyên nhân gốc** + category taxonomy + link commit fix (nếu đã fix) |
| E3 | `docs/ERROR_ANALYSIS.md` — quy trình 2 bước (THIẾT §17.2) | **Bước 1 Open Coding (thủ công):** đọc ~100 trace, ghi chú tự do nguyên nhân cốt lõi (checklist dẫn dắt). **Bước 2 Axial Coding (LLM hỗ trợ):** gom nhóm thành taxonomy 4–8 danh mục + tần suất |
| E4 | `features.json` thêm F-005 (module này) `verification` = "có ≥1 trace log đã phân loại + taxonomy cập nhật" | liên kết với handoff |
| E5 | Thêm 1 dòng `.agent/rules.md`: "Mỗi lỗi fail chưa fix được → ghi 1 trace vào `docs/trace-log/` + gán taxonomy ID" | nối với Reflexion protocol có sẵn |

## Scope — OUT
- Không xây dashboard tự động (để metrics-kpi)
- Không tự động parse log của client ngoài (Claude/Cursor) — chỉ trace hệ thống sinh ra
- Không xoá trace cũ (append-only — "Keep the wrong stuff in", THIẾT §14.3.4)

## Commands
```bash
cd /mnt/second_drive/Agent_system
ls docs/failure-taxonomy.md docs/ERROR_ANALYSIS.md docs/trace-log/
# test: ghi 1 trace mẫu + phân loại
# (thủ công — không có lệnh test tự động cho taxonomy; acceptance = file tồn tại + đủ 6 cột)
# verify suite vẫn xanh
uv run --no-project --python 3.11 --with pytest python -m pytest tests/ -q
```

## Testing Strategy
| Mức | Cách | Acceptance |
|---|---|---|
| Cấu trúc | soi `failure-taxonomy.md` đủ 7 cột × ≥4 row | OK |
| Trace | 1 trace mẫu hợp lệ trong `docs/trace-log/` | đủ header + category + RCA |
| Quy trình | `ERROR_ANALYSIS.md` có 2 bước + checklist + số trace mẫu khuyến nghị (100) | đủ |
| Liên kết | `.agent/rules.md` có dòng trigger taxonomy | 1 dòng |
| Suite | pytest xanh | 0 failed |

## Boundaries
- **Always:** mỗi trace 1 file (không dồn); gán taxonomy ID trước khi fix; ghi layer_to_fix
- **Ask first:** thêm danh mục taxonomy mới (>6) — cần lý do; đổi `layer_to_fix` đã chốt
- **Never:** xóa trace; gán "done" khi chưa có commit fix; bỏ qua tần suất (bắt buộc đếm)

## Success Criteria
1. `docs/failure-taxonomy.md` tồn tại, ≥4 danh mục, đủ 7 cột
2. `docs/trace-log/` có ≥1 trace mẫu phân loại đúng format
3. `docs/ERROR_ANALYSIS.md` mô tả đủ Open + Axial coding + khuyến nghị ~100 trace
4. `.agent/rules.md` có trigger ghi trace khi fail
5. Test suite xanh

## Open Questions
1. Tần suất update taxonomy: hàng tuần (khuyến nghị, THIẾT §22.3) hay hàng tháng?
2. Có muốn tôi viết helper script `scripts/record_trace.py` (nhận slug + category → sinh file trace chuẩn format) để giảm thao tác tay? (hiện spec nói thủ công)
3. Source trace: chỉ từ hệ thống agent-system, hay cả trace từ FLOW_SKILL/pixonhub (nếu anh muốn một taxonomy thống nhất)?
