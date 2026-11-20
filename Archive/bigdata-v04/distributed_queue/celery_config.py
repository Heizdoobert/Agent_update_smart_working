"""
distributed_queue.celery_config
-------------------------------
Production-hardened Celery & Redis configuration for Map-Reduce & Big Data ETL.
Implements the War-Room consensus invariants to prevent task loss and duplicate runs.
"""

# 1. BROKER & QUEUE RELIABILITY
broker_url = "redis://localhost:6379/0"
result_backend = "redis://localhost:6379/1"

# CRITICAL: Prevent ghost duplicate executions on long ETL tasks
# Invariant: visibility_timeout >> task_time_limit > task_soft_time_limit
broker_transport_options = {
    "visibility_timeout": 86400,          # 24 hours (default 3600s is dangerous)
    "socket_timeout": 30.0,
    "socket_connect_timeout": 30.0,
    "socket_keepalive": True,
    "max_connections": 100,
    "health_check_interval": 15,
}

# 2. AT-LEAST-ONCE DELIVERY & OOM PROTECTION
task_acks_late = True                     # Do not ACK until task finishes execution
task_reject_on_worker_lost = True         # Requeue task if worker process is SIGKILLed/OOMed
task_acks_on_failure_or_timeout = True    # ACK if task raises handled exception or hits time limit

# CRITICAL: Stop greedy task hoarding in heavy compute workers
worker_prefetch_multiplier = 1            # 1 task per worker child at a time (fair distribution)

# 3. TIMEOUT BOUNDARIES
task_soft_time_limit = 7200               # 2 hours: raises SoftTimeLimitExceeded for clean exit
task_time_limit = 7500                    # 2 hours 5 mins: supervisor SIGKILLs child if frozen

# 4. MEMORY DEFENSE & PROACTIVE RECYCLING
worker_max_memory_per_child = 2097152     # 2 GB (in KB): Recycles worker after task if RSS > 2GB
worker_max_tasks_per_child = 50           # Recycles process after 50 tasks to purge C-extension leaks

# 5. STATE & RESULT LIFECYCLE
task_track_started = True                 # Emits 'STARTED' state event to detect hanging tasks
result_expires = 86400                    # Clean up Redis result keys after 24 hours
result_extended = True                    # Store task args/kwargs in result for RCA debugging

# 6. SERIALIZATION & SECURITY
task_serializer = "json"
accept_content = ["json"]
result_serializer = "json"
timezone = "UTC"
enable_utc = True
