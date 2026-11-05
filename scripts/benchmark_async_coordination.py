import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
import psutil

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from coordination_service import echo_task


def run_throughput(batch_size: int) -> dict:
    start = time.time()
    for i in range(batch_size):
        # Fire-and-forget Celery task invocation
        echo_task.apply_async(args=[{"seq": i, "op": "echo"}], ignore_result=True)
    elapsed = time.time() - start
    tps = batch_size / elapsed if elapsed > 0 else 0
    return {"batch_size": batch_size, "tasks_per_sec": tps, "total_time": elapsed}


def run_latency(batch_size: int, timeout: float = 5.0) -> dict:
    # Warm-up phase (10 tasks) to eliminate cold start jitter
    for i in range(10):
        try:
            res = echo_task.apply_async(args=[{"seq": i, "op": "warmup"}])
            res.get(timeout=timeout)
        except Exception:
            pass

    latencies = []
    for i in range(batch_size):
        t0 = time.time()
        result = echo_task.apply_async(args=[{"seq": i, "op": "echo"}])
        result.get(timeout=timeout)
        latencies.append((time.time() - t0) * 1000)  # ms
    if not latencies:
        return {"batch_size": batch_size, "avg_latency_ms": 0.0, "p95_latency_ms": 0.0}
    avg = sum(latencies) / len(latencies)
    sorted_latencies = sorted(latencies)
    p95_idx = max(0, int(0.95 * len(sorted_latencies)) - 1)
    p95 = sorted_latencies[p95_idx]
    return {"batch_size": batch_size, "avg_latency_ms": avg, "p95_latency_ms": p95}


def resource_usage(pid: int) -> dict:
    p = psutil.Process(pid)
    return {"cpu_percent": p.cpu_percent(interval=0.1), "memory_mb": p.memory_info().rss / 1024 / 1024}


def main():
    parser = argparse.ArgumentParser(description="Benchmark async coordination stack with Celery tasks.")
    parser.add_argument("--benchmark", choices=["throughput", "latency"], required=True)
    parser.add_argument("--batch", type=int, default=1000)
    parser.add_argument("--timeout", type=float, default=5.0, help="Timeout in seconds for latency tasks (default: 5.0)")
    args = parser.parse_args()

    if args.benchmark == "throughput":
        result = run_throughput(args.batch)
    else:
        result = run_latency(args.batch, timeout=args.timeout)

    out_dir = REPO_ROOT / "results" / "raw"
    out_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    out_path = out_dir / f"{args.benchmark}_{args.batch}_{timestamp}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    print(f"Result written to {out_path}")


if __name__ == "__main__":
    main()
