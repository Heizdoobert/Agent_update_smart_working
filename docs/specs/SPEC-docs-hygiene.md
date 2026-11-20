# Spec: docs-hygiene — Dọn tài liệu, link gãy, config sai (Module 2/7)

> Trạng thái: 🟡 CHỜ DUYỆT · Map: `CAPABILITY_MAP.md` (đã duyệt) · Phụ thuộc: `cleanup` (xong)
> Nguồn chuẩn: THIẾT Mục 5 (Garden), Mục 15.1.1 (mô tả tool như onboarding doc)

## Objective
Repo chỉ còn tài liệu **sống, đúng, duy nhất**: 1 protocol duy cho agent, không link gãy, không entrypoint ảo, tài liệu THIẾT vào git, bản đồ dự án khớp cây thư mục sau cleanup.

## Scope — IN (bằng chứng đã verify)

| # | Việc | Bằng chứng hiện trạng |
|---|---|---|
| U1 | `GEMINI.md` & `CLAUDE.md`: workflow 12 bước bị **dán 2 lần** trong mỗi file; 2 file gần như trùng tuyệt đối | `grep -c "Immutable Task Execution Workflow"` = 2/file; `diff` ≈ giống nhau |
| U2 | `agent_plugin.json`: `entrypoint: "plugin.py"` — **file không tồn tại**; description "Unknown project" | `ls plugin.py` → No such file |
| U3 | `README.md`: 6 link trỏ `/mnt/second_drive/SKILL/...` (repo khác, máy-specific) — cụm Big Data sẽ vào `Archive/` sau cleanup | `grep -c "SKILL/" README.md` = 6 |
| U4 | `docs/PROJECT_MAP.md`: thiếu các module sống: `flow.py`, `doctor.py`, `feature_flags.py`, `distillation/` chỉ 1 dòng, `sdk/` thiếu `wizard/installer/scanner` chi tiết | so với cây thư mục thực + `ls agent_system/` |
| U5 | `docs/reference/rfc-agent-design.md` (82,506 B = đúng file THIẾT gốc) đang **untracked** → ai clone là mất | `git status` → `?? docs/reference/` |
| U6 | `RELEASE_NOTES.md` + `CHANGELOG.md`: ghi nhận "113 tests PASS" của cụm đã archive → thêm 1 dòng v2.0-remediation note | nội dung file |

## Scope — OUT
- Không đổi **nội dung** 12 bước workflow (chỉ khử trùng lặp) — nội dung là của Huy
- Không đụng `docs/specs/`, `docs/decisions/`, `docs/intent/`
- Không sửa `AGENTS.md` (nó = symlink `.agent/rules.md` của workspace ngoài repo — xác minh trước khi động)

## Commands
```bash
cd /mnt/second_drive/Agent_system
# verify trước
grep -c "Immutable Task Execution Workflow" GEMINI.md CLAUDE.md
diff GEMINI.md CLAUDE.md | head
grep -n "SKILL/" README.md
# verify sau
grep -c "Immutable Task Execution Workflow" GEMINI.md CLAUDE.md   # mỗi file = 1
grep -rn "second_drive/SKILL" README.md                             # = 0
git ls-files docs/reference/                                         # có rfc-agent-design.md
```

## Testing Strategy
| Mức | Cách | Acceptance |
|---|---|---|
| Link | script grep mọi `file://`/markdown link trong README + PROJECT_MAP → `test -e` từng target | 0 link gãy (sau khi sửa) |
| JSON | `python3 -m json.tool agent_plugin.json` | parse sạch + entrypoint trỏ file thật |
| Nội dung | `diff` 2 protocol files | giống nhau (hoặc 1 symlink) — 1 bản duy nhất |
| Test suite | `uv run --no-project --python 3.11 --with pytest python -m pytest tests/ -q` | vẫn xanh (module này không đụng code) |

## Boundaries
- **Always:** backup 1 branch trước khi edit; commit riêng 1 nhóm/sự việc; giữ convention commit hiện có
- **Ask first:** đổi tên/sửa nghĩa của 12 bước workflow; đổi description `agent_plugin.json` (nó mô tả plugin cho client nào?)
- **Never:** xóa nội dung rules (chỉ gộp trùng); đụng `agent_system/` code; push

## Success Criteria
1. `grep -c` workflow = **1** trong GEMINI.md và CLAUDE.md
2. 2 file protocol **đồng nhất** (1 source + 1 symlink hoặc nội dung byte-identical)
3. `agent_plugin.json`: entrypoint tồn tại HOẶC trường bị bỏ (tùy anh chọn); description đúng
4. README: 0 link trỏ máy khác; phần mô tả Big Data chỉ còn trỏ `Archive/bigdata-v04/`
5. `git ls-files docs/reference/` chứa `rfc-agent-design.md`
6. PROJECT_MAP khớp cây thư mục (mỗi module `agent_system/*` có ≥1 dòng mô tả)
7. Test suite vẫn xanh

## Open Questions
1. U2 — `agent_plugin.json` dùng cho client nào (Antigravity plugin registry?)? → quyết định sửa entrypoint hay bỏ file
2. GEMINI.md vs CLAUDE.md — file nào là "chủ" để symlink? (mặc định: CLAUDE.md chủ, GEMINI.md symlink)
3. U5 — commit tài liệu THIẾT có nên tách 1 commit riêng để review dễ hơn? (khuyến nghị: có)
