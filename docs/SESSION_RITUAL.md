# Session Ritual (handoff) — 3 bước, bắt buộc

## BƯỚC 1 — KHỞI ĐỘNG (mỗi session)

```bash
# 1.1 Load trạng thái trước
cat claude-progress.txt
cat todo.md

# 1.2 Nếu chưa có (session đầu / bị mất) — INIT workspace
bash init.sh

# 1.3 Xem feature đang làm + acceptance criteria
python3 -c "
import json
f = json.load(open('features.json'))
for x in f['features']:
    print(x['id'], x['status'], '-', x['name'])
"
```

## BƯỚC 2 — KẾT THÚC (mỗi session)

1. **Ghi `claude-progress.txt`** — context dùng, features in-progress, steps done (+evidence), next, blockers, git HEAD.
2. **Cập nhật `features.json`** — chỉ flip `status: done` **SAU** khi có:
   - Evidence (pytest / ruff / file list) + commit SHA, **VÀ**
   - `acceptance_criteria` toàn bộ tick.
3. **Commit** mọi thay đổi trong session (message nêu rõ module F-00x).

## BƯỚC 3 — XÁC NHẬN DONE (không được skip)

Một feature **CHỈ** được xem là `done` khi **CẢ BA**:
- [ ] Evidence thật (output pytest / ruff / file), không "tôi nghĩ nó pass"
- [ ] Commit SHA ghi trong `features.json` + `claude-progress.txt`
- [ ] `acceptance_criteria` **toàn bộ** tick

> **Cấm** đánh dấu done khi: test chưa chạy, test fail, chưa commit, hoặc chỉ "build pass" (spec verification-harness: "Build Pass" ≠ "Working").
