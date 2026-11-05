#!/usr/bin/env bash
set -euo pipefail

# Log file location (home directory)
LOG="$HOME/system_monitor.log"

timestamp() { date '+%Y-%m-%d %H:%M:%S'; }

{
  echo "=== $(timestamp) Monitoring report ==="

  echo "[Redis]"
  if /usr/bin/redis-cli ping | grep -q PONG; then
    echo "Redis: OK"
  else
    echo "Redis: NOT reachable"
  fi

  echo "[Celery Worker]"
  if pgrep -f "coordination_service.celery_app worker" > /dev/null; then
    echo "Celery worker: running (PID $(pgrep -f "celery -A coordination_service.celery_app worker"))"
  else
    echo "Celery worker: NOT running"
  fi

  echo "[Antigravity MCP]"
  if pgrep -f "agy mcp" > /dev/null; then
    echo "Antigravity MCP: running (PID $(pgrep -f "agy mcp"))"
  else
    echo "Antigravity MCP: NOT running"
  fi

  echo "=== End of report ==="
} >> "$LOG"

# Optional: notify via stdout for interactive runs
cat "$LOG"
