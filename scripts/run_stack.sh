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
celery -A coordination_service.celery_app worker --loglevel=info &
CELERY_PID=$!

echo "[INFO] Celery worker started (PID $CELERY_PID)"

# Wait for services to be ready
sleep 5

# Run benchmarks (throughput & latency)
python3 scripts/benchmark_async_coordination.py --benchmark throughput --batch 1000
python3 scripts/benchmark_async_coordination.py --benchmark latency --batch 500

# Generate markdown report
python3 scripts/generate_report.py

# Stop background services
kill $FASTAPI_PID $CELERY_PID

echo "[INFO] Services stopped"
