# Launch Plan — Agent_system v0.4.4 → v0.5.0 (2026-11-20)

> Áp skill `shipping-and-launch`. Launch = **push `main` (10 commits) → GitHub CI (lint → mypy → test @3.14)** → merge-ready.
> Repo: `Heizdoobert/Agent_update_smart_working` (remote origin, reachable — đã verify `git ls-remote`).
>
> ✅ **ĐÃ PUSH (2026-11-23):** `96a464c..dc9711f` → CI run `45102609286` = **success** (lint ✅ · mypy ✅ · test ubuntu/macos/windows @3.14 ✅). Remote SHA verify: `dc9711fe...` = local HEAD.
> Rollback reference: state trước push = `96a464c` (revert/checkout về SHA này nếu cần).

## Scope lần launch
- 9/9 features done (F-001…F-009), commit HEAD `c235c72`
- **BREAKING:** `requires-python 3.9 → 3.14` (F-009) — mọi consumer cài bằng Python 3.9–3.13 sẽ bị chặn install
- **GATE MỚI (blocking):** mypy CI job + ruff `UP` ruleset — sau launch, code không pass 2 gate này **không merge được nữa**
- 167 tests / mypy 0 / ruff clean / 6/6 E2E harness (verify 2026-11-20)

## Pre-launch checklist (bằng chứng đã chạy)

| Hạng mục | Trạng thái | Bằng chứng |
|---|---|---|
| Tests (unit) | ✅ 167 passed | `pytest tests/ -q` trên Py3.14, 2026-11-20 |
| E2E / smoke (staging) | ✅ 6/6 PASS | `scripts/verify/verify_cli.sh` (evidence: `docs/trace-log/evidence/`) |
| Lint | ✅ All checks passed | `ruff check` (E,F,W,I,UP @140) |
| Type check | ✅ 0 errors / 46 files | `mypy` baseline flags |
| Secrets in code | ✅ 0 hits | regex scan `sk-/AKIA/ghp_/xox*/Bearer` trên `agent_system/`+`tests/` |
| Secrets in git | ✅ | `git ls-files` chỉ còn `Archive/` code cũ (không có key) |
| Dependencies audit | ✅ N/A | `pyproject.toml`: **0 runtime deps**; `requirements.txt` đã archive (stale) |
| TODO/FIXME | ✅ 0 | grep `agent_system/ tests/` |
| Changelog | ✅ | `CHANGELOG.md` `[Unreleased]` cập nhật (Changed/Added/Fixed/Removed) |
| Docs | ✅ | `lint-baseline.md` đóng 2 baseline, `FEATURE_MAP.md`, specs/plan đủ |
| CI definition | ✅ | `ci.yml`: lint → mypy (blocking) → test @3.14, 3 OS |
| Feature flags | ✅ N/A | F-001…F-009 đều done, không có flag dở dang |
| Health check endpoint | ✅ N/A | CLI/library (không phải web service); `agent-system doctor` = health report |

**Khoảng trống đã khai báo (không block launch):**
- Không có `pip-audit` (không có runtime dependency → không có thứ để audit)
- Không có monitoring/observability production — repo là engine CLI/SDK, không phải service; KPI dashboard (`metrics` subcommand) đóng vai trò quan sát
- Error budget / SLO: chưa định nghĩa — ghi nhận, không block (không có SLO hiện tại)

## Rollback plan

### Trigger conditions (bất kỳ 1 → rollback)
1. CI đỏ trên `main` (lint/mypy/test) và không fix được trong 1 phiên làm việc
2. Consumer báo lỗi import/behavior mới phát hiện (không nằm trong 167 tests)
3. Phát hiện secret/không an toàn sau khi push (dù scan trước push sạch)

### Rollback steps
```bash
# Option A — rollback 1 module (nhanh, giữ module trước đó)
git revert --no-commit c235c72            # python-floor-314 (F-009)
git revert --no-commit <SHA mypy-fix>      # mypy-fix (F-008)
git commit -m "revert: F-009 + F-008 (launch rollback)"
git push

# Option B — rollback toàn bộ launch (về state trước remediation v2)
git revert --no-commit <10 commits>        # hoặc
git reset --hard 670f344                  # state trước docs-hygiene (backup branch: backup/pre-cleanup-v2)
git push --force-with-lease
```
- **Data rollback:** N/A — không có migration, không có DB, không có write-state phía consumer
- **Time to rollback:** Option A < 5 phút · Option B < 10 phút (không cần redeploy — CI chạy lại tự động)
- **Post-rollback verification:** `git ls-remote origin main` khớp SHA rollback + CI xanh

## Rollout sequence (thay vì big-bang)
1. ✅ Pre-launch checklist xanh (trên)
2. **PUSH `main`** (chờ duyệt của anh) — CI chạy tự động (lint → mypy → test, 3 OS)
3. **Verify CI xanh** trên GitHub (evidence: Actions run URL)
4. **Consumer check:** các repo/skill dùng `agent_system` (FLOW_SKILL, pixonhub) vẫn import OK trên Py3.14 — FLOW_SKILL không động, verify import 1 lần
5. **Monitor 24h:** lỗi CI mới, báo cáo consumer
6. **Follow-up sau launch:** pilot `--strict` mypy (1–2 tuần sau), bump version 0.5.0 + tag (nếu anh duyệt)

## Open decisions (cần anh)
| # | Quyết định | Mặc định đề xuất |
|---|---|---|
| 1 | **Push `main` lên `Heizdoobert/Agent_update_smart_working`?** (10 commits, chưa push) | ⏸ CHỜ ĐUYỆT — skill yêu cầu "Team notified", anh là approver |
| 2 | Bump version `0.4.4 → 0.5.0` + git tag? (semver: có breaking change → minor) | Sau khi CI xanh |
| 3 | Pilot `--strict` mypy (follow-up, không launch này) | 1–2 tuần sau |
