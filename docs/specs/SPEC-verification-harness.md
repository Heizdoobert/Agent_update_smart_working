# Spec: verification-harness — Kiểm chứng thực thi + Feature Map (Module 6/7)

> Trạng thái: 🟡 CHỜ DUYỆT · Map: `CAPABILITY_MAP.md` (đã duyệt) · Phụ thuộc: `handoff` (xong)
> Nguồn chuẩn: THIẾT Mục 2 (Verifier Bottleneck, checklist Q1–Q5), Bước 2 (§18.3), §6.5 (bác bỏ bằng chứng chung), §2.2

## Objective
Agent phải **tự chứng minh kết quả** không cần người đọc diff (Thiếu S2). Xây: (a) Feature Map — bản đồ tính năng góc nhìn người dùng để agent & người **chung từ vựng**; (b) script tự khởi động + chạy luồng thật; (c) Definition of Done gắn **bằng chứng định lượng** theo đúng miền (CLI/perf/UI), bác bỏ "build đã pass".

## Checklist Q1–Q5 tự đánh giá (THIẾT §2.2) — áp cho repo này

| # | Câu hỏi | Trạng thái hiện tại | Gap |
|---|---|---|---|
| Q1 | Agent tự khởi chạy app không cần người bấm? | 🟡 CLI `agent-system` chạy được, chưa có script `init.sh` chuẩn | V (xem V1) |
| Q2 | Tự điều khiển luồng user? | 🔴 chưa có | V3 |
| Q3 | Đọc được profiling trace? | 🔴 chưa có | V4 |
| Q4 | Tái lập lỗi không cần người chỉ? | 🟡 có pytest nhưng thiếu repro-script tự động | V2 |
| Q5 | Tự chứng minh đúng miền tác động? | 🔴 thiếu evidence theo miền | V2, V5 |

> 🚨 Q1–Q4 chưa đạt → theo THIẾT **chưa chạy song song nhiều agent**; chỉ chạy 1 agent + người review. Module này chính là bước mở khóa.

## Scope — IN

| # | Việc | Chi tiết |
|---|---|---|
| V1 | `init.sh` ở root (template §23.4) | `set -e`; git init (nếu thiếu); tạo/kiểm tra 4 handoff files; **health check**: `pytest -q` + `ruff check` + import smoke test; in `=== Workspace ready ===` |
| V2 | `docs/FEATURE_MAP.md` — Feature Map (template §23.6) | Entry Points (CLI: `init`, `scan`, `mcp`, `plan`, `critic`, `reflect`, `memory`, `skill`, `session`, `install`, `doctor`) + **User Flows** từng command: input → action → output mong đợi → **Verification** (lệnh thật + evidence). Đây là từ vựng chung agent↔người |
| V3 | `scripts/verify/` — script kiểm chứng theo miền (THIẾT §6.5) | `verify_cli.sh`: chạy từng command thật, assert exit 0 + output chứa expected string. `verify_evidence.sh`: ghi screenshot/trace/profile vào `docs/trace-log/evidence/`. Mỗi script = 1 miền (CLI/perf/UI) |
| V4 | Definition of Done table trong `docs/FEATURE_MAP.md` | Sửa CLI → phải chạy lệnh thật; Tối ưu perf → phải có dấu vết profile định lượng (ms trước/sau); Đổi UI/config → phải có pixel/diff. **Bác bỏ** "build đã pass" |
| V5 | `features.json` (từ module handoff) — mỗi feature `verification.evidence_required` trỏ đúng script V3 | liên kết |

## Scope — OUT
- Không viết UI/E2E browser (repo này là CLI+MCP, không có frontend) → Q2 "điều khiển UI" = điều khiển **CLI flow**, không phải browser
- Không xây perf-harness chuyên sâu (chỉ profile baseline đơn giản cho `init.sh`/MCP round-trip)
- Không đụng `Archive/`

## Commands
```bash
cd /mnt/second_drive/Agent_system
bash init.sh                                  # phải in "Workspace ready"
bash scripts/verify/verify_cli.sh             # exit 0, mỗi command có evidence
ls docs/FEATURE_MAP.md
# verify evidence
ls docs/trace-log/evidence/                   # có file sau khi chạy verify
uv run --no-project --python 3.11 --with pytest python -m pytest tests/ -q
```

## Testing Strategy
| Mức | Cách | Acceptance |
|---|---|---|
| init | `bash init.sh` từ repo sạch (fresh clone giả lập) | exit 0 + "Workspace ready" + 4 handoff files tồn tại |
| CLI evidence | `verify_cli.sh` | mỗi command: exit 0 + expected string + evidence file ghi |
| Feature Map | soi đủ Entry Points + ≥5 User Flows, mỗi flow có Verification | OK |
| DoD | FEATURE_MAP có bảng 3 miền (CLI/perf/UI) + dòng "bác bỏ" | đủ |
| Suite | pytest xanh | 0 failed |

## Boundaries
- **Always:** mọi claim "hoàn thành" phải gắn 1 file evidence; chạy `verify_cli.sh` trước khi đánh dấu feature done; evidence append-only
- **Ask first:** thêm command mới vào FEATURE_MAP (đổi contract CLI); thêm perf target số cụ thể
- **Never:** đánh dấu done bằng "build pass" / "chạy được"; xóa evidence; bỏ qua 1 trong 3 miền khi sửa

## Success Criteria
1. `bash init.sh` → exit 0 + 4 handoff files + "Workspace ready"
2. `bash scripts/verify/verify_cli.sh` → exit 0 + `docs/trace-log/evidence/` có file
3. `docs/FEATURE_MAP.md` đủ Entry Points + ≥5 flows, mỗi flow có Verification + DoD table 3 miền
4. `features.json` mỗi feature có `evidence_required` trỏ script thật
5. pytest xanh

## Open Questions
1. Q2 "điều khiển UI" — repo này là CLI, tôi diễn giải thành **CLI flow**. Có đúng với ý THIẾT không, hay anh muốn gắn E2E cho một app client cụ thể (pixonhub desktop)?
2. Perf baseline: đo round-trip của MCP tool nào (tất cả 8 hay chỉ `agent_memory_search`)? (mặc định: 2 tool đại diện — memory_search + plan)
3. Có muốn `verify_cli.sh` chạy trong CI (job verify) không? (khuyến nghị: có — nối với ci-quality)
