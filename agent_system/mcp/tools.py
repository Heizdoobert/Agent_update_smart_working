"""Cognitive tools dispatcher and JSON Schema declarations for MCP server."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from agent_system.core.truncator import StructuralTruncator
from agent_system.memory.episodic import EpisodicMemory
from agent_system.memory.semantic import SemanticMemory
from agent_system.reasoning.astar import AStarPlanner
from agent_system.reasoning.mcts import MCTSPlanner
from agent_system.reasoning.transition import (
    ActionDefinition,
    StateMachineTransitionModel,
    StateNode,
)
from agent_system.reflection.adapters.python_ast import PythonAstCritic
from agent_system.reflection.critic import CriticEngine, SchemaCritic
from agent_system.reflection.reflector import SelfReflector
from agent_system.sdk.ingestion import KnowledgeIngester
from agent_system.sdk.registry import PluginRegistry
from agent_system.sdk.scanner import CodebaseScanner
from agent_system.storage.sqlite_store import SQLiteStore

TOOLS_SCHEMA: List[Dict[str, Any]] = [
    {
        "name": "agent_plan",
        "description": "Synthesize optimal action plan using A* Search or MCTS rollout reasoning.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "initial": {
                    "type": "object",
                    "description": "Initial state dictionary of attributes.",
                },
                "goal_key": {
                    "type": "string",
                    "description": "State attribute key that marks goal completion.",
                },
                "goal_value": {
                    "description": "Expected value for goal_key (default: true).",
                },
                "method": {
                    "type": "string",
                    "enum": ["astar", "mcts"],
                    "description": "Planner algorithm ('astar' or 'mcts', default 'astar').",
                },
                "actions": {
                    "type": "array",
                    "description": "Optional list of action objects with name, cost, preconditions, effects.",
                    "items": {"type": "object"},
                },
            },
            "required": ["initial", "goal_key"],
        },
    },
    {
        "name": "agent_critic",
        "description": "Audit code or text artifact against strict static compliance and architectural rules.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Source code or text artifact to audit.",
                },
                "language": {
                    "type": "string",
                    "enum": ["python", "json", "text"],
                    "description": "Target language (default 'python').",
                },
                "strict": {
                    "type": "boolean",
                    "description": "Require complete type annotations (Python).",
                },
            },
            "required": ["code"],
        },
    },
    {
        "name": "agent_reflect",
        "description": "In-memory self-reflection and auto-patching loop to resolve violations before output.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Python code artifact to reflect and repair.",
                },
                "max_iterations": {
                    "type": "integer",
                    "description": "Maximum repair iterations (default 3, max 5).",
                },
            },
            "required": ["code"],
        },
    },
    {
        "name": "agent_memory_search",
        "description": "Search semantic memory using BM25 / FTS5 ranking.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query terms.",
                },
                "category": {
                    "type": "string",
                    "description": "Optional category filter.",
                },
                "top_k": {
                    "type": "integer",
                    "description": "Maximum results to return (default 3).",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "agent_memory_recipe_record",
        "description": "Record recovery recipe or fix solution in episodic memory.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "Error or issue key."},
                "recipe": {"type": "string", "description": "Solution recipe."},
            },
            "required": ["key", "recipe"],
        },
    },
    {
        "name": "agent_memory_recipe_get",
        "description": "Lookup recovery recipe from episodic memory.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "Error or issue key."},
            },
            "required": ["key"],
        },
    },
    {
        "name": "agent_scan",
        "description": "Scan codebase manifests and extract tech stack, test runner, and coding rules.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "root": {
                    "type": "string",
                    "description": "Root path to scan (default current directory).",
                },
            },
        },
    },
    {
        "name": "agent_init_auto",
        "description": "Auto-initialize brownfield project into agent_system: generate Tier 1 rules and index Tier 2 docs.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "root": {
                    "type": "string",
                    "description": "Root directory of the project (default current directory).",
                },
            },
        },
    },
]


class CognitiveToolsDispatcher:
    """Dispatches MCP tool invocations to the in-memory agent_system cognitive modules."""

    def __init__(self, root_path: str | Path = ".") -> None:
        self.root_path = Path(root_path).resolve()
        self._store: Optional[SQLiteStore] = None

    @property
    def store(self) -> SQLiteStore:
        """Lazily initialize shared concurrency-safe SQLite store."""
        if self._store is None:
            self._store = SQLiteStore()
        return self._store

    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Return MCP compliant tools specification list."""
        return TOOLS_SCHEMA

    def dispatch(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Execute tool and return string result bounded by context limit."""
        handler = getattr(self, f"_tool_{tool_name}", None)
        if not handler:
            raise ValueError(f"Unknown tool: '{tool_name}'")
        raw_output = handler(arguments)
        return StructuralTruncator.truncate_text(str(raw_output), max_bytes=3072)

    def _tool_agent_plan(self, args: Dict[str, Any]) -> str:
        initial_dict = args.get("initial", {})
        goal_key = args.get("goal_key", "")
        goal_val = args.get("goal_value", True)
        method = args.get("method", "astar")

        initial_state = StateNode("init", initial_dict)
        actions_raw = args.get("actions")
        action_defs: List[ActionDefinition] = []

        if actions_raw:
            action_defs = [
                ActionDefinition(
                    name=a["name"],
                    cost=a.get("cost", 1.0),
                    preconditions=a.get("preconditions", {}),
                    effects=a.get("effects", {}),
                )
                for a in actions_raw
            ]
        else:
            try:
                registry = PluginRegistry(allowed_roots=[self.root_path])
                plugin = registry.load_plugin(self.root_path)
                if plugin:
                    action_defs = registry.get_all_actions()
            except Exception:
                pass

        if not action_defs:
            return "Error: No actions provided via arguments or project plugin."

        model = StateMachineTransitionModel(action_defs)

        def is_goal(state: StateNode) -> bool:
            return state.get(goal_key) == goal_val

        if method == "mcts":
            planner = MCTSPlanner(model, max_rollout_depth=15)
            plan = planner.plan(initial_state, is_goal, simulations=50)
        else:
            planner = AStarPlanner(model)
            plan = planner.plan(initial_state, is_goal)

        steps = [
            {"step_id": s.step_id, "action": s.action_type, "params": s.parameters}
            for s in plan.steps
        ]
        return json.dumps(
            {
                "plan_id": plan.plan_id,
                "score": plan.total_score,
                "step_count": len(steps),
                "steps": steps,
            },
            indent=2,
        )

    def _tool_agent_critic(self, args: Dict[str, Any]) -> str:
        code = args.get("code", "")
        language = args.get("language", "python")
        strict = args.get("strict", False)

        critics = []
        if language == "python":
            critics.append(PythonAstCritic(require_type_annotations=strict))
        elif language == "json":
            critics.append(SchemaCritic())

        engine = CriticEngine(critics)
        report = engine.evaluate(code)
        diagnostics = [
            {"code": d.code, "message": d.message, "severity": d.severity, "line": d.line}
            for d in report.diagnostics
        ]
        return json.dumps(
            {
                "status": report.verdict.status.value,
                "score": report.verdict.score,
                "summary": report.verdict.summary,
                "diagnostics": diagnostics,
                "suggestions": report.suggestions,
            },
            indent=2,
        )

    def _tool_agent_reflect(self, args: Dict[str, Any]) -> str:
        code = args.get("code", "")
        max_iter = min(args.get("max_iterations", 3), 5)

        engine = CriticEngine([PythonAstCritic()])
        reflector = SelfReflector(engine, max_iterations=max_iter)
        result = reflector.reflect_and_patch(code)
        return result.final_artifact

    def _tool_agent_memory_search(self, args: Dict[str, Any]) -> str:
        query = args.get("query", "")
        category = args.get("category")
        top_k = args.get("top_k", 3)

        memory = SemanticMemory(store=self.store)
        results = memory.search(query, category=category, top_k=top_k)

        items = [
            {"id": r.item_id, "score": r.score, "content": r.content, "category": r.category}
            for r in results
        ]
        return json.dumps({"count": len(items), "results": items}, indent=2)

    def _tool_agent_memory_recipe_record(self, args: Dict[str, Any]) -> str:
        key = args.get("key", "")
        recipe = args.get("recipe", "")
        memory = EpisodicMemory(store=self.store)
        memory.record_recovery_recipe(key, recipe)
        return f"Successfully recorded recovery recipe for key '{key}'."

    def _tool_agent_memory_recipe_get(self, args: Dict[str, Any]) -> str:
        key = args.get("key", "")
        memory = EpisodicMemory(store=self.store)
        recipe = memory.get_recovery_recipe(key)
        return recipe if recipe else f"No recipe found for key '{key}'."

    def _tool_agent_scan(self, args: Dict[str, Any]) -> str:
        root = args.get("root") or str(self.root_path)
        scanner = CodebaseScanner(root_path=root)
        manifest = scanner.scan()
        return json.dumps(manifest.to_dict(), indent=2)

    def _tool_agent_init_auto(self, args: Dict[str, Any]) -> str:
        root = args.get("root") or str(self.root_path)
        scanner = CodebaseScanner(root_path=root)
        manifest = scanner.scan()
        ingester = KnowledgeIngester(root_path=root)
        res = ingester.ingest(manifest)
        return json.dumps(
            {
                "status": "SUCCESS",
                "rules_path": str(res.rules_path),
                "rules_bytes": res.rules_bytes,
                "chunks_indexed": res.chunks_indexed,
                "manifest": manifest.to_dict(),
            },
            indent=2,
        )
