# KPI DASHBOARD — Agent System

Bảng 8 metric + ngưỡng + hành động. **Live value** xem bằng:

```bash
cd /mnt/second_drive/Agent_system
.venv/bin/python -m agent_system.cli.main metrics            # bảng text
.venv/bin/python -m agent_system.cli.main metrics --json     # JSON (pipe đi)
```

> Ngưỡng CỨNG theo THIẾT §14.5 / §22 / §18.5 — đổi ngưỡng cần lý do + ghi chú ở đây.

## 8 Metrics

| Metric | 🟢 An toàn | 🟡 Cảnh báo | 🔴 Critical | Hành động |
|---|---|---|---|---|
| **context_usage_pct** | < 30% | ≥ 30% | ≥ 40% | 🔴 RESET SESSION (không summarization) — THIẾT §18.5 |
| **kv_cache_hit_rate** | > 80% | 60–80% | < 60% | batch prompt, dùng lại prefix |
| **input_output_ratio** | < 80:1 | 80–160:1 | > 160:1 | giảm context (lazy-load FEATURE_MAP), reset |
| **tool_count** | < 15 | 15–30 | > 30 | PRUNE — gộp tool hiếm dùng |
| **rollback_rate** | ≤ 0.5% | 0.5–2.5% | > 2.5% | North Star — chạy ERROR_ANALYSIS |
| **self_verification_rate** | > 90% | 80–90% | < 80% | mọi "done" phải có evidence + SHA (rules §8) |
| **token_shift_to_verification** | ≥ 60% (~70% target) | < 60% | — | tăng verify_cli checks (estimate từ trace-log) |
| **flow_retry_ceiling** | 2 (parallel) / 3 (single) | — | — | 2 fail vòng song song → **Human Gate** (THIẾT §18.5) |

## North Star (THIẾT §22)

1. **rollback_rate ≤ 0.5%** — ít revert nhất có thể.
2. **self_verification_rate > 90%** — đa số claim có bằng chứng thật.
3. **token_shift ~70%** — token đổ vào VERIFY (không phải chỉ generate).

## Quy tắc trần retry (THIẾT §18.5 — Stripe Minions)

- **Vòng FLOW song song (multi-agent):** fail **2** vòng → bắt buộc bàn giao người (Human Gate). Không retry vô hạn.
- **Vòng đơn (single-agent / reflect):** giữ trần **3** iteration.
- **TUYỆT ĐỐI KHÔNG** tăng trần > 2 cho vòng song song (metrics.py: `FLOW_RETRY_CEILING = 2`).

## Nguồn data (offline thuần — không server, không DB)

| Metric | Nguồn |
|---|---|
| context_usage_pct | `claude-progress.txt` (dòng `NN%` cuối) |
| self_verification_rate | `features.json` (done / total) |
| rollback_rate | git `Revert` commits + `features.json.status=rolled_back` (chưa cấu hình → `no_data`) |
| tool_count | CLI subcommand surface (12) |
| token_shift | trace-log (estimate) |
| kv_cache / in:out | cần log client (chưa có → `no_data`) |

> `metrics` **không bao giờ crash** khi file thiếu — metric thiếu data in `no_data` + exit 0 (Boundaries spec).
