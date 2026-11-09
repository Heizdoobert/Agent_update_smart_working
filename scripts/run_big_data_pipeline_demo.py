#!/usr/bin/env python3
"""
scripts.run_big_data_pipeline_demo
----------------------------------
End-to-End demonstration of the Production Big Data Agent Architecture:
1. Generates realistic multi-line CSV data (RFC 4180).
2. Uses QuoteAwareChunker for deterministic slicing.
3. Dispatches parallel workers via TaskDispatcher.
4. Executes bounded-memory aggregation with DuckDBWorker.
5. Aggregates metrics (Reduce Phase).
6. Ingests aggregate insight into memory_layer with SourceChunkPointer.
7. Verifies end-to-end data integrity.
"""

import os
import sys
import json
import tempfile
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from data_pipeline.chunker import QuoteAwareChunker
from data_pipeline.worker import DuckDBWorker
from distributed_queue.task_dispatcher import TaskDispatcher
from tri_modal_router import TaskDomain, route_execution_tier
from memory_layer.agent_hooks import post_task_hook, pre_task_hook


def run_demo():
    print("==================================================================")
    print("🚀 STARTING BIG DATA MAP-REDUCE & DUAL-TIER MEMORY PIPELINE DEMO")
    print("==================================================================")

    # 1. Tri-Modal Routing Check
    routing = route_execution_tier(TaskDomain.TABLE_AGGREGATION, estimated_tokens=1_000_000)
    print(f"\n[1. Router Decision] Tier: {routing['tier']} | Engine: {routing['engine']} | Cost: {routing['cost_discount']}")
    assert routing["token_cost"] == 0

    # 2. Generate Synthetic Multiline CSV Data
    tmp_dir = tempfile.gettempdir()
    csv_file = os.path.join(tmp_dir, "synthetic_reviews_dataset.csv")

    print("\n[2. Data Generation] Generating 2,000 synthetic records with multiline quotes...")
    with open(csv_file, "w", encoding="utf-8") as f:
        f.write("id,customer_id,sentiment,review_text,rating\n")
        for i in range(1, 2001):
            if i % 3 == 0:
                review = f'"Complaint #{i}:\nProduct arrived late.\nRequested partial refund."'
                sentiment = "negative"
                rating = 1
            elif i % 2 == 0:
                review = f'"Feedback #{i}:\nGood value for money."'
                sentiment = "positive"
                rating = 5
            else:
                review = f'"Review #{i}: Satisfactory experience."'
                sentiment = "neutral"
                rating = 3
            f.write(f"{i},cust_{i % 100},{sentiment},{review},{rating}\n")

    file_size_kb = os.path.getsize(csv_file) / 1024
    print(f"   Created file: {csv_file} ({file_size_kb:.2f} KB)")

    # 3. Slicing with QuoteAwareChunker
    print("\n[3. Map Phase: Splitting] Scanning file boundaries with QuoteAwareChunker...")
    chunker = QuoteAwareChunker(target_chunk_size_bytes=16 * 1024)  # 16KB chunks to force multiple partitions
    chunks = chunker.split_file(csv_file)
    header = chunker.extract_header(csv_file)
    print(f"   Generated {len(chunks)} safe chunk boundaries without RFC 4180 quote fractures.")

    # 4. Map Phase: Parallel Execution via TaskDispatcher
    print("\n[4. Worker Pool] Dispatching partitions to DuckDBWorker instances...")
    dispatcher = TaskDispatcher(max_workers=4)

    def _process_chunk(chunk_info):
        start, end, idx = chunk_info
        data = QuoteAwareChunker.read_chunk_payload(csv_file, start, end, header_bytes=header)
        worker = DuckDBWorker(max_memory_mb=128, threads=1)
        res = worker.process_csv_payload(
            data,
            """
            SELECT 
                sentiment, 
                COUNT(*) as count, 
                ROUND(AVG(rating), 2) as avg_rating 
            FROM chunk_data 
            GROUP BY sentiment
            """
        )
        worker.close()
        return {"chunk_index": idx, "summary": res}

    map_results = dispatcher.map(_process_chunk, chunks)
    print(f"   Successfully processed {len(map_results)} partitions.")
    assert all(r["status"] == "SUCCESS" for r in map_results)

    # 5. Reduce Phase: Aggregate Metrics
    print("\n[5. Reduce Phase] Aggregating partition results across all workers...")
    def _aggregate(payloads):
        totals = {}
        for p in payloads:
            for row in p["summary"]:
                sent = row["sentiment"]
                if sent not in totals:
                    totals[sent] = {"count": 0, "rating_sum": 0.0}
                totals[sent]["count"] += row["count"]
                totals[sent]["rating_sum"] += row["count"] * row["avg_rating"]
        
        final_summary = {}
        for sent, d in totals.items():
            final_summary[sent] = {
                "total_reviews": d["count"],
                "avg_rating": round(d["rating_sum"] / d["count"], 2) if d["count"] else 0.0,
            }
        return final_summary

    aggregated_metrics = dispatcher.reduce(_aggregate, map_results)
    print("   Aggregated Metrics:")
    for sent, data in aggregated_metrics.items():
        print(f"     - {sent.capitalize()}: {data['total_reviews']} reviews | Avg Rating: {data['avg_rating']}")

    total_records = sum(d["total_reviews"] for d in aggregated_metrics.values())
    assert total_records == 2000
    print(f"   Verified: Exact 2,000 / 2,000 records processed without single record loss!")

    # 6. Memory Layer Integration: Ingesting Insight with SourceChunkPointer
    print("\n[6. Memory Layer Integration] Recording condensed insight with Dual-Tier SourceChunkPointer...")
    task_id = "task_etl_reviews_001"
    user_id = "analytics_team"
    insight_file = os.path.join(tmp_dir, "etl_insight_output.json")

    insight_payload = [{
        "insight": f"Customer sentiment breakdown: {aggregated_metrics['negative']['total_reviews']} negative complaints (Avg {aggregated_metrics['negative']['avg_rating']}/5.0). Prompt refund automation required.",
        "type": "core_knowledge",
        "priority": "high",
        "source_pointer": {
            "storage_uri": f"s3://datalake/raw/synthetic_reviews_dataset.csv",
            "file_path": csv_file,
            "chunk_count": len(chunks),
            "total_records": 2000,
            "git_commit_sha": os.getenv("GIT_COMMIT_SHA", "HEAD"),
        }
    }]
    with open(insight_file, "w", encoding="utf-8") as f:
        json.dump(insight_payload, f)

    post_task_hook(task_id, user_id, insight_file)
    print("   Stored in Milvus Lite via post_task_hook. Insight file cleanly unlinked.")

    # 7. Verification: Retrieve via pre_task_hook
    print("\n[7. Verification] Querying memory_layer via pre_task_hook...")
    retrieved = pre_task_hook(task_id, user_id, "complaints refund", k=1)
    assert len(retrieved) >= 1
    found = retrieved[0]
    print(f"   Retrieved Content: {found['content']}")
    print(f"   Retrieved Source Pointer: {found['source_pointer']}")
    assert found["source_pointer"]["total_records"] == 2000

    # Cleanup
    if os.path.exists(csv_file):
        os.remove(csv_file)

    print("\n==================================================================")
    print("✅ END-TO-END BIG DATA MAP-REDUCE & MEMORY INTEGRATION: ALL PASSED!")
    print("==================================================================")


if __name__ == "__main__":
    run_demo()
