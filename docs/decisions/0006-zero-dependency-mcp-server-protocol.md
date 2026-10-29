# ADR-006: Zero-Dependency Model Context Protocol (MCP) Server

**Status:** ACCEPTED  
**Date:** 2026-10-29  
**Deciders:** Agent System Core Team  

---

## 1. Context & Problem Statement

Modern AI developer environments (Claude Desktop, Cursor, Windsurf, Antigravity, Claude Code) natively support the **Model Context Protocol (MCP)**, an open standard created by Anthropic allowing AI agents to discover and invoke tools over a local JSON-RPC connection.

Currently, `Agent_system` provides a CLI (`agent-system <cmd>`) and Python SDK (`agent_system.*`). While CLI pipes work well in bash terminals, GUI and agentic IDEs require tools to be declared and executed via MCP. 

However, official Python MCP SDK packages (`mcp`, `pydantic-ai`, etc.) introduce dozens of external dependencies (AnyIO, Pydantic, Starlette, SSE clients), violating `Agent_system`'s **Non-Negotiable Rule 1: 100% Domain-Agnostic Standard Library with Zero External Runtime Dependencies**.

How can `Agent_system` act as a first-class MCP Server for any agentic IDE while maintaining zero third-party dependencies?

---

## 2. Decision

We implement a lightweight, pure-Python standard library **MCP Stdio Server** (`agent_system.mcp`):

1. **Protocol Implementation:**
   - Adhere to the Model Context Protocol Specification (`2024-11-05`).
   - Implement JSON-RPC 2.0 message loop reading from `sys.stdin` and writing formatted JSON lines to `sys.stdout`.
   - Direct all internal diagnostics, logging, and stderr streams to `sys.stderr` to keep `sys.stdout` pristine for JSON-RPC frames.

2. **Supported Protocol Methods:**
   - `initialize`: Returns server info (`agent-system v0.3.0`) and tool capabilities.
   - `notifications/initialized`: Notification acknowledgment.
   - `ping`: Standard latency keep-alive probe.
   - `tools/list`: Emits JSON Schema declarations for all core cognitive tools (`plan`, `critic`, `reflect`, `memory_search`, `memory_recipe`, `scan`, `init_auto`).
   - `tools/call`: Dispatches tool invocations directly to the in-memory engine and returns standardized `{"content": [{"type": "text", "text": "..."}], "isError": bool}` responses.

3. **CLI Integration:**
   - Expose the server as `agent-system mcp [--root PATH]`.
   - Compatible with Claude Desktop config (`claude_desktop_config.json`) and Cursor MCP config (`.cursor/mcp.json`).

---

## 3. Invariants & Guarantees

1. **Zero External Runtime Dependencies:** Implemented entirely via `sys`, `json`, `dataclasses`, and `typing`.
2. **Context Budget Compliance (<3KB):** Output payloads of tools like `memory_search` and `critic` remain bounded by `StructuralTruncator`.
3. **Sub-second Tool Dispatch:** In-memory execution without sub-process overhead; response times are $<5$ms per tool call.
4. **Resilience & Safe Error Handling:** Malformed JSON-RPC requests return standard JSON-RPC 2.0 error codes (`-32700 Parse error`, `-32601 Method not found`, `-32602 Invalid params`) without crashing the daemon loop.

---

## 4. Consequences

### Positive
- Universal plug-and-play capability for any MCP-compliant AI assistant (Claude Desktop, Cursor, Antigravity, Windsurf).
- Zero installation friction: users do not need to install `pip install mcp` or virtual environments.
- High performance: instantaneous tool execution directly inside the existing Python process.

### Negative
- Requires maintaining the minimal JSON-RPC 2.0 parser in `agent_system/mcp/` rather than relying on a third-party framework (well worth the isolation guarantee).
