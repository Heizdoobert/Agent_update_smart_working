# Quickstart — Install & Use

All commands verified against the CLI (`agent-system <cmd> --help`).

## 1. Install

Requirement: **Python 3.14+** (floor).

```bash
# clone
git clone https://github.com/Heizdoobert/Agent_update_smart_working.git
cd Agent_update_smart_working

# venv
python3.14 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# install
pip install -e ".[embed]"          # [embed] = fastembed vectors. Drop it for BM25-only
agent-system doctor                # verify: DB, embeddings, MCP clients, flow-task bridge
```

No runtime dependencies — the package installs clean on any 3.14 interpreter.

## 2. Wire into an AI client (pick one)

```bash
agent-system install --dry-run                 # preview what will change
agent-system install --target claude           # Claude Desktop
agent-system install --target cursor           # Cursor
agent-system install --target windsurf         # Windsurf
agent-system install --target antigravity      # Antigravity
agent-system install --target mcp              # MCP server registration only
agent-system install --target rules            # Universal System Instruction only
agent-system install --print-instruction       # print the instruction block, write nothing
```

- `install` writes a **marked block** (`<!-- agent-system:begin -->`) into client config. Rest of the file untouched. Re-run = update block, never clobber.
- Claude Code CLI alternative: `claude mcp add agent-system -- agent-system mcp`

Env vars (optional):

| Var | Effect |
|---|---|
| `AGENT_SYSTEM_DB_DIR` | Move the DB (default `~/.agent_system/agent_system.db`) |
| `AGENT_SYSTEM_NO_EMBED=1` | Force BM25, no vector model |
| `AGENT_SYSTEM_LLM_PATCH=1` | `reflect` may call a cheap Claude model for repairs the rule-patcher can't make |

## 3. Use it — daily commands

### See what is registered
```bash
agent-system doctor          # health of everything
agent-system skill list      # registered skills
agent-system session list    # active sessions
agent-system metrics         # KPI dashboard (context %, KV-cache, retry ceiling)
agent-system metrics --json  # machine-readable
```

### Plan (A* = deterministic, MCTS = sampled)
```bash
# initial state + goal as JSON
echo '{"is_ready": false, "tests_green": false}' > state.json
agent-system plan --initial state.json --goal-key is_ready --method astar
agent-system plan --initial state.json --goal-key is_ready --method mcts --simulations 200
```

### Critic (static audit of an artifact)
```bash
agent-system critic --file out.py                     # language auto-detected
agent-system critic --file out.py --strict            # require type annotations
agent-system critic --file spec.md --language markdown
cat code.txt | agent-system critic --file -           # stdin
```

### Reflect (critic + auto-repair loop, max 5 rounds)
```bash
agent-system reflect --file buggy.py
agent-system reflect --file buggy.py --output-code    # print only the repaired code
```

### Memory
```bash
agent-system memory index --id doc1 --content "text..." --category notes
agent-system memory search --query "note about db" --top-k 3
agent-system memory recipe-record --key FORBIDDEN_CALL --recipe "replace eval with ast check"
agent-system memory recipe-get --key FORBIDDEN_CALL
```

### Skills & sessions
```bash
agent-system skill get --name <name>
agent-system skill inject --names <name1,name2>   # bounded prompt context (--max-bytes <3KB)
agent-system session set --id s1 --key k --value v
agent-system session get --id s1
agent-system session delete --id s1
```

### Bootstrap a new project
```bash
agent-system init --auto --root /path/to/project   # scan + init, no prompts
agent-system scan --root /path/to/project          # scan only
agent-system scan --root . --json                  # machine-readable manifest
```

## 4. The loop (what actually runs)

```
plan  ->  execute  ->  critic  ->  (score < 100)  ->  reflect  ->  critic  ...  (<=5 rounds)  ->  output
```

Every output passes the Critic before delivery. `reflect` repairs what the critic rejects, up to 5 rounds, then stops and reports.

## 5. Smoke test (60 seconds)

```bash
agent-system doctor && agent-system metrics && agent-system skill list
echo 'import os
x = eval("1+1")' > /tmp/bad.py
agent-system reflect --file /tmp/bad.py --output-code
# expect: repaired code without eval
```

## 6. Test

```bash
pytest tests/          # 167 passed (Python 3.14)
```
