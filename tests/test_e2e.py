"""End-to-End Integration Test for Cognitive Agent Workflow."""

import tempfile
import time
from pathlib import Path
import pytest

from agent_system.core.contracts import ActionStep, TaskGoal, TraceRecord
from agent_system.core.session import SessionManager
from agent_system.memory.episodic import EpisodicMemory
from agent_system.memory.scratchpad import WorkingScratchpad
from agent_system.memory.semantic import SemanticMemory
from agent_system.reasoning.astar import AStarPlanner
from agent_system.reasoning.transition import ActionDefinition, StateMachineTransitionModel, StateNode
from agent_system.reflection.adapters.python_ast import PythonAstCritic
from agent_system.reflection.critic import CriticEngine
from agent_system.reflection.reflector import SelfReflector
from agent_system.skills.registry import SkillRegistry
from agent_system.storage.sqlite_store import SQLiteStore


def test_full_cognitive_agent_e2e():
    """Simulate complete intelligent agent loop:

    Skill Injection -> A* Planning -> Self-Reflection -> Memory Recording -> Semantic Search
    """
    total_start = time.time()

    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        db_path = root / "e2e_agent.db"
        store = SQLiteStore(db_path)

        # 1. Dynamic Skill Registry
        skills_dir = root / "skills"
        skill_a = skills_dir / "audit"
        skill_a.mkdir(parents=True)
        (skill_a / "SKILL.md").write_text(
            """---
name: code-auditor
description: Audits code for static compliance and security
---
Run PythonAstCritic before final handoff.
""",
            encoding="utf-8",
        )

        registry = SkillRegistry(allowed_roots=[root])
        registry.scan_directory(skills_dir)
        skill_ctx = registry.build_skill_context(["code-auditor"], max_bytes=1024)
        assert "code-auditor" in skill_ctx

        # 2. Scratchpad & Session
        session_mgr = SessionManager(store)
        session = session_mgr.create_session("sess_e2e_1")
        session.set("skill_context", skill_ctx)
        session_mgr.save_session(session)

        scratchpad = WorkingScratchpad()
        scratchpad.set("active_task", "data_pipeline", session_id="sess_e2e_1")

        # 3. A* Planning Engine
        initial_state = StateNode("init", {"extracted": False, "transformed": False, "loaded": False})
        actions = [
            ActionDefinition("extract", 1.0, {"extracted": False}, {"extracted": True}),
            ActionDefinition("transform", 1.0, {"extracted": True, "transformed": False}, {"transformed": True}),
            ActionDefinition("load", 1.0, {"transformed": True, "loaded": False}, {"loaded": True}),
        ]
        model = StateMachineTransitionModel(actions)
        planner = AStarPlanner(model)
        plan = planner.plan(initial_state, lambda s: s.get("loaded") is True)

        assert plan is not None
        assert len(plan.steps) == 3
        assert [s.action_type for s in plan.steps] == ["extract", "transform", "load"]

        # 4. In-Memory Self-Reflection & Critic Loop
        critic = CriticEngine([PythonAstCritic(require_type_annotations=True)])
        reflector = SelfReflector(critic, max_iterations=3)

        draft_code = """
import pdb

def process_batch(items: list):
    return [i * 2 for i in items]
"""
        reflection_result = reflector.reflect_and_patch(draft_code)
        assert reflection_result.success is True
        assert reflection_result.patched is True
        assert "pdb" not in reflection_result.final_artifact or "# [Self-Reflection" in reflection_result.final_artifact
        assert "-> Any:" in reflection_result.final_artifact

        # 5. Episodic Memory Recording
        episodic = EpisodicMemory(store)
        episodic.record_trace(
            TraceRecord(
                task_id="data_pipeline",
                step_index=0,
                action="plan_and_reflect",
                observation="Successfully planned 3 steps and patched code",
                reward=1.0,
                done=True,
            )
        )
        episodic.record_recipe("FORBIDDEN_IMPORT_PDB", "Comment out import and replace with logging")

        traces = episodic.get_traces("data_pipeline")
        assert len(traces) == 1
        assert traces[0].done is True

        recipe = episodic.lookup_recipe("FORBIDDEN_IMPORT_PDB")
        assert recipe is not None

        # 6. Semantic Memory Indexing & Search
        semantic = SemanticMemory(store)
        doc = f"Pipeline execution completed with plan: {[s.action_type for s in plan.steps]}. Cleaned code generated."
        semantic.index_document("pipe_summary", doc, category="pipelines")

        search_results = semantic.search("pipeline execution", category="pipelines", top_k=1)
        assert len(search_results) == 1
        assert "pipe_summary" == search_results[0].item_id

        total_elapsed_ms = (time.time() - total_start) * 1000
        # Entire cognitive pipeline completes in sub-second time!
        assert total_elapsed_ms < 1000.0
