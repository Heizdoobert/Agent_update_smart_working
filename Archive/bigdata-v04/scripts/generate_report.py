'''"""Generate a markdown benchmark report.

- Reads every *.json file under `results/raw/`.
- Each JSON file contains either throughput or latency metrics (see
  `benchmark_async_coordination.py`).
- Produces `results/benchmark_report.md` with a table per benchmark type.
"""'''

import json
import os
from pathlib import Path
from collections import defaultdict

RESULTS_ROOT = Path(__file__).resolve().parents[1] / "results"
RAW_DIR = RESULTS_ROOT / "raw"
REPORT_PATH = RESULTS_ROOT / "benchmark_report.md"


def load_json(p: Path) -> dict:
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)


def collect_results() -> dict:
    """Return mapping: benchmark_type -> list[dict]"""
    data = defaultdict(list)
    if not RAW_DIR.is_dir():
        print(f"[WARN] No raw results folder: {RAW_DIR}")
        return data

    for json_file in RAW_DIR.glob("*.json"):
        payload = load_json(json_file)
        bench_type = json_file.stem.split("_")[0]
        data[bench_type].append(payload)
    return data


def format_throughput(rows: list[dict]) -> str:
    header = "| Batch size | Tasks/sec | Total time (s) |\n|---|---|---|"
    lines = [header]
    for r in sorted(rows, key=lambda x: x["batch_size"]):
        lines.append(
            f"| {r['batch_size']} | {r['tasks_per_sec']:.2f} | {r['total_time']:.3f} |"
        )
    return "\n".join(lines)


def format_latency(rows: list[dict]) -> str:
    header = "| Batch size | Avg latency (ms) | 95‑pct latency (ms) |\n|---|---|---|"
    lines = [header]
    for r in sorted(rows, key=lambda x: x["batch_size"]):
        lines.append(
            f"| {r['batch_size']} | {r['avg_latency_ms']:.2f} | {r['p95_latency_ms']:.2f} |"
        )
    return "\n".join(lines)


def build_report(data: dict) -> str:
    parts = ["# Benchmark Report", "", f"_Generated on {os.getenv('DATE', 'unknown')}_", ""]
    for bench, rows in data.items():
        parts.append(f"## {bench.capitalize()} benchmark")
        parts.append("")
        if bench == "throughput":
            parts.append(format_throughput(rows))
        elif bench == "latency":
            parts.append(format_latency(rows))
        else:
            parts.append("*(unknown benchmark type – raw JSON displayed)*")
            parts.append("```json")
            for r in rows:
                parts.append(json.dumps(r, indent=2))
            parts.append("```")
        parts.append("\n---\n")
    return "\n".join(parts)


def main():
    data = collect_results()
    if not data:
        print("[INFO] No benchmark data found – nothing to write")
        return
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    report_md = build_report(data)
    REPORT_PATH.write_text(report_md, encoding="utf-8")
    print(f"[INFO] Report written to {REPORT_PATH}")


if __name__ == "__main__":
    main()
