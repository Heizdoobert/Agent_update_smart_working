#!/usr/bin/env bash
# war_room_init.sh: Helper CLI for managing Agile Sprints and War-Room State in agent-system session

set -euo pipefail

CMD="${1:-help}"
TASK_ID="${2:-default_task}"

check_cli() {
  if ! command -v agent-system &> /dev/null; then
    echo "ERROR: 'agent-system' CLI is not found in PATH." >&2
    exit 1
  fi
}

case "$CMD" in
  init)
    check_cli
    echo "Initializing task session: $TASK_ID"
    agent-system session set --id "$TASK_ID" --key "sprint" --value "1"
    agent-system session set --id "$TASK_ID" --key "status" --value "SPRINT_ACTIVE"
    agent-system session set --id "$TASK_ID" --key "qa_failures" --value "None"
    echo "Task $TASK_ID initialized at Sprint 1."
    ;;

  next-sprint)
    check_cli
    FAIL_MSG="${3:-Unknown failure}"
    CURRENT_SPRINT=$(agent-system session get --id "$TASK_ID" | grep -oP '"sprint":\s*"?\K[0-9]+' || echo "1")
    NEXT_SPRINT=$((CURRENT_SPRINT + 1))

    if [ "$NEXT_SPRINT" -le 3 ]; then
      echo "Advancing task $TASK_ID to Sprint $NEXT_SPRINT"
      agent-system session set --id "$TASK_ID" --key "sprint" --value "$NEXT_SPRINT"
      agent-system session set --id "$TASK_ID" --key "status" --value "SPRINT_ACTIVE"
      agent-system session set --id "$TASK_ID" --key "qa_failures" --value "$FAIL_MSG"
      echo "Sprint $NEXT_SPRINT active. Diagnostics updated."
    else
      echo "Sprint limit (3) exceeded for task $TASK_ID! Escalating to War-Room."
      agent-system session set --id "$TASK_ID" --key "status" --value "WAR_ROOM_REQUIRED"
      agent-system session set --id "$TASK_ID" --key "qa_failures" --value "$FAIL_MSG"
      echo "STATUS: WAR_ROOM_REQUIRED. Halting individual sprints."
    fi
    ;;

  war-room)
    check_cli
    echo "Activating Emergency War-Room for task: $TASK_ID"
    agent-system session set --id "$TASK_ID" --key "status" --value "WAR_ROOM_ACTIVE"
    echo "State locked to WAR_ROOM_ACTIVE."
    ;;

  pass)
    check_cli
    echo "Marking task $TASK_ID as QA_PASSED"
    agent-system session set --id "$TASK_ID" --key "status" --value "QA_PASSED"
    ;;

  status)
    check_cli
    echo "--- Current State for Task: $TASK_ID ---"
    agent-system session get --id "$TASK_ID"
    ;;

  help|*)
    echo "Usage: $0 {init|next-sprint|war-room|pass|status} <task_id> [failure_diagnostic]"
    echo ""
    echo "Commands:"
    echo "  init <task_id>                     Start new task at Sprint 1"
    echo "  next-sprint <task_id> <diagnostic> Increment sprint count (Max 3) or trigger War-Room"
    echo "  war-room <task_id>                 Lock state to WAR_ROOM_ACTIVE"
    echo "  pass <task_id>                     Record 100% QA pass"
    echo "  status <task_id>                   View current session data"
    exit 0
    ;;
esac
