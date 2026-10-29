# Spec: Zero-Dependency Model Context Protocol (MCP) Server

## 1. Objective

Expose the entire `Agent_system` cognitive engine as a compliant **Model Context Protocol (MCP)** server over standard I/O (`stdio`). This allows AI Agent tools (Claude Desktop, Cursor, Antigravity, Windsurf) to natively list and invoke cognitive capabilities (`plan`, `critic`, `reflect`, `memory_search`, `memory_recipe`, `scan`, `init_auto`) with zero third-party dependencies.

---

## 2. Tech Stack & Invariants

- **Language:** Python 3.9+ (100% Standard Library: `json`, `sys`, `dataclasses`, `typing`, `pathlib`).
- **Protocol:** JSON-RPC 2.0 / MCP Protocol Version `2024-11-05` over `stdio`.
- **Runtime Dependencies:** Zero (`pip install mcp` NOT required).
- **Context Budget:** Text content in tool outputs is strictly bounded by `StructuralTruncator` (<3KB).

---

## 3. Architecture & Protocol Handling

```
AI Agent (Claude / Cursor / Windsurf)
          │
      (stdio) JSON-RPC 2.0
          ▼
agent_system.mcp.server.MCPServer
          │
     ┌────┴───────────────────────────┐
     ▼                                ▼
Protocol Handler (JSON-RPC)     Tools Dispatcher
  - initialize                    - agent_plan
  - notifications/initialized     - agent_critic
  - ping                          - agent_reflect
  - tools/list                    - agent_memory_search
  - tools/call                    - agent_scan
                                  - agent_init_auto
```

### JSON-RPC 2.0 Frame Schema

```json
// Request
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "agent_memory_search",
    "arguments": {
      "query": "deployment instructions",
      "top_k": 3
    }
  }
}

// Response
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "Found 1 memory:\n[README.md > Deployment Guide]..."
      }
    ],
    "isError": false
  }
}
```

---

## 4. Exposed Tools Schema

1. `agent_plan`:
   - `initial` (object, required): Initial state key-values.
   - `goal_key` (string, required): Key in state marking goal completion.
   - `goal_value` (any, optional, default `true`): Expected value of goal key.
   - `method` (string, optional: `"astar"` or `"mcts"`, default `"astar"`).
   - `actions` (array of objects, optional): Custom action definitions if not using project plugin.

2. `agent_critic`:
   - `code` (string, required): Code artifact or configuration text to audit.
   - `language` (string, optional: `"python"` | `"json"` | `"text"`, default `"python"`).
   - `strict` (boolean, optional, default `false`): Require full type annotations.

3. `agent_reflect`:
   - `code` (string, required): Python code to audit and self-patch in memory.
   - `max_iterations` (integer, optional, default `3`): Max repair loop count ($\le 5$).

4. `agent_memory_search`:
   - `query` (string, required): Search query string.
   - `category` (string, optional): Memory category filter.
   - `top_k` (integer, optional, default `3`): Max result count.

5. `agent_memory_recipe_record`:
   - `key` (string, required): Error or issue identifier.
   - `recipe` (string, required): Solution / recovery steps.

6. `agent_memory_recipe_get`:
   - `key` (string, required): Error or issue identifier.

7. `agent_scan`:
   - `root` (string, optional, default `"."`): Root directory of target repository.

8. `agent_init_auto`:
   - `root` (string, optional, default `"."`): Root directory to auto-scaffold and ingest.

---

## 5. Commands & Configuration

```bash
# Start MCP server via CLI
python3 -m agent_system.cli.main mcp

# Or via installed binary
agent-system mcp --root /path/to/project
```

### Configuration in Claude Desktop (`~/.config/Claude/claude_desktop_config.json`)
```json
{
  "mcpServers": {
    "agent-system": {
      "command": "agent-system",
      "args": ["mcp"]
    }
  }
}
```

---

## 6. Testing Strategy

1. **Unit Tests (`tests/test_mcp_server.py`):**
   - Test JSON-RPC 2.0 handshake (`initialize`, `notifications/initialized`, `ping`).
   - Test `tools/list` schema accuracy.
   - Test `tools/call` for every registered tool with valid and invalid parameters.
   - Test error handling (`-32700 Parse error`, `-32601 Method not found`).
2. **Integration Tests (`tests/test_mcp_e2e.py`):**
   - End-to-end stdio subprocess piping test simulating an MCP client speaking to `agent-system mcp`.

---

## 7. Success Criteria

1. [ ] Protocol compliance: Zero errors across standard JSON-RPC 2.0 calls.
2. [ ] Zero external dependencies: Only Python standard library imports.
3. [ ] All 8 cognitive tools are fully functional through `tools/call`.
4. [ ] 100% of test suite passes.
