# Spec: cleanup — Archive Big Data cluster & rác (Module 1/7)

> Trạng thái: 🟡 CHỜ DUYỆT
> Map: `CAPABILITY_MAP.md` (đã duyệt) — module id `cleanup`, không phụ thuộc
> Nguồn chuẩn: `docs/reference/rfc-agent-design.md` Mục 5 (Garden Analogy), Bước 1 ("audit mẫu code cũ → xóa")

## Objective
Đưa repo `Agent_system` về trạng thái **chỉ chứa hệ thống sống** (package `agent_system/` + docs + tests của nó) trước khi build các module sau (docs-hygiene, ci-quality, ...). Xóa = **archive**: move vào `Archive/` + branch backup, KHÔNG xóa khỏi git history.

**Success =** mọi `git ls-files` không còn trỏ vào cụm Big Data; test suite chỉ chứa test của package sống; pyproject không kéo dead code vào venv.

## Scope — IN (đúng audit, bằng chứng đã verify)

| Nhóm | Paths | Bằng chứng đã verify |
|---|---|---|
| A. Big Data cluster (70 file tracked) | `token_engine/` `tri_modal_router/` `peft/` `data_pipeline/` `distributed_queue/` `coordination_service/` `memory_layer/` `utils/` `results/` `scripts/` | 0 import từ `agent_system/`; deps celery/pymilvus/duckdb không có trong pyproject/venv; Milvus 19530 không chạy; `diff -rq` vs `/mnt/second_drive/SKILL` = y hệt (twin chết) |
| B. Tests gắn cụm A | `tests/test_memory_isolation.py` `tests/test_tenant_vector_store_milvus.py` **`tests/test_cli_agent.py`** | `test_memory_isolation.py:10` `from memory_layer import ...`; `test_tenant_vector_store_milvus.py:22` `from scripts.tenant_vector_store import ...`; `test_cli_agent.py:10` `from scripts.run_agent import run_agent` → `scripts/run_agent.py:20` `from cli.agents_config import ...` (cả 2 path sắp archive); `test_e2e.py` KHÔNG import cụm A (chỉ chuỗi `"data_pipeline"` ở dòng 60/97/107) → **KHÔNG đụng** |
| C. Dead trong package | `agent_system/hadoop/` (untracked) | 0 import, không có Hadoop env |
| D. Rác root | `dump.rdb` (tracked), `time_limit` (0 byte, tracked), `image_29419c4c.jpg` (untracked) | `git ls-files`, `stat -c size=0`, `file` |
| E. Rác runtime demo | `.agent/insights_test123.json` `.agent/reflexion_state.json` (**tracked** — đã verify `git ls-files .agent/`) | nội dung `"test123"/"demo task"` → dùng `git mv`, KHÔNG dùng `mv` thường (để tránh staged-deletion + untracked copy) |
| F. Skills trùng lặp (root) | `adaptive-self-healing-agent/` `airtest-excel-ocr-testgen/` `core-subagent-team/` | trùng 1:1 với `~/.hermes/skills/...` + repo SKILL |
| G. Docs stale | `tasks/plan.md` `tasks/todo.md` (spec Big Data v0.4.3 đã xong) | nội dung = plan cũ |
| H. Config sửa kèm | `pyproject.toml:8` (bỏ `token_engine`), `.gitignore` (thêm `*.rdb`, `Archive/`) | `pyproject.toml:8` `include = ["agent_system", "token_engine"]` |

## Scope — OUT (không đụng trong module này)
- `docs/` (trừ việc commit `docs/reference/rfc-agent-design.md` → module docs-hygiene)
- `README.md`, `GEMINI.md`, `CLAUDE.md`, `agent_plugin.json` (→ docs-hygiene)
- `agent_system/` (core|reasoning|reflection|memory|skills|sdk|mcp|cli|flow.py|doctor.py) — **100% giữ nguyên**
- `tests/` trừ 2 file nhóm B (test_e2e.py KHÔNG đụng — đã verify không import cụm A)
- Redis 6379, FLOW_SKILL, repo SKILL — không đụng
- **Không `git push`** (branch backup local là đủ; push = Ask first)

### Nhóm I (thêm 2026-11-20, đã verify)
| Nhóm | Paths | Bằng chứng |
|---|---|---|
| I. CLI legacy standalone | `cli/` (3 file: agents_config.py, requirements.txt + __init__ nếu có) | `grep token_engine\|memory_layer\|data_pipeline cli/` = 0; chỉ `import os`; KHÔNG nằm trong package `agent_system/`, không import bởi ai; `requirements.txt` kéo torch/transformers (deps không dùng) → di vào `Archive/bigdata-v04/cli-legacy/` |

## Tech Stack
Python 3.11 (git mv + filesystem ops), git 2.x. Không thêm dependency nào.

## Commands
```bash
# 0. Trước khi làm: snapshot
git -C /mnt/second_drive/Agent_system status --short          # phải = git state đã biết (chỉ untracked như audit)
git -C /mnt/second_drive/Agent_system branch backup/pre-cleanup-v2

# 1. Move (không xóa)
git mv token_engine tri_modal_router peft data_pipeline distributed_queue \
       coordination_service memory_layer utils results scripts Archive/bigdata-v04/
git mv tests/test_memory_isolation.py tests/test_tenant_vector_store_milvus.py \
       tests/test_cli_agent.py Archive/bigdata-v04/tests/
git rm --cached dump.rdb time_limit                                # bỏ tracking, giữ file vật lý
mv agent_system/hadoop Archive/bigdata-v04/hadoop                  # untracked → mv thường
git mv .agent/insights_test123.json .agent/reflexion_state.json Archive/bigdata-v04/.agent-trash/   # TRACKED → git mv
git mv adaptive-self-healing-agent airtest-excel-ocr-testgen core-subagent-team Archive/skills-dup/
mv tasks/plan.md tasks/todo.md Archive/plan-v04/
git mv cli Archive/bigdata-v04/cli-legacy
# NOTE: folder skill `adaptive-self-healing-agent` (reflexion_runner.py trỏ ../../memory_layer)
#       nằm trong Archive/skills-dup/ — KHÁC Archive/bigdata-v04/ → relative path GÃY.
#       Chấp nhận: bản hermes-skill (~/.hermes/skills/...) đã gãy trước (target không tồn tại),
#       check=False nuốt lỗi. KHÔNG sửa skill hermes trong module này (ngoài repo).

# 2. Config
# pyproject.toml:8  →  include = ["agent_system"]
# .gitignore: thêm  →  *.rdb,  Archive/
# .venv: reinstall để regenerate editable finder (bản finder 0.4.3/0.4.4 hardcode path token_engine cũ):
.venv/bin/pip install -e . --no-deps
.venv/bin/python -c "import agent_system.cli.main, agent_system.mcp.server" && echo IMPORT-OK
.venv/bin/python -c "import token_engine" 2>&1 | grep -q ModuleNotFoundError && echo TOKEN_ENGINE-GONE-OK

# 2b. Consumer cross-repo (ASK FIRST — đụng repo SKILL):
# /mnt/second_drive/SKILL/.venv có editable finder MAPPING token_engine → repo này,
# và SKILL có importer sống (token_engine/tests/test_engine.py, scripts/run_big_data_pipeline_demo.py).
#   Option A (khuyến nghị): SKILL đã có token_engine local y hệt →
#     /mnt/second_drive/SKILL/.venv/bin/pip uninstall -y agent-system
#     /mnt/second_drive/SKILL/.venv/bin/pip install -e /mnt/second_drive/SKILL --no-deps
#     verify: /mnt/second_drive/SKILL/.venv/bin/python -c "import token_engine; print(token_engine.__file__)"
#     → phải trỏ /mnt/second_drive/SKILL/token_engine/__init__.py
#   Option B: giữ lại 1 path shim /mnt/second_drive/Agent_system/token_engine (KHỌNG khuyến nghị — giữ rác)

# 3. Chạy test: suite thu 118-3=115 tests (3 file dead rời; test_e2e GIỮ)
uv run --no-project --python 3.11 --with pytest python -m pytest tests/ -q
#   kỳ vọng: 115 passed, 0 failed, 0 error

# 4. Commit
git add -A && git commit -m "cleanup: archive big-data v0.4 cluster, dead tests, root junk (v2.0 map: cleanup)"
```

## Project Structure (sau cleanup)
```
Agent_system/
├── agent_system/          # package sống — KHÔNG ĐỤNG
├── cli/                   # agents_config (cần check: có import dead không? → verify step)
├── tests/                 # còn 31 file, chỉ test package sống
├── docs/                  # specs/decisions/intent/reference — KHÔNG ĐỤNG (ngoại lệ: reference/ commit ở docs-hygiene)
├── .agent/                # chỉ còn rules.md
├── Archive/               # MỚI — bản lưu, git-ignored, branch backup vẫn có
│   ├── bigdata-v04/
│   ├── skills-dup/
│   └── plan-v04/
├── CAPABILITY_MAP.md      # đã duyệt
├── SPEC-cleanup.md        # file này
└── docs/specs/SPEC-*.md   # spec các module sau
```

## Code Style
Không viết code trong module này — chỉ git mv / git rm --cached / sửa 2 dòng config. Commit message theo convention đã có trong `git log` (khởi đầu chữ thường, `scope: mô tả`).

## Testing Strategy
| Mức | Cách | Acceptance |
|---|---|---|
| Trước | `git status --short` + `git branch` | state khớp audit (không có surprise) |
| Sau mỗi nhóm | `uv run ... pytest tests/ -q` | count giảm đúng 2 test, 0 error |
| Cuối | `uv run ... pytest tests/ -q` + `git ls-files \| grep -c bigdata-cluster` | **115 passed / 0 failed / 0 error**; grep = 0; `pip` reinstall dry-run không kéo `token_engine` |
| Verify import | `PYTHONPATH=. uv run --with pytest python -c "import agent_system.cli.main, agent_system.mcp.server"` | import sạch |

## Boundaries
- **Always:** branch backup trước; mỗi nhóm move → chạy test → mới nhóm tiếp; báo cáo gì/làm-sao/bằng-chứng sau mỗi nhóm (quy tắc fix-chốt của Huy).
- **Ask first:** `git push`; đổi path trong code (bước 5 quy tắc 12-bước: TUYỆT ĐỐI không đổi path trong code — module này chỉ move file, không sửa code); đụng `agent_system/` bất kỳ file nào.
- **Never:** `git rm` (thường) các file tracked — chỉ `git mv` hoặc `git rm --cached`; đụng `tests/test_e2e.py`; đụng Redis/FLOW_SKILL/repo SKILL; commit secret.

## Success Criteria (đo được)
1. `git ls-files | grep -cE "token_engine|memory_layer|data_pipeline|distributed_queue|coordination_service|tri_modal_router|peft/|results/|scripts/|^cli/"` → **0**
2. `pytest tests/ -q` → **115 passed, 0 failed, 0 error** (3 test dead đã rời: test_memory_isolation, test_tenant_vector_store_milvus, test_cli_agent; test_e2e GIỮ + PASS)
3. `git branch --list 'backup/*'` có `backup/pre-cleanup-v2`
4. `Archive/` tồn tại đủ 4 nhóm (bigdata-v04, skills-dup, plan-v04, .agent-trash); `.gitignore` chứa `Archive/`
5. `pyproject.toml` không còn `token_engine` **+** `.venv` đã reinstall: `import agent_system.cli.main` OK, `import token_engine` → ModuleNotFoundError
6. (Nếu duyệt Option A) `SKILL/.venv`: `import token_engine` → trỏ `/mnt/second_drive/SKILL/token_engine/__init__.py`
7. `git status --short` sau commit = sạch (không staged-deletion orphan, không untracked copy từ mv thường)

## Open Questions
1. ~~`cli/` có import cụm A không?~~ → **ĐÃ GIẢI QUYẾT (doubt cycle 1):** `cli/agents_config.py` chỉ `import os`, `scripts/run_agent.py:20` import nó → cả `cli/` là dead, đã đưa vào scope (nhóm I).
2. **BLOCKER 2 (doubt cycle 1) — consumer cross-repo:** `SKILL/.venv` có editable finder trỏ `token_engine` vào repo này + SKILL có importer sống. **Option A** (uninstall agent-system trong SKILL venv, reinstall từ SKILL local — khuyến nghị) hay **Option B** (giữ path shim)? → **ASK FIRST vì đụng repo SKILL**
3. Branch backup: branch `backup/pre-cleanup-v2` là đủ, có cần thêm tag? (mặc định: branch đủ)
4. `dump.rdb`: 2 process redis đang chạy (:6379). Plan giữ file vật lý ở chỗ cũ (chỉ untrack) → an toàn cả khi redis có CWD ở repo root. Không cần stop redis.
