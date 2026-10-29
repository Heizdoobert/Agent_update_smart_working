"""Unified CLI Toolkit for Agent System (agent-system)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from agent_system import __version__
from agent_system.core.session import SessionManager
from agent_system.memory.episodic import EpisodicMemory
from agent_system.memory.semantic import SemanticMemory
from agent_system.reasoning.astar import AStarPlanner
from agent_system.reasoning.mcts import MCTSPlanner
from agent_system.reasoning.transition import ActionDefinition, StateMachineTransitionModel, StateNode
from agent_system.reflection.adapters.python_ast import PythonAstCritic
from agent_system.reflection.critic import CriticEngine, SchemaCritic
from agent_system.reflection.reflector import SelfReflector
from agent_system.skills.registry import SkillRegistry
from agent_system.sdk.registry import PluginRegistry
from agent_system.sdk.wizard import OnboardingWizard


def _read_input(file_arg: Optional[str] = None) -> str:
    """Read input from file path, or stdin if '-' or piped."""
    if file_arg and file_arg != "-":
        p = Path(file_arg)
        if not p.is_file():
            sys.stderr.write(f"Error: File '{file_arg}' not found.\n")
            sys.exit(1)
        return p.read_text(encoding="utf-8")

    # If stdin has data piped into it
    if not sys.stdin.isatty() or file_arg == "-":
        return sys.stdin.read()

    return ""


def cmd_plan(args: argparse.Namespace) -> int:
    """Execute A* or MCTS planning from state model."""
    initial_raw = _read_input(args.initial)
    if not initial_raw:
        sys.stderr.write("Error: Missing initial state JSON (--initial or stdin).\n")
        return 1

    init_dict = json.loads(initial_raw)
    initial_state = StateNode(state_id="init", attributes=init_dict)

    action_defs: List[ActionDefinition] = []
    if args.actions:
        actions_raw = _read_input(args.actions)
        if not actions_raw:
            sys.stderr.write("Error: Missing actions JSON (--actions).\n")
            return 1

        actions_data = json.loads(actions_raw)
        action_defs = [
            ActionDefinition(
                name=a["name"],
                cost=a.get("cost", 1.0),
                preconditions=a.get("preconditions", {}),
                effects=a.get("effects", {}),
            )
            for a in actions_data
        ]
    else:
        # Fallback to actions provided by project plugin if available
        try:
            registry = PluginRegistry(allowed_roots=[Path.cwd()])
            plugin = registry.load_plugin(Path.cwd())
            if plugin:
                action_defs = registry.get_all_actions()
        except Exception as e:
            sys.stderr.write(f"Warning: Failed to load plugin actions: {e}\n")

    if not action_defs:
        sys.stderr.write(
            "Error: No action definitions found via --actions or project plugin.\n"
        )
        return 1

    model = StateMachineTransitionModel(action_defs)
    goal_key = args.goal_key
    goal_val: Any = True
    if args.goal_value is not None:
        try:
            goal_val = json.loads(args.goal_value)
        except (json.JSONDecodeError, TypeError):
            goal_val = args.goal_value

    def is_goal(state: StateNode) -> bool:
        return state.get(goal_key) == goal_val

    if args.method == "mcts":
        planner = MCTSPlanner(model, max_rollout_depth=args.max_depth)
        plan = planner.plan(initial_state, is_goal, simulations=args.simulations)
    else:
        planner = AStarPlanner(model)
        plan = planner.plan(initial_state, is_goal)

    if not plan:
        sys.stderr.write("Planning failed: No valid path found to goal.\n")
        return 1

    output = {
        "plan_id": plan.plan_id,
        "goal_id": plan.goal_id,
        "score": plan.total_score,
        "rationale": plan.rationale,
        "steps": [
            {"step": s.step_id, "action": s.action_type, "params": s.parameters}
            for s in plan.steps
        ],
    }
    sys.stdout.write(json.dumps(output, indent=2, ensure_ascii=False) + "\n")
    return 0


def cmd_critic(args: argparse.Namespace) -> int:
    """Evaluate an artifact through registered critics."""
    content = _read_input(args.file)
    if not content:
        sys.stderr.write("Error: No artifact content provided to evaluate.\n")
        return 1

    engine = CriticEngine()
    if args.language == "python":
        engine.register_critic(PythonAstCritic(require_type_annotations=args.strict))
    elif args.language == "json":
        engine.register_critic(SchemaCritic())
    else:
        engine.register_critic(PythonAstCritic())

    report = engine.evaluate(content, context={"language": args.language})

    output = {
        "status": report.verdict.status.value,
        "score": report.verdict.score,
        "summary": report.verdict.summary,
        "diagnostics": [
            {
                "code": d.code,
                "message": d.message,
                "severity": d.severity,
                "line": d.line,
                "fix": d.fix_recipe,
            }
            for d in report.diagnostics
        ],
        "suggestions": report.suggestions,
    }
    sys.stdout.write(json.dumps(output, indent=2, ensure_ascii=False) + "\n")
    return 0 if report.is_passed else 1


def cmd_reflect(args: argparse.Namespace) -> int:
    """Execute in-memory self-reflection and auto-repair."""
    content = _read_input(args.file)
    if not content:
        sys.stderr.write("Error: No artifact provided to reflect and patch.\n")
        return 1

    engine = CriticEngine([PythonAstCritic(require_type_annotations=args.strict)])
    reflector = SelfReflector(engine, max_iterations=args.max_iterations)

    res = reflector.reflect_and_patch(content, context={"language": "python"})

    if args.output_code:
        sys.stdout.write(res.final_artifact + "\n")
    else:
        output = {
            "success": res.success,
            "iterations": res.iterations,
            "patched": res.patched,
            "message": res.message,
            "final_artifact": res.final_artifact,
        }
        sys.stdout.write(json.dumps(output, indent=2, ensure_ascii=False) + "\n")

    return 0 if res.success else 1


def cmd_memory(args: argparse.Namespace) -> int:
    """Memory operations (semantic search, indexing, recovery recipes)."""
    if args.memory_action == "index":
        mem = SemanticMemory()
        mem.index_document(args.id, args.content, category=args.category)
        sys.stdout.write(f"Indexed document '{args.id}' into category '{args.category}'.\n")
        return 0

    elif args.memory_action == "search":
        mem = SemanticMemory()
        results = mem.search(args.query, category=args.category, top_k=args.top_k)
        output = [
            {
                "id": r.item_id,
                "category": r.category,
                "score": r.score,
                "content": r.content,
            }
            for r in results
        ]
        sys.stdout.write(json.dumps(output, indent=2, ensure_ascii=False) + "\n")
        return 0

    elif args.memory_action == "recipe-record":
        episodic = EpisodicMemory()
        episodic.record_recipe(args.key, args.recipe)
        sys.stdout.write(f"Recorded recovery recipe for '{args.key}'.\n")
        return 0

    elif args.memory_action == "recipe-get":
        episodic = EpisodicMemory()
        rec = episodic.lookup_recipe(args.key)
        if not rec:
            sys.stderr.write(f"No recipe found for '{args.key}'.\n")
            return 1
        sys.stdout.write(json.dumps(rec, indent=2, ensure_ascii=False) + "\n")
        return 0

    sys.stderr.write("Unknown memory action.\n")
    return 1


def cmd_skill(args: argparse.Namespace) -> int:
    """Dynamic skill management commands."""
    allowed_dir = Path(args.root_dir).resolve() if args.root_dir else Path.cwd()
    registry = SkillRegistry(allowed_roots=[allowed_dir])
    registry.scan_directory(allowed_dir)

    if args.skill_action == "list":
        skills = registry.list_skills()
        sys.stdout.write(json.dumps(skills, indent=2) + "\n")
        return 0

    elif args.skill_action == "get":
        skill = registry.get_skill(args.name)
        if not skill:
            sys.stderr.write(f"Skill '{args.name}' not found.\n")
            return 1
        out = {
            "name": skill.name,
            "description": skill.description,
            "instructions": skill.instructions,
            "path": skill.path,
            "sha256": skill.sha256,
        }
        sys.stdout.write(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
        return 0

    elif args.skill_action == "inject":
        names = [s.strip() for s in args.names.split(",") if s.strip()]
        ctx = registry.build_skill_context(names, max_bytes=args.max_bytes)
        sys.stdout.write(ctx + "\n")
        return 0

    sys.stderr.write("Unknown skill action.\n")
    return 1


def cmd_session(args: argparse.Namespace) -> int:
    """Session state inspection and manipulation."""
    mgr = SessionManager()

    if args.session_action == "list":
        sessions = mgr.list_sessions()
        sys.stdout.write(json.dumps(sessions, indent=2) + "\n")
        return 0

    elif args.session_action == "get":
        sess = mgr.get_session(args.id)
        if not sess:
            sys.stderr.write(f"Session '{args.id}' not found.\n")
            return 1
        sys.stdout.write(json.dumps(sess.data, indent=2, ensure_ascii=False) + "\n")
        return 0

    elif args.session_action == "set":
        sess = mgr.get_or_create(args.id)
        sess.set(args.key, args.value)
        mgr.save_session(sess)
        sys.stdout.write(f"Updated session '{args.id}': {args.key} = {args.value}\n")
        return 0

    elif args.session_action == "delete":
        deleted = mgr.delete_session(args.id)
        sys.stdout.write(f"Deleted session '{args.id}': {deleted}\n")
        return 0

    sys.stderr.write("Unknown session action.\n")
    return 1


def cmd_init(args: argparse.Namespace) -> int:
    """Run interactive onboarding wizard to bootstrap project SDK configuration."""
    wizard = OnboardingWizard(target_dir=args.target_dir)
    success = wizard.run()
    return 0 if success else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agent-system",
        description="Cognitive Agent Framework CLI: Reasoning, Reflection, Memory & Skills",
    )
    parser.add_argument("--version", action="version", version=f"agent-system {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # 0. Init
    p_init = subparsers.add_parser("init", help="Bootstrap project SDK configuration interactively")
    p_init.add_argument("--target-dir", default=None, help="Target project directory")
    p_init.set_defaults(func=cmd_init)

    # 1. Plan
    p_plan = subparsers.add_parser("plan", help="Synthesize action plan via A* or MCTS")
    p_plan.add_argument("--initial", help="Path to initial state JSON or '-' for stdin")
    p_plan.add_argument("--actions", default=None, help="Path to actions JSON (optional if provided by plugin)")
    p_plan.add_argument("--goal-key", required=True, help="State attribute key denoting goal")
    p_plan.add_argument("--goal-value", default=None, help="State attribute value denoting goal")
    p_plan.add_argument("--method", choices=["astar", "mcts"], default="astar", help="Planning method")
    p_plan.add_argument("--simulations", type=int, default=50, help="MCTS rollout simulations")
    p_plan.add_argument("--max-depth", type=int, default=15, help="Max rollout depth")
    p_plan.set_defaults(func=cmd_plan)

    # 2. Critic
    p_critic = subparsers.add_parser("critic", help="Audit artifact compliance with static rules")
    p_critic.add_argument("--file", default="-", help="Path to artifact file or '-' for stdin")
    p_critic.add_argument("--language", choices=["python", "json", "text"], default="python")
    p_critic.add_argument("--strict", action="store_true", help="Require type annotations")
    p_critic.set_defaults(func=cmd_critic)

    # 3. Reflect
    p_reflect = subparsers.add_parser("reflect", help="In-memory self-reflection and auto-patching")
    p_reflect.add_argument("--file", default="-", help="Path to artifact file or '-' for stdin")
    p_reflect.add_argument("--max-iterations", type=int, default=3, help="Max repair iterations (<=5)")
    p_reflect.add_argument("--strict", action="store_true", help="Require type annotations")
    p_reflect.add_argument("--output-code", action="store_true", help="Output raw repaired code only")
    p_reflect.set_defaults(func=cmd_reflect)

    # 4. Memory
    p_mem = subparsers.add_parser("memory", help="Semantic and Episodic memory management")
    mem_sub = p_mem.add_subparsers(dest="memory_action", required=True)

    m_idx = mem_sub.add_parser("index", help="Index document into semantic search")
    m_idx.add_argument("--id", required=True, help="Document ID")
    m_idx.add_argument("--content", required=True, help="Document text")
    m_idx.add_argument("--category", default="general", help="Category tag")

    m_search = mem_sub.add_parser("search", help="BM25 search over semantic memory")
    m_search.add_argument("--query", required=True, help="Search query")
    m_search.add_argument("--category", default=None, help="Filter category")
    m_search.add_argument("--top-k", type=int, default=3, help="Max results")

    m_rec_set = mem_sub.add_parser("recipe-record", help="Record recovery recipe")
    m_rec_set.add_argument("--key", required=True, help="Error or issue key")
    m_rec_set.add_argument("--recipe", required=True, help="Recovery recipe description")

    m_rec_get = mem_sub.add_parser("recipe-get", help="Lookup recovery recipe")
    m_rec_get.add_argument("--key", required=True, help="Error or issue key")
    p_mem.set_defaults(func=cmd_memory)

    # 5. Skill
    p_skill = subparsers.add_parser("skill", help="Dynamic skill discovery and injection")
    skill_sub = p_skill.add_subparsers(dest="skill_action", required=True)

    s_list = skill_sub.add_parser("list", help="List registered skills")
    s_list.add_argument("--root-dir", default=None, help="Root directory to scan")

    s_get = skill_sub.add_parser("get", help="Get skill details")
    s_get.add_argument("--name", required=True, help="Skill name")
    s_get.add_argument("--root-dir", default=None, help="Root directory")

    s_inj = skill_sub.add_parser("inject", help="Build bounded skill prompt context")
    s_inj.add_argument("--names", required=True, help="Comma-separated skill names")
    s_inj.add_argument("--max-bytes", type=int, default=3072, help="Max bytes budget (<3KB)")
    s_inj.add_argument("--root-dir", default=None, help="Root directory")
    p_skill.set_defaults(func=cmd_skill)

    # 6. Session
    p_sess = subparsers.add_parser("session", help="Session token management across commands")
    sess_sub = p_sess.add_subparsers(dest="session_action", required=True)

    ss_list = sess_sub.add_parser("list", help="List all active sessions")
    ss_get = sess_sub.add_parser("get", help="Get session data")
    ss_get.add_argument("--id", required=True, help="Session ID")
    ss_set = sess_sub.add_parser("set", help="Set session key-value")
    ss_set.add_argument("--id", required=True, help="Session ID")
    ss_set.add_argument("--key", required=True, help="Key")
    ss_set.add_argument("--value", required=True, help="Value")
    ss_del = sess_sub.add_parser("delete", help="Delete session")
    ss_del.add_argument("--id", required=True, help="Session ID")
    p_sess.set_defaults(func=cmd_session)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    effective_args = sys.argv[1:] if argv is None else list(argv)
    if not effective_args:
        # Bare root invocation: check if interactive first-time setup is needed
        wizard = OnboardingWizard()
        if wizard.is_interactive() and wizard.is_needed():
            success = wizard.run()
            return 0 if success else 1
        parser = build_parser()
        parser.print_help()
        return 0

    parser = build_parser()
    args = parser.parse_args(argv)
    if hasattr(args, "func"):
        return args.func(args)
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
