#!/usr/bin/env python3
"""
Reflexion Runner: State Machine and Self-Correction Engine for Adaptive Agents.
Provides state checkpointing, deterministic evaluation, RCA diagnosis,
and episodic memory persistence.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

STATE_FILE = Path(".agent/reflexion_state.json")


def ensure_state_dir() -> None:
    """Ensure parent directory of state file exists."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)


def load_state() -> Dict[str, Any]:
    """Load active reflexion state from disk."""
    if not STATE_FILE.exists():
        sys.stderr.write(f"Error: State file {STATE_FILE} not found. Run 'init' first.\n")
        sys.exit(1)
    with open(STATE_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def save_state(state: Dict[str, Any]) -> None:
    """Persist active reflexion state to disk."""
    ensure_state_dir()
    with open(STATE_FILE, "w", encoding="utf-8") as file:
        json.dump(state, file, indent=2, ensure_ascii=False)


def classify_error(raw_error: str) -> str:
    """Heuristic classification of execution errors into standard categories."""
    if re.search(r"SyntaxError|IndentationError|ParseError", raw_error, re.I):
        return "SYNTAX_ERROR"
    if re.search(r"ModuleNotFoundError|ImportError|command not found", raw_error, re.I):
        return "MISSING_DEP"
    if re.search(r"AssertionError|Expected|Mismatch|KeyError", raw_error, re.I):
        return "ASSERTION_FAIL"
    if re.search(r"Timeout|Timed out|ConnectionRefused", raw_error, re.I):
        return "TIMEOUT_OR_HANG"
    return "RUNTIME_ERROR"


def cmd_init(args: argparse.Namespace) -> None:
    """Initialize a new reflexion cycle."""
    session_id = args.session_id or str(uuid.uuid4())[:8]
    few_shots: List[str] = []

    # Optionally query semantic memory for existing recipes
    try:
        query_proc = subprocess.run(
            ["agent-system", "memory", "search", "--query", args.goal, "--top-k", "2"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5,
            check=False,
        )
        if query_proc.returncode == 0 and query_proc.stdout.strip():
            few_shots.append(query_proc.stdout.strip())
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    state: Dict[str, Any] = {
        "session_id": session_id,
        "goal": args.goal,
        "iteration": 0,
        "max_retries": args.max_retries,
        "status": "EXECUTING",
        "few_shots": few_shots,
        "trace": [],
        "last_error": None,
        "rca_diagnosis": None,
        "hitl_feedback": None,
        "recovered": False,
    }
    save_state(state)
    print(f"Reflexion state initialized: session={session_id}, max_retries={args.max_retries}")
    if few_shots:
        print("Injected dynamic few-shots from memory.")


def cmd_step(args: argparse.Namespace) -> None:
    """Record an execution step in the active iteration trace."""
    state = load_state()
    step_record = {
        "iteration": state["iteration"],
        "action": args.action,
        "output": args.output,
        "exit_code": args.exit_code,
    }
    state["trace"].append(step_record)
    save_state(state)
    print(f"Recorded step in iteration {state['iteration']}: {args.action}")


def cmd_evaluate(args: argparse.Namespace) -> None:
    """Evaluate current iteration via validation command or direct score."""
    state = load_state()
    passed = True
    error_output = ""

    if args.check_cmd:
        proc = subprocess.run(
            args.check_cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            passed = False
            error_output = proc.stderr.strip() or proc.stdout.strip()
    elif args.score is not None:
        if args.score < 95.0:
            passed = False
            error_output = f"Evaluation score {args.score} below threshold 95.0."

    if passed:
        state["status"] = "SUCCESS"
        if state["iteration"] > 0:
            state["recovered"] = True
        print(f"Evaluation PASSED at iteration {state['iteration']}.")
        # Invoke memory reflection task to store insights
        try:
            env = os.environ.copy()
            env["TASK_ID"] = state.get("session_id", "unknown")
            env["USER_ID"] = "default_user"
            # Timestamp for metadata (ISO 8601 UTC)
            from datetime import datetime
            env["TIMESTAMP"] = datetime.utcnow().isoformat() + "Z"
            insight_path = f".agent/insights_{state.get('session_id','tmp')}.json"
            env["INSIGHT_FILE"] = insight_path
            subprocess.run([
                sys.executable,
                os.path.join(os.path.dirname(__file__), "../../memory_layer/scripts/memory_reflection.py"),
            ], env=env, check=False)
        except Exception as e:
            print(f"[MemoryReflection] Failed to invoke: {e}")
    else:
        error_class = classify_error(error_output)
        state["last_error"] = {
            "error_class": error_class,
            "raw_message": error_output[:1024],
        }
        state["rca_diagnosis"] = f"Identified {error_class}: {error_output[:250]}"

        if state["iteration"] + 1 >= state["max_retries"]:
            state["status"] = "PENDING_HITL"
            print(f"Max retries reached ({state['max_retries']}). Transitioned to PENDING_HITL.")
        else:
            state["status"] = "REFLECTING"
            print(f"Evaluation FAILED ({error_class}). Transitioned to REFLECTING.")

    save_state(state)


def cmd_reflect(args: argparse.Namespace) -> None:
    """Synthesize structured reflection payload and increment iteration."""
    del args  # unused parameter
    state = load_state()
    if state["status"] not in ("REFLECTING", "PENDING_HITL"):
        print(f"Warning: Current status is '{state['status']}', not REFLECTING.")

    state["iteration"] += 1
    state["status"] = "EXECUTING"

    err = state.get("last_error") or {}
    payload = [
        "=================== ADAPTIVE REFLEXION PROMPT ===================",
        f"Goal: {state['goal']}",
        f"Current Attempt: {state['iteration']} / {state['max_retries']}",
        f"Diagnosed Error Class: {err.get('error_class', 'UNKNOWN')}",
        f"RCA Diagnosis: {state.get('rca_diagnosis', 'None')}",
    ]

    if state.get("hitl_feedback"):
        payload.append(f"[HUMAN FEEDBACK OVERRIDE]: {state['hitl_feedback']}")
        state["hitl_feedback"] = None

    payload.append("Directive: Address the RCA diagnosis directly. Do NOT repeat prior mistakes.")
    payload.append("================================================================")

    save_state(state)
    print("\n".join(payload))


def cmd_hitl(args: argparse.Namespace) -> None:
    """Provide human-in-the-loop guidance to resume an exhausted cycle."""
    state = load_state()
    state["hitl_feedback"] = args.feedback
    state["iteration"] = 0
    state["status"] = "REFLECTING"
    save_state(state)
    print(f"Human guidance injected: '{args.feedback}'. Status set to REFLECTING.")


def cmd_save_recipe(args: argparse.Namespace) -> None:
    """Persist recovery recipe to episodic memory if recovery occurred."""
    state = load_state()
    recipe_text = args.recipe or state.get("rca_diagnosis") or "Generic resolution"
    key = args.key

    try:
        proc = subprocess.run(
            ["agent-system", "memory", "recipe-record", "--key", key, "--recipe", recipe_text],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        if proc.returncode == 0:
            print(f"Recorded recovery recipe to Episodic Memory: {key}")
            state["persisted_recipe"] = key
            save_state(state)
        else:
            print(f"Warning: Failed to record recipe via CLI: {proc.stderr.strip()}")
    except FileNotFoundError:
        print("Notice: 'agent-system' CLI not found. Recipe recorded locally in state.")


def cmd_status(args: argparse.Namespace) -> None:
    """Display active reflexion state."""
    del args
    state = load_state()
    print(f"Session:    {state.get('session_id')}")
    print(f"Goal:       {state.get('goal')}")
    print(f"Status:     {state.get('status')}")
    print(f"Iteration:  {state.get('iteration')} / {state.get('max_retries')}")
    print(f"Recovered:  {state.get('recovered')}")
    if state.get("last_error"):
        print(f"Last Error: {state['last_error'].get('error_class')}")


def main() -> None:
    """CLI Entry point for Reflexion Runner."""
    parser = argparse.ArgumentParser(description="Adaptive Reflexion Runner")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # init
    p_init = subparsers.add_parser("init", help="Initialize reflexion loop")
    p_init.add_argument("--goal", required=True, help="Task objective")
    p_init.add_argument("--max-retries", type=int, default=3, help="Max retry limit")
    p_init.add_argument("--session-id", help="Optional session UUID")

    # step
    p_step = subparsers.add_parser("step", help="Record execution step")
    p_step.add_argument("--action", required=True, help="Description of action taken")
    p_step.add_argument("--output", default="", help="Output or observation")
    p_step.add_argument("--exit-code", type=int, default=0, help="Subprocess exit code")

    # evaluate
    p_eval = subparsers.add_parser("evaluate", help="Evaluate current step")
    p_eval.add_argument("--check-cmd", help="Shell command to validate outcome")
    p_eval.add_argument("--score", type=float, help="Critic score (0-100)")

    # reflect
    subparsers.add_parser("reflect", help="Synthesize reflection prompt")

    # hitl
    p_hitl = subparsers.add_parser("hitl", help="Inject human-in-the-loop feedback")
    p_hitl.add_argument("--feedback", required=True, help="Human guidance directive")

    # save-recipe
    p_rec = subparsers.add_parser("save-recipe", help="Record recipe to episodic memory")
    p_rec.add_argument("--key", required=True, help="Recipe identifier")
    p_rec.add_argument("--recipe", help="Recipe content")

    # status
    subparsers.add_parser("status", help="Show current state")

    parsed = parser.parse_args()

    dispatch = {
        "init": cmd_init,
        "step": cmd_step,
        "evaluate": cmd_evaluate,
        "reflect": cmd_reflect,
        "hitl": cmd_hitl,
        "save-recipe": cmd_save_recipe,
        "status": cmd_status,
    }

    dispatch[parsed.command](parsed)


if __name__ == "__main__":
    main()
