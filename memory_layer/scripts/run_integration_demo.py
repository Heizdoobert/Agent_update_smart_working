#!/usr/bin/env python3
"""
Integration Demo for Knowledge System
-----------------------------------
Simulates a single agent task cycle:
1. Pre‑task hook retrieves past insights.
2. Agent "does work" (dummy placeholder).
3. Generates a temporary insight JSON file.
4. Post‑task hook stores the insight.
5. Verifies that the insight can be retrieved.
"""
import json
import os
import tempfile
import time
from pathlib import Path

from memory_layer.agent_hooks import pre_task_hook, post_task_hook

def simulate_task(task_id: str, user_id: str, query: str) -> str:
    """Placeholder for agent logic. Returns path to a temporary insight file."""
    # Create dummy insight data
    insights = [
        {"insight": f"Result of {query}", "type": "demo"},
    ]
    insight_path = Path(tempfile.gettempdir()) / f"insights_{task_id}.json"
    insight_path.write_text(json.dumps(insights), encoding="utf-8")
    return str(insight_path)

def main():
    task_id = "demo001"
    user_id = "demo_user"
    query = "summarize recent experiment results"

    print("[Demo] Pre‑task hook retrieving insights...")
    prior = pre_task_hook(task_id, user_id, query)
    print(f"[Demo] Retrieved {len(prior)} prior insights.")

    print("[Demo] Simulating task execution...")
    time.sleep(0.5)  # simulate work
    insight_file = simulate_task(task_id, user_id, query)
    print(f"[Demo] Insight file created at {insight_file}")

    print("[Demo] Post‑task hook storing insights...")
    post_task_hook(task_id, user_id, insight_file)

    print("[Demo] Verifying stored insight can be retrieved...")
    later = pre_task_hook(task_id, user_id, query)
    print(f"[Demo] Retrieved {len(later)} insights after storage.")
    for i, ins in enumerate(later, 1):
        print(f"  {i}: {ins.get('content')}")

if __name__ == "__main__":
    main()
