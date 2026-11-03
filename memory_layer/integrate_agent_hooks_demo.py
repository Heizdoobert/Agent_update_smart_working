#!/usr/bin/env python3
"""
Demo integration of agent hooks.
This script shows how a typical agent task loop would call the hooks.
Replace the placeholder "agent_main_loop" with your actual agent entry point.
"""
import uuid
import time
from memory_layer.agent_hooks import pre_task_hook, post_task_hook

def agent_task(task_id: str, user_id: str, query: str) -> str:
    """Placeholder for the real agent work.
    Returns path to a temporary insight JSON file.
    """
    # Simulate some work and generate insight data
    insights = [{"insight": f"Result for {query}", "type": "demo"}]
    import json, tempfile, os
    insight_path = os.path.join(tempfile.gettempdir(), f"insights_{task_id}.json")
    with open(insight_path, "w", encoding="utf-8") as f:
        json.dump(insights, f)
    return insight_path

def main():
    # Example run loop (single iteration)
    task_id = str(uuid.uuid4())
    user_id = "demo_user"
    query = "summarize project status"

    # 1. Retrieve past insights
    past = pre_task_hook(task_id, user_id, query)
    print(f"[Hook] Retrieved {len(past)} past insights")

    # 2. Execute agent logic (placeholder)
    print("[Agent] Performing task…")
    time.sleep(0.5)
    insight_file = agent_task(task_id, user_id, query)
    print(f"[Agent] Insight file: {insight_file}")

    # 3. Store new insights
    post_task_hook(task_id, user_id, insight_file)
    print("[Hook] Insight stored.")

if __name__ == "__main__":
    main()
