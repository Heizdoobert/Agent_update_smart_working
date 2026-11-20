# Spec: metrics-kpi — Dashboard Context + KPI + trần retry (Module 7/7)

> Trạng thái: 🟡 CHỜ DUYỆT · Map: `CAPABILITY_MAP.md` (đã duyệt) · Phụ thuộc: `verification-harness` (xong)
> Nguồn chuẩn: THIẾT §14.5 (Context dashboard), §22 (Metrics & KPIs), §18.5 (trần retry ≤2), Mục 10 (KV-cache), §20.3 (AI Platform checklist)

## Objective
Đo được + cảnh báo tự động 3 nhóm: (a) **Context economy** — usage %, KV-cache, in:out ratio, tool count (Thiếu S5); (b) **KPI North Star** — rollback rate, self-verification rate, token shift to verification (Thiếu S6); (c) **Trần retry** vòng FLOW ≤2 (Thiếu S7). Mục tiêu: hệ thống **tự báo** trước khi vào Dumb Zone / vượt ngân sách, không để người phát hiện.

## Scope — IN

| # | Việc | Chi tiết |
|---|---|---|
| M1 | `agent_system/metrics.py` — module đo (domain-agnostic) | Functions: `context_usage_pct(tokens_used, window)` → warn@30 / critical@40 (THIẾT §14.5); `kv_cache_hit_rate(hits, total)` → target >80%; `input_output_ratio(in_t, out_t)` → target <80:1; `tool_count(n)` → <15 safe / >30 prune. Mỗi function trả struct `{value, level: safe/warn/critical, action}` |
| M2 | `agent_system/metrics.py` — KPI functions | `rollback_rate(reverted, total)` → ≤0.5%; `self_verification_rate(proven, total)` → >90%; `token_shift_to_verification(verify_tokens, total)` → ~70%. Nguồn data = log `features.json` + trace-log (không cần DB mới) |
| M3 | `agent_system/cli/main.py` thêm subcommand `agent-system metrics [--json]` | In dashboard bảng (text) hoặc JSON. Nguồn: đọc `claude-progress.txt` (context % cuối) + `features.json` (verification status) + optional `docs/lint-baseline.md`. **Không cần server chạy** — tính từ file |
| M4 | Trần retry vòng FLOW ≤2 (THIẾT §18.5, Stripe Minions) | Trong `flow.py`/MCP `flow_plan_approve`: nếu sub-agent fail >2 vòng → **bắt buộc bàn giao người** (đúng "Human Gate"). Kiểm tra code hiện tại: `reflector` đã có trần 3→5 → **hạ xuống ≤2 cho vòng FLOW song song** (riêng `reflect` giữ 3) |
| M5 | `docs/KPI_DASHBOARD.md` — bảng metric + ngưỡng + hành động (copy THIẾT §14.5 + §22.2) | 8 metric × (An toàn/Cảnh báo/Critical/Hành động). Live value cập nhật bằng `agent-system metrics` |
| M6 | Alert: khi `context_usage_pct` ≥30 → log WARN vào `claude-progress.txt`; ≥40 → in đỏ + gợi ý "reset session" (THIẾT §18.5 "Reset phiên khi context >40%, không summarization") | trong metrics.py + CLI |
| M7 | `features.json` thêm F-007 (module này) `verification` = "`agent-system metrics` chạy + 3 KPI có value + trần retry FLOW=2 trong code" | liên kết |

## Scope — OUT
- Không xây web dashboard / Prometheus (chỉ file + CLI text/JSON — đúng "offline thuần")
- Không thêm DB (data nguồn = file handoff + trace-log)
- Không đổi API MCP đã phát hành (chỉ thêm, không sửa nghĩa)

## Commands
```bash
cd /mnt/second_drive/Agent_system
uv run --no-project --python 3.11 --with pytest \
  python -m agent_system.cli.main metrics            # bảng text
uv run --no-project --python 3.11 --with pytest \
  python -m agent_system.cli.main metrics --json     # JSON
# verify trần retry
grep -n "max_rounds\|MAX_RETRY\|max_iterations" agent_system/flow.py agent_system/mcp/tools.py
# test module mới
uv run --no-project --python 3.11 --with pytest \
  python -m pytest tests/test_metrics.py -v
uv run --no-project --python 3.11 --with pytest python -m pytest tests/ -q
```

## Testing Strategy
| Mức | Cách | Acceptance |
|---|---|---|
| Unit | `tests/test_metrics.py`: 7 functions × (safe/warn/critical) boundary | mỗi ngưỡng 30/40, 80, 80:1, 15/30, 0.5, 90, 70 có test 2 phía |
| CLI | `metrics` + `metrics --json` | exit 0; JSON parse sạch; 8 metric xuất hiện |
| Trần retry | test mô phỏng FLOW fail 2 lần → stop + bàn giao người; fail 1 lần → retry | hành vi đúng |
| Alert | giả `context_usage_pct`=45 → WARN/CRITICAL log sinh ra | có dòng trong output |
| Suite | pytest toàn bộ | 0 failed / 0 error |

## Boundaries
- **Always:** metrics tính từ file (không server); ngưỡng cứng theo THIẾT (30/40, 0.5, 90, 70, 2); mỗi metric có `action` kèm
- **Ask first:** đổi ngưỡng (cần lý do + ghi vào KPI_DASHBOARD); thêm metric mới
- **Never:** để `metrics` crash khi file thiếu (phải in "no data" + exit 0); tăng trần retry >2; xóa log WARN

## Success Criteria
1. `tests/test_metrics.py` pass (≥21 test boundary)
2. `agent-system metrics` → bảng 8 metric có value + level + action
3. `agent-system metrics --json` → JSON valid, đủ 8 key
4. Trần retry FLOW = 2 trong code (grep bằng chứng) + test hành vi
5. `docs/KPI_DASHBOARD.md` đủ 8 metric × 4 cột
6. `features.json` F-007 đầy đủ
7. Toàn suite xanh

## Open Questions
1. North Star "rollback rate ≤0.5%" — nguồn data revert từ đâu? (git log `Revert` + `features.json.status=rolled_back`?) Anh confirm source.
2. "Token shift to verification ~70%" — đo bằng token thật (cần log từ client) hay ước tính từ số lần gọi verify tool? (mặc định: ước tính từ trace-log, ghi rõ là estimate)
3. Có push metrics lên một nơi tập trung (pixonhub / sheet) không, hay giữ trong repo? (mặc định: giữ trong repo + `metrics --json` để pipe đi)
4. Trần retry 2: áp cho **mọi** vòng FLOW, hay chỉ vòng song song multi-agent (vòng đơn vẫn 3)? (khuyến nghị: multi=2, single=3)
