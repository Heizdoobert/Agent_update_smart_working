#!/usr/bin/env bash
set -euo pipefail

# Activate virtualenv if present
if [ -d "./venv" ]; then
  source ./venv/bin/activate
else
  echo "[WARN] No virtualenv – using system Python"
fi

# Load .env variables
if [ -f ".env" ]; then
  export $(grep -v '^#' .env | xargs)
fi

# Start FastAPI in background
uvicorn coordination_service.main:app --host 0.0.0.0 --port 8000 &
FASTAPI_PID=$!

echo "[INFO] FastAPI started (PID $FASTAPI_PID)"

# Start Celery worker in background
celery -A coordination_service.celery_app worker --loglevel=info --concurrency=4 &
CELERY_PID=$!

echo "[INFO] Celery worker started (PID $CELERY_PID)"

# Wait for services to be ready
sleep 5

# Collect resource usage via ps
echo "[INFO] Resource usage:"
ps -p $FASTAPI_PID -o pid,pcpu,rss,command
ps -p $CELERY_PID -o pid,pcpu,rss,command

# Run latency benchmarks first on clean queue
echo "[INFO] Running latency benchmarks..."
python3 scripts/benchmark_async_coordination.py --benchmark latency --batch 1000
python3 scripts/benchmark_async_coordination.py --benchmark latency --batch 4000

sleep 2

# Run throughput benchmarks
echo "[INFO] Running throughput benchmarks..."
python3 scripts/benchmark_async_coordination.py --benchmark throughput --batch 20000
python3 scripts/benchmark_async_coordination.py --benchmark throughput --batch 40000

# Generate markdown report
python3 scripts/generate_report.py

# Stop background services
kill $FASTAPI_PID $CELERY_PID

echo "[INFO] Services stopped"
