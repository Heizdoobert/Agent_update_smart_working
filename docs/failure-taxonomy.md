# Failure Taxonomy — Agent System

Mỗi lần lỗi (test fail, build break, critic < 100), ghi 1 trace vào `docs/trace-log/` theo bảng dưới.
Mục tiêu: sau ~100 trace, chạy Open + Axial coding (xem `docs/ERROR_ANALYSIS.md`) để rút pattern.

**7 cột bắt buộc cho mỗi trace:**

| # | Cột | Ý nghĩa | Ví dụ |
|---|---|---|---|
| 1 | `ts` | ISO-8601 timestamp | 2026-11-20T17:30:00+07:00 |
| 2 | `cat` | Mã category (E1–E5, §below) | E1 |
| 3 | `sym` | Symptom — gì xảy ra, 1 dòng | `import token_engine` thành công trong venv Agent_system |
| 4 | `ctx` | Context — file/function/commit liên quan | `SKILL/.venv/pyvenv.cfg` command → Agent_system |
| 5 | `root` | Root cause — vì sao (sau khi RCA) | venv cross-wired: pip editable trỏ repo khác |
| 6 | `fix` | Fix đã áp dụng | rebuild venv via uv + `git rm -r --cached .venv` |
| 7 | `pre` | Prevention — làm gì để không lặp lại | untrack .venv từ git (commit fd6272a) |

---

## Categories (E1–E5)

### E1 — Environment / Dependency (môi trường)
Venv sai, package thiếu, version Python không khớp, import trỏ repo khác, `.env`/config thiếu.
> *Điển hình session này: SKILL/.venv cross-wired → token_engine import ra repo Agent_system.*

### E2 — Correctness (sai logic)
Code chạy được nhưng kết quả sai: annotation sai, union type, off-by-one, edge case chưa xử lý.
> *Điển hình: F821 `CriticReport` dùng annotation không import (chỉ sống nhờ `from __future__ import annotations`).*

### E3 — Integration / Contract (gỡ kết nối)
2 module kỳ vọng interface khác nhau, manifest/entrypoint sai, CI matrix vỡ, tool description mismatch.
> *Điển hình: `agent_plugin.json` entrypoint `plugin.py` không tồn tại.*

### E4 — Process / Workflow (quy trình)
Bỏ bước verify, commit không kèm evidence, đánh dấu done sai, không cập nhật handoff file, đổi case đã PASS.
> *Điển hình: `git add -A` vô tình commit junk (image, time_limit, uv.lock) — thiếu bước check scope.*

### E5 — Performance / Resource (hiệu năng)
Timeout, memory leak, N+1 query, token budget vượt, context window tràn, retry loop vô hạn.
> *(Chưa có case thật trong session này — giữ category để ghi nhận khi xảy ra.)*

---

## Quy tắc ghi trace

1. **Ghi NGAY** sau khi fix (nhớ root + fix rõ), không để cuối ngày.
2. `root` phải khác `sym` — nếu chỉ copy symptom vào root là chưa RCA.
3. Không xoá trace cũ — tích luỹ để ERROR_ANALYSIS.
4. Một lỗi = một trace (đừng gộp 2 lỗi thành 1 dòng).
