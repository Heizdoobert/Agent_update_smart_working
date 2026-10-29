"""Unit tests for agent_system.mcp.server and tools."""
import json
import pytest

from agent_system.mcp.server import MCPServer
from agent_system.mcp.tools import CognitiveToolsDispatcher


def test_mcp_handshake_and_ping():
    server = MCPServer()

    # 1. Initialize
    init_req = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test-client", "version": "1.0.0"},
        },
    }
    resp_str = server.handle_message(json.dumps(init_req))
    assert resp_str is not None
    resp = json.loads(resp_str)
    assert resp["id"] == 1
    assert resp["result"]["protocolVersion"] == "2024-11-05"
    assert resp["result"]["serverInfo"]["name"] == "agent-system"
    assert "tools" in resp["result"]["capabilities"]

    # 2. Initialized notification (no response)
    notif_req = {"jsonrpc": "2.0", "method": "notifications/initialized"}
    assert server.handle_message(json.dumps(notif_req)) is None

    # 3. Ping
    ping_req = {"jsonrpc": "2.0", "id": 2, "method": "ping"}
    resp_ping = json.loads(server.handle_message(json.dumps(ping_req)))
    assert resp_ping["id"] == 2
    assert resp_ping["result"] == {}


def test_mcp_tools_list():
    server = MCPServer()
    list_req = {"jsonrpc": "2.0", "id": 10, "method": "tools/list"}
    resp = json.loads(server.handle_message(json.dumps(list_req)))
    assert resp["id"] == 10
    tools = resp["result"]["tools"]
    tool_names = [t["name"] for t in tools]

    assert "agent_plan" in tool_names
    assert "agent_critic" in tool_names
    assert "agent_reflect" in tool_names
    assert "agent_memory_search" in tool_names
    assert "agent_scan" in tool_names
    assert "agent_init_auto" in tool_names

    # Check schema structure of agent_critic
    critic_tool = next(t for t in tools if t["name"] == "agent_critic")
    assert "inputSchema" in critic_tool
    assert "code" in critic_tool["inputSchema"]["properties"]


def test_mcp_tools_call_critic_and_reflect():
    server = MCPServer()

    # Tool call: agent_critic
    critic_req = {
        "jsonrpc": "2.0",
        "id": 20,
        "method": "tools/call",
        "params": {
            "name": "agent_critic",
            "arguments": {
                "code": "def valid_func():\n    return 42\n",
                "language": "python",
            },
        },
    }
    resp = json.loads(server.handle_message(json.dumps(critic_req)))
    assert resp["id"] == 20
    assert resp["result"]["isError"] is False
    content_text = resp["result"]["content"][0]["text"]
    assert "PASS" in content_text

    # Tool call: agent_reflect
    reflect_req = {
        "jsonrpc": "2.0",
        "id": 21,
        "method": "tools/call",
        "params": {
            "name": "agent_reflect",
            "arguments": {
                "code": "import pdb\ndef fn(): pass\n",
                "max_iterations": 2,
            },
        },
    }
    resp_ref = json.loads(server.handle_message(json.dumps(reflect_req)))
    assert resp_ref["id"] == 21
    ref_text = resp_ref["result"]["content"][0]["text"]
    assert "# [Self-Reflection" in ref_text


def test_mcp_tools_call_plan():
    server = MCPServer()
    plan_req = {
        "jsonrpc": "2.0",
        "id": 30,
        "method": "tools/call",
        "params": {
            "name": "agent_plan",
            "arguments": {
                "initial": {"state_a": True, "state_b": False},
                "goal_key": "state_b",
                "goal_value": True,
                "actions": [
                    {
                        "name": "transform_a_to_b",
                        "cost": 1.0,
                        "preconditions": {"state_a": True},
                        "effects": {"state_b": True},
                    }
                ],
                "method": "astar",
            },
        },
    }
    resp = json.loads(server.handle_message(json.dumps(plan_req)))
    assert resp["id"] == 30
    assert resp["result"]["isError"] is False
    plan_text = resp["result"]["content"][0]["text"]
    assert "transform_a_to_b" in plan_text


def test_mcp_error_handling_parse_error_and_method_not_found():
    server = MCPServer()

    # Malformed JSON
    resp_parse = json.loads(server.handle_message("not valid json {"))
    assert resp_parse["error"]["code"] == -32700

    # Unknown method
    unknown_req = {"jsonrpc": "2.0", "id": 99, "method": "non_existent_method"}
    resp_unknown = json.loads(server.handle_message(json.dumps(unknown_req)))
    assert resp_unknown["error"]["code"] == -32601

    # Unknown tool in tools/call
    unknown_tool = {
        "jsonrpc": "2.0",
        "id": 100,
        "method": "tools/call",
        "params": {"name": "ghost_tool", "arguments": {}},
    }
    resp_tool = json.loads(server.handle_message(json.dumps(unknown_tool)))
    assert resp_tool["result"]["isError"] is True
    assert "Unknown tool" in resp_tool["result"]["content"][0]["text"]
