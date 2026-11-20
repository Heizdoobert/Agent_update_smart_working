#!/usr/bin/env bash
# verify_cli.sh — E2E CLI verification, captures evidence to docs/trace-log/evidence/
# Exits non-zero on ANY failed check. Prints "EVIDENCE CAPTURED" at the end.
#
# HARDENING (learned from TR-20261120: a command can exit 0 but produce no output,
# e.g. a mis-formatted plan that still returns 0 in some paths): a check only PASSes
# when the command exits 0 AND produced non-empty output. Empty output => FAIL.
set -uo pipefail
cd "$(dirname "$0")/../.."

EV=docs/trace-log/evidence
mkdir -p "$EV"
PASS=0; FAIL=0

run() {
  local name="$1"; shift
  local out="$EV/$name.log"
  local rc=0
  {
    echo "\$ $*"
    echo "----"
  } > "$out"
  "$@" >> "$out" 2>&1 || rc=$?
  # non-empty body after the header (ignore the 2 header lines)
  local body_lines
  body_lines=$(tail -n +3 "$out" | grep -c '[^[:space:]]' || true)
  if [ "$rc" -eq 0 ] && [ "${body_lines:-0}" -gt 0 ]; then
    echo "  PASS  $name"
    PASS=$((PASS+1))
  else
    echo "  FAIL  $name  (rc=$rc, body_lines=${body_lines:-0}, see $out)"
    FAIL=$((FAIL+1))
  fi
}

PY=(.venv/bin/python -m agent_system.cli.main)

# 1. help — CLI boots, prints usage
run "01_help" "${PY[@]}" --help

# 2. doctor — health report (memory DB, embeddings, mcp, flow-bridge)
run "02_doctor" "${PY[@]}" doctor

# 3. skill list — skill discovery
run "03_skill_list" "${PY[@]}" skill list

# 4. session list — session store
run "04_session_list" "${PY[@]}" session list

# 5. critic — audit a markdown artifact (expect real score output)
printf '# Verification artifact\n\nThis file is used by verify_cli.sh to exercise the critic pipeline.\n' > "$EV/sample_artifact.md"
run "05_critic" "${PY[@]}" critic --file "$EV/sample_artifact.md" --language markdown

# 6. plan — A* over a 2-state transition.
#    ActionDefinition uses FLAT state + "preconditions"/"effects" (NOT pre/post).
printf '{"pos": 0}' > "$EV/plan_initial.json"
printf '[{"name": "move", "cost": 1, "preconditions": {"pos": 0}, "effects": {"pos": 1}}]' > "$EV/plan_actions.json"
run "06_plan_astar" "${PY[@]}" plan --initial "$EV/plan_initial.json" --actions "$EV/plan_actions.json" --goal-key pos --goal-value 1 --method astar

echo
echo "===================="
echo "verify_cli: PASS=$PASS FAIL=$FAIL"
echo "evidence dir: $EV/"
ls -1 "$EV"/*.log 2>/dev/null
echo "===================="

if [ "$FAIL" -gt 0 ]; then
  echo "RESULT: FAILED"
  exit 1
fi
echo "EVIDENCE CAPTURED"
echo "RESULT: PASS"
