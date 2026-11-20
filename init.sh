#!/usr/bin/env bash
# init.sh — bootstrap handoff workspace (idempotent: skip files that already exist)
# Usage: bash init.sh   → prints "Workspace ready" + exit 0 when done
set -euo pipefail
cd "$(dirname "$0")"

created=()
skipped=()

track() {  # track <path> <created?1:0>
  if [ "$2" = "1" ]; then created+=("$1"); else skipped+=("$1"); fi
}

mkdir -p docs/trace-log docs/trace-log/evidence

# claude-progress.txt
if [ -e claude-progress.txt ]; then
  track "claude-progress.txt" 0
else
  cat > claude-progress.txt <<EOF
=== SESSION (fresh init) ===
Context used at end: n/a
Features in progress: (none yet)
Done (with evidence): (none yet)
Steps completed:
  - workspace initialized by init.sh
Next:
  - review features.json, pick a feature
Blockers: none
Git HEAD: $(git log --oneline -1 2>/dev/null || echo "(no commits)")
EOF
  track "claude-progress.txt" 1
fi

# todo.md
if [ -e todo.md ]; then
  track "todo.md" 0
else
  printf '# TODO\n- [ ] pick a feature from features.json\n- [ ] implement + self-verify\n- [ ] update claude-progress.txt + features.json\n' > todo.md
  track "todo.md" 1
fi

# features.json
if [ -e features.json ]; then
  track "features.json" 0
else
  printf '{\n  "project": "agent-system",\n  "version": "0.4.4",\n  "updated": "%s",\n  "features": []\n}\n' "$(date +%F)" > features.json
  track "features.json" 1
fi

# SESSION_RITUAL
if [ -e docs/SESSION_RITUAL.md ]; then
  track "docs/SESSION_RITUAL.md" 0
else
  printf '# Session Ritual\n## Khởi động\ncat claude-progress.txt todo.md\n## Kết thúc\n1. ghi claude-progress.txt\n2. cập nhật features.json (done only sau khi có evidence + commit SHA)\n3. commit\n' > docs/SESSION_RITUAL.md
  track "docs/SESSION_RITUAL.md" 1
fi

echo "init.sh: created=${#created[@]} (${created[*]:-none})"
echo "init.sh: skipped=${#skipped[@]} (${skipped[*]:-none})"
echo "Workspace ready"
