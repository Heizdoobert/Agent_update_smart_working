"""End-to-End integration test for agent-system MCP stdio server."""
import json
import subprocess
import sys
import tempfile
from pathlib import Path
import pytest


def test_mcp_server_stdio_e2e():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        (tmppath / "pyproject.toml").write_text('[project]\nname = "e2e_mcp"\n')

        # Launch agent-system mcp as a subprocess
        cmd = [
            sys.executable,
            "-m",
            "agent_system.cli.main",
            "mcp",
            "--root",
            str(tmppath),
        ]
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )

        try:
            # 1. Send initialize
            init_msg = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "test-e2e-client", "version": "1.0"},
                },
            }
            proc.stdin.write(json.dumps(init_msg) + "\n")
            proc.stdin.flush()

            init_line = proc.stdout.readline()
            assert init_line, "Expected JSON-RPC response from MCP server"
            init_resp = json.loads(init_line)
            assert init_resp["id"] == 1
            assert init_resp["result"]["protocolVersion"] == "2024-11-05"
            assert init_resp["result"]["serverInfo"]["name"] == "agent-system"

            # 2. Send notifications/initialized
            proc.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n")
            proc.stdin.flush()

            # 3. Send ping
            proc.stdin.write(json.dumps({"jsonrpc": "2.0", "id": 2, "method": "ping"}) + "\n")
            proc.stdin.flush()

            ping_line = proc.stdout.readline()
            ping_resp = json.loads(ping_line)
            assert ping_resp["id"] == 2
            assert ping_resp["result"] == {}

            # 4. Call agent_scan tool
            scan_call = {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": "agent_scan",
                    "arguments": {"root": str(tmppath)},
                },
            }
            proc.stdin.write(json.dumps(scan_call) + "\n")
            proc.stdin.flush()

            scan_line = proc.stdout.readline()
            scan_resp = json.loads(scan_line)
            assert scan_resp["id"] == 3
            assert scan_resp["result"]["isError"] is False
            content = scan_resp["result"]["content"][0]["text"]
            assert "Python" in content
            assert "pyproject.toml" in content

        finally:
            proc.stdin.close()
            proc.wait(timeout=3)
            assert proc.returncode == 0
