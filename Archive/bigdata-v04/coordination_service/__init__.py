from celery import Celery
import os

# Build Redis URL with optional password
redis_host = os.getenv('REDIS_HOST', 'localhost')
redis_password = os.getenv('REDIS_PASSWORD')
if redis_password:
    redis_auth = f':{redis_password}@'
else:
    redis_auth = ''

broker_url = f'redis://{redis_auth}{redis_host}:6379/0'
backend_url = f'redis://{redis_auth}{redis_host}:6379/1'

celery_app = Celery(
    'coordination',
    broker=broker_url,
    backend=backend_url,
)

celery_app.conf.update(
    task_acks_late=True,
    worker_prefetch_multiplier=64,
    worker_max_tasks_per_child=10000,
    task_track_started=False,
    result_extended=False,
    result_expires=3600,
    task_time_limit=300,
    task_soft_time_limit=240,
)

# Example task for benchmarking
@celery_app.task
def echo_task(payload: dict):
    return {"status": "ok", "payload": payload}

