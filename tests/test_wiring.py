"""Installer safety, doctor and the flow-task bridge."""

from __future__ import annotations

import json
import os
import stat
import sys
from pathlib import Path

from agent_system import doctor, flow
from agent_system.mcp.tools import CognitiveToolsDispatcher
from agent_system.sdk.installer import RULES_BEGIN, RULES_END, write_managed_block


def test_managed_block_keeps_user_text_and_is_idempotent(tmp_path):
    f = tmp_path / "CLAUDE.md"
    f.write_text("# mine\nkeep this\n", encoding="utf-8")
    write_managed_block(f, "rule v1")
    write_managed_block(f, "rule v2")
    out = f.read_text(encoding="utf-8")
    assert "keep this" in out and "rule v2" in out and "rule v1" not in out
    assert out.count(RULES_BEGIN) == 1 and out.count(RULES_END) == 1


def _fake_flow(tmp_path, monkeypatch):
    if sys.platform == "win32":  # fake launcher is a POSIX shell script
        return None
    exe = tmp_path / "flow-task"
    exe.write_text('#!/bin/sh\necho "ran: $@"\n')
    exe.chmod(exe.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("FLOW_TASK_BIN", str(exe))
    return exe


def test_flow_tools_call_flow_task(tmp_path, monkeypatch):
    if not _fake_flow(tmp_path, monkeypatch):
        return
    d = CognitiveToolsDispatcher(root_path=tmp_path)
    assert d.dispatch("flow_task_submit", {"message": "do x"}) == "ran: enqueue do x"
    assert d.dispatch("flow_task_status", {"task_id": "42"}) == "ran: status 42"
    assert d.dispatch("flow_task_submit", {"message": " "}).startswith("error")


def test_flow_missing_is_a_message_not_a_crash(monkeypatch, tmp_path):
    monkeypatch.delenv("FLOW_TASK_BIN", raising=False)
    monkeypatch.setattr(flow, "find", lambda: None)
    assert flow.run("status", "1").startswith("error: flow-task not installed")


def test_doctor_reports_core_checks(monkeypatch, tmp_path):
    monkeypatch.setenv("AGENT_SYSTEM_DB_DIR", str(tmp_path))
    rep = doctor.run()
    names = {c["name"] for c in rep["checks"]}
    assert {"python", "memory-db", "embeddings", "mcp-clients", "flow-task"} <= names
    assert rep["ok"] is True
    json.dumps(rep)
    assert "memory-db" in doctor.render(rep)


def test_flow_plan_tools_pass_goal_model_and_ids(tmp_path, monkeypatch):
    if not _fake_flow(tmp_path, monkeypatch):
        return
    d = CognitiveToolsDispatcher(root_path=tmp_path)
    assert d.dispatch("flow_plan_create", {"goal": "build x", "model": "gpt-oss-120b-medium"}) == "ran: plan build x --model gpt-oss-120b-medium"
    assert d.dispatch("flow_plan_create", {"goal": "build x"}) == "ran: plan build x"
    assert d.dispatch("flow_plan_approve", {"plan_id": "p1"}) == "ran: approve p1"
    assert d.dispatch("flow_plan_status", {"plan_id": "p1"}) == "ran: status p1"
    assert d.dispatch("flow_plan_create", {"goal": " "}).startswith("error")
