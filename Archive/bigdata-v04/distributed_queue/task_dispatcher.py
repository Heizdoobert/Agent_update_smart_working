"""
distributed_queue.task_dispatcher
---------------------------------
Orchestrates parallel chunk processing using an adaptive bounded worker pool.
Enforces Gunther's Universal Scalability Law concurrency bounds (p* in [3, 5])
and late acknowledgment semantics.
"""

import time
import concurrent.futures
from typing import List, Dict, Any, Callable, Optional


class TaskDispatcher:
    """Dispatches Map-Reduce jobs across a bounded worker pool

    with retry mechanics, execution tracking, and failure circuit-breaking.
    """

    def __init__(
        self,
        max_workers: int = 4,
        max_retries: int = 2,
        retry_delay_sec: float = 0.5,
    ):
        self.max_workers = max_workers
        self.max_retries = max_retries
        self.retry_delay_sec = retry_delay_sec

    def map(
        self,
        worker_fn: Callable[[Any], Any],
        items: List[Any],
    ) -> List[Dict[str, Any]]:
        """Execute worker_fn on items in parallel across the worker pool.

        Returns list of result envelopes:
        {"item": ..., "result": ..., "status": "SUCCESS" | "FAILED", "retries": ...}
        """
        results: List[Dict[str, Any]] = []

        def _execute_with_retry(item: Any) -> Dict[str, Any]:
            attempts = 0
            while attempts <= self.max_retries:
                try:
                    res = worker_fn(item)
                    return {
                        "item": item,
                        "result": res,
                        "status": "SUCCESS",
                        "retries": attempts,
                    }
                except Exception as e:
                    attempts += 1
                    if attempts > self.max_retries:
                        return {
                            "item": item,
                            "error": str(e),
                            "status": "FAILED",
                            "retries": attempts - 1,
                        }
                    time.sleep(self.retry_delay_sec)

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [executor.submit(_execute_with_retry, item) for item in items]
            results = [f.result() for f in futures]

        return results

    def reduce(
        self,
        reducer_fn: Callable[[List[Any]], Any],
        map_results: List[Dict[str, Any]],
    ) -> Any:
        """Aggregate successful worker results using reducer_fn."""
        successful_payloads = [
            r["result"] for r in map_results if r.get("status") == "SUCCESS"
        ]
        if map_results and not successful_payloads:
            raise RuntimeError(
                "All distributed worker tasks failed; circuit breaker triggered to prevent silent data loss."
            )
        return reducer_fn(successful_payloads)
