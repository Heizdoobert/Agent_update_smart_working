# TODO (handoff checklist — v2.0 remediation)

## DONE
- [x] F-001 cleanup — archive big-data, junk, dead tests (commit b90f07a)
- [x] F-002 docs-hygiene — GEMINI/CLAUDE dedup, manifest, README, PROJECT_MAP (670f344)
- [x] F-003 ci-quality — ruff gate + lint CI job + F821/F841 fixes (9650cdb)

## IN PROGRESS
- [ ] F-004 handoff — 4 files + ritual trigger in .agent/rules.md

## NEXT (build order)
- [ ] F-005 error-taxonomy — failure-taxonomy.md, trace-log/, ERROR_ANALYSIS.md, rules trigger
- [ ] F-006 verification-harness — init.sh, FEATURE_MAP.md, scripts/verify/verify_cli.sh
- [ ] F-007 metrics-kpi — metrics.py, tests/test_metrics.py, KPI_DASHBOARD.md, retry ceiling=2
- [ ] FINAL — full test run (all modules) + email full report → hhhuygiau@gmail.com

## RULES (đừng bỏ qua)
- Chỉ đánh dấu done SAU khi self-verify (evidence + commit SHA).
- Không push remote (theo spec).
- Không sửa case test đã PASS.
- Không đụng Redis 6379 (live) / FLOW_SKILL.
