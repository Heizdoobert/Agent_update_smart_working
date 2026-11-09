import time
import pytest
from distributed_queue.task_dispatcher import TaskDispatcher


def test_dispatcher_parallel_map_reduce():
    dispatcher = TaskDispatcher(max_workers=4)
    data_chunks = list(range(1, 11))

    # Worker multiplies by 10
    def worker(val):
        return val * 10

    # Reducer sums all values
    def reducer(results):
        return sum(results)

    map_res = dispatcher.map(worker, data_chunks)
    assert len(map_res) == 10
    assert all(r["status"] == "SUCCESS" for r in map_res)

    total = dispatcher.reduce(reducer, map_res)
    assert total == sum(x * 10 for x in data_chunks)


def test_dispatcher_retry_on_transient_failure():
    dispatcher = TaskDispatcher(max_workers=2, max_retries=2, retry_delay_sec=0.01)
    attempts = {}

    def flaky_worker(val):
        attempts[val] = attempts.get(val, 0) + 1
        if attempts[val] < 2:
            raise RuntimeError("Transient network blip")
        return val * 2

    res = dispatcher.map(flaky_worker, [1, 2, 3])
    assert len(res) == 3
    # All should have succeeded on retry attempt 1
    assert all(r["status"] == "SUCCESS" for r in res)
    assert all(r["retries"] == 1 for r in res)


def test_dispatcher_fatal_failure_containment():
    dispatcher = TaskDispatcher(max_workers=2, max_retries=1, retry_delay_sec=0.01)

    def crashing_worker(val):
        if val == 999:
            raise ValueError("Corrupted poison pill")
        return val

    res = dispatcher.map(crashing_worker, [1, 999, 2])
    assert len(res) == 3
    statuses = {r["item"]: r["status"] for r in res}
    assert statuses[1] == "SUCCESS"
    assert statuses[2] == "SUCCESS"
    assert statuses[999] == "FAILED"


def test_dispatcher_order_preservation():
    dispatcher = TaskDispatcher(max_workers=4)

    # Invert completion order with variable sleeps
    def variable_sleep_worker(item):
        delay = 0.05 if item % 2 == 0 else 0.01
        time.sleep(delay)
        return item * 100

    items = list(range(10))
    res = dispatcher.map(variable_sleep_worker, items)
    assert [r["item"] for r in res] == items
    assert [r["result"] for r in res] == [x * 100 for x in items]


def test_dispatcher_circuit_breaker_on_100_percent_failure():
    dispatcher = TaskDispatcher(max_workers=2, max_retries=0)

    def fail_all_worker(item):
        raise ValueError("Intentional crash")

    map_res = dispatcher.map(fail_all_worker, [1, 2, 3])
    assert all(r["status"] == "FAILED" for r in map_res)

    with pytest.raises(RuntimeError, match="All distributed worker tasks failed; circuit breaker triggered to prevent silent data loss."):
        dispatcher.reduce(lambda x: x, map_res)

