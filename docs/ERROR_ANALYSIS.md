# ERROR_ANALYSIS — Quy trình phân tích lỗi (Open + Axial coding)

**Khi nào chạy:** khi `docs/trace-log/` đạt **~100 trace**. Không chạy sớm — mẫu nhỏ sẽ rút ra pattern sai.

## Bước 1 — Open coding (mở)

Đọc MỌI trace trong `docs/trace-log/`. Với từng trace:
1. Nhãn `cat` (E1–E5) đã có.
2. Đọc `sym` + `root`, tự đặt **1 từ khóa pattern** (không gò vào E1–E5 — để phát hiện pattern mới ngoài taxonomy).
3. Ghi vào bảng: `trace_id | cat | từ-khóa-pattern`.

## Bước 2 — Axial coding (trục)

1. Gom tất cả từ-khóa-pattern giống nhau thành **cluster**.
2. Mỗi cluster = **1 pattern lỗi**. Đặt tên + định nghĩa 1 câu.
3. Xếp cluster theo tần suất (trace nào lặp lại nhiều nhất).
4. Với mỗi pattern top-5: ghi **root cause chung** + **prevention chung** (rút từ cột 5 + 7).

## Bước 3 — Quyết định hành động (Output)

Với mỗi pattern top-5, CHỌN 1 hành động cụ thể:

| Loại hành động | Khi nào |
|---|---|
| **Add rule** vào `.agent/rules.md` | Lỗi do thiếu quy trình (E4) — ví dụ "check scope trước `git add -A`" |
| **Add ruff/mypy rule** | Lỗi code (E2) phát hiện được bằng static analysis |
| **Add test** | Edge case (E2) cần bảo vệ vĩnh viễn |
| **Add CI job / check** | Lỗi môi trường (E1) lặp lại |
| **Update taxonomy** | Phát hiện category mới ngoài E1–E5 → thêm E6 |

## Output chuẩn (sau mỗi lần chạy)

```
## ERROR_ANALYSIS — <date> (N traces)
### Pattern top-5
1. <tên pattern> — <N> traces — root: <...> — action: <rule/test/CI>
...
### Category distribution
E1: n | E2: n | E3: n | E4: n | E5: n
### Decisions
- [ ] Added rule X to .agent/rules.md
- [ ] Added test Y
```

> **Lưu ý:** Đây là quy trình TĨNH (offline), chạy bằng người/agent khi đủ mẫu — KHÔNG phải code chạy tự động. `metrics-kpi` (F-007) đo CHỈ SỐ live; `ERROR_ANALYSIS` này phân tích TRIỆT ĐỂ khi đủ dữ liệu.
