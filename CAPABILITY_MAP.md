# Capability Map: Agent_system v2.0 Remediation

> Trạng thái: ✅ ĐÃ DUYỆT (Huy — 2026-11-20)
> Nguồn chuẩn: `docs/reference/rfc-agent-design.md` (TÀI LIỆU NỘI BỘ THIẾT v2.0)
> Quy tắc thực thi: **archive-first, không xóa cứng** — mọi thứ move vào `Archive/`, giữ branch backup.

| Module id | Trách nhiệm | Phụ thuộc |
|---|---|---|
| `cleanup` | Di/archive 70 file Big Data cluster + rác (D1–D6), sửa `pyproject` (dòng `token_engine`), `.gitignore` | — |
| `docs-hygiene` | Gộp GEMINI/CLAUDE trùng lặp, sửa `agent_plugin.json`, README link gãy, `PROJECT_MAP` thiếu module, commit tài liệu THIẾT (U1–U8) | cleanup |
| `ci-quality` | Ruff + mypy strict (S1), sửa test hardcode `/home/agent` (U9), CI xanh 3 OS — **gate tin cậy cho mọi bước sau** | cleanup |
| `handoff` | `features.json` + `claude-progress.txt` + nghi thức bắt đầu phiên (S3, template §23 doc) | ci-quality |
| `error-taxonomy` | Failure taxonomy 4–8 danh mục + quy trình đọc trace/tuần (S4, doc §17) | handoff |
| `verification-harness` | Feature Map, test app-thật, acceptance criteria gắn evidence (S2, doc Bước 2) | handoff |
| `metrics-kpi` | Ngưỡng cảnh báo context 30/40%, trần retry vòng FLOW, KPI dashboard rollback/cost (S5/S6/S7) | verification-harness |

**Build order:** `cleanup` → (`docs-hygiene` ∥ `ci-quality`) → `handoff` → (`error-taxonomy` ∥ `verification-harness`) → `metrics-kpi`

**Assumptions đã xác nhận (2026-11-20):**
1. Phạm vi = toàn bộ remediation theo audit (UPDATE + DELETE + THIẾU).
2. Archive-first, branch backup, không xóa cứng.
3. `/mnt/second_drive/SKILL` là bản chủ của cụm Big Data (diff y hệt) → bản trong Agent_system là chết.
4. Tài THIẾT là nguồn chuẩn duy nhất.
5. Chỉ đụng repo `Agent_system`; không đụng Redis 6379, không đụng FLOW_SKILL.
6. Tài liệu tiếng Việt, code tiếng Anh.
7. Không có cron/pixonhub/tool nào gọi các script Big Data (Huy confirm).
