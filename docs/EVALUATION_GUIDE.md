# Evaluation Guide for Asynchronous Coordination

## 1. Purpose
This document describes how to **measure** and **compare** the performance, reliability, and resource usage of the asynchronous multi‑agent coordination stack introduced in the research plan.

## 2. Test Environments
| Environment | OS | Architecture | Docker Image |
|-------------|----|--------------|--------------|
| Linux (Ubuntu 22.04) | x86_64 | `agent/async-coord:linux` |
| macOS (12.6) | arm64 | `agent/async-coord:macos` |
| Windows Server 2022 | x86_64 | `agent/async-coord:windows` |

Use the supplied `docker-compose.yml` (see `scripts/docker-compose.yml`) to spin up the full stack (Redis, Celery workers, coordination service, and a sample agent).

## 3. Benchmarks
### 3.1 Throughput
- **Definition**: Number of tasks successfully completed per second.
- **Command**: `python scripts/benchmark_async_coordination.py --benchmark throughput`
- **Metrics collected**: `tasks_per_sec`, `avg_latency_ms`, `p95_latency_ms`.

### 3.2 Latency
- **Definition**: End‑to‑end time from task submission to result storage.
- **Command**: `python scripts/benchmark_async_coordination.py --benchmark latency`

### 3.3 Resource Usage
- **CPU / Memory** for each worker process. Use `psutil` inside the benchmark script and store CSV output.

### 3.4 Failure Recovery
- Simulate worker crash (`kill -9 <pid>`) during a batch and verify that the task is re‑queued and completed.
- Record the number of retries, time to recovery, and any lost messages (should be 0).

## 4. Test Data
- **Task payload**: Small JSON (<3 KB) with a simple calculation (e.g., `{'op': 'add', 'a': 1, 'b': 2}`) to isolate coordination overhead.
- **Batch sizes**: 10, 100, 1 000, 10 000 tasks.

## 5. Result Reporting
- Store raw JSON results in `results/raw/`.
- Generate a summary Markdown file `results/benchmark_results.md` using the helper script `scripts/generate_report.py`.
- Include **charts** (via `matplotlib` or `plotly`) for throughput vs. batch size and latency distribution.

## 6. Comparative Baselines
| Baseline | Description |
|----------|-------------|
| **Sync‑direct** | Agent A calls Agent B via HTTP and waits (no queue). |
| **Queue‑only** | Celery queue without coordination service (no lock, no state). |
| **Full async stack** | Our proposed architecture (lead orchestrator + workers + 3‑tier memory). |

Run the same benchmark suite on each baseline and compare the numbers in the final report.

## 7. Acceptance Criteria
- **Throughput**: ≥ 80 % of sync‑direct baseline for batch size ≥ 1000.
- **Latency**: 95th‑percentile ≤ 200 ms for batch size 1000.
- **Zero lost messages** in failure‑recovery scenario.
- **Documentation** of all steps, scripts, and configuration files committed to the repo.

---
*Document version: 0.1 – 2026‑11‑05*
