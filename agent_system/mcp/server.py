"""Zero-dependency Model Context Protocol (MCP) JSON-RPC 2.0 stdio server."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional, TextIO

from agent_system import __version__
from agent_system.mcp.tools import CognitiveToolsDispatcher

PROTOCOL_VERSION = "2024-11-05"


def _json_result(req_id: Any, result: Any) -> str:
    """Format standard JSON-RPC 2.0 success response string."""
    return json.dumps({"jsonrpc": "2.0", "id": req_id, "result": result})


def _json_error(req_id: Any, code: int, message: str) -> str:
    """Format standard JSON-RPC 2.0 error response string."""
    return json.dumps({"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}})


class MCPServer:
    """Compliant Model Context Protocol stdio server implemented with pure standard library."""

    def __init__(
        self,
        root_path: str | Path = ".",
        stdin: Optional[TextIO] = None,
        stdout: Optional[TextIO] = None,
        stderr: Optional[TextIO] = None,
    ) -> None:
        self.root_path = Path(root_path).resolve()
        self.stdin = stdin or sys.stdin
        self.stdout = stdout or sys.stdout
        self.stderr = stderr or sys.stderr
        self.tools = CognitiveToolsDispatcher(root_path=self.root_path)

    def handle_message(self, message_str: str) -> Optional[str]:
        """Process incoming JSON-RPC 2.0 message and return JSON-RPC response or None."""
        if not message_str or not message_str.strip():
            return None

        try:
            req: Dict[str, Any] = json.loads(message_str)
        except (json.JSONDecodeError, ValueError) as err:
            return _json_error(None, -32700, f"Parse error: {str(err)}")

        if not isinstance(req, dict):
            return _json_error(None, -32600, "Invalid Request: expected JSON object")

        req_id = req.get("id")
        method = req.get("method", "")
        params = req.get("params", {})

        # Handle notifications (requests without 'id')
        if req_id is None:
            if method == "notifications/initialized":
                self._log("Client completed MCP initialization.")
            return None

        # Standard JSON-RPC 2.0 / MCP Methods
        if method == "initialize":
            return _json_result(
                req_id,
                {
                    "protocolVersion": PROTOCOL_VERSION,
                    "capabilities": {"tools": {}},
                    "serverInfo": {
                        "name": "agent-system",
                        "version": __version__,
                    },
                },
            )

        elif method == "ping":
            return _json_result(req_id, {})

        elif method == "tools/list":
            return _json_result(req_id, {"tools": self.tools.get_tool_definitions()})

        elif method == "tools/call":
            tool_name = params.get("name", "")
            arguments = params.get("arguments", {})
            try:
                content_text = self.tools.dispatch(tool_name, arguments)
                return _json_result(
                    req_id,
                    {"content": [{"type": "text", "text": content_text}], "isError": False},
                )
            except Exception as exc:
                return _json_result(
                    req_id,
                    {
                        "content": [
                            {"type": "text", "text": f"Error executing tool '{tool_name}': {str(exc)}"}
                        ],
                        "isError": True,
                    },
                )

        else:
            return _json_error(req_id, -32601, f"Method not found: '{method}'")

    def run_stdio(self) -> None:
        """Main stdio loop reading JSON-RPC lines from stdin and writing to stdout."""
        self._log(f"agent-system MCP Server v{__version__} listening on stdio...")
        while True:
            try:
                line = self.stdin.readline()
                if not line:
                    break
                response = self.handle_message(line)
                if response:
                    self.stdout.write(response + "\n")
                    self.stdout.flush()
            except (KeyboardInterrupt, EOFError):
                break
            except Exception as e:
                self._log(f"Unexpected error in MCP stdio loop: {e}")

    def _log(self, message: str) -> None:
        """Log diagnostic messages exclusively to stderr to protect stdout JSON-RPC stream."""
        self.stderr.write(f"[agent-system:mcp] {message}\n")
        self.stderr.flush()
