#!/usr/bin/env python3
"""Simple CLI wrapper to run supported agents.

Usage:
    python3 scripts/run_agent.py <agent_name> "<prompt>"

The script determines the appropriate model for the requested agent,
respecting the environment variable ``SMALL_MODEL`` (truthy values select a
lighter model).  For the purpose of this repository we do **not** make real API
calls – the script only demonstrates model selection and prints the received
prompt.  Real integration can replace the ``_run_*`` functions with actual SDK
calls.
"""

import os
import sys
from typing import List

# Local configuration module.
from cli.agents_config import get_model


def _run_claude(prompt: str, model: str) -> str:
    # Placeholder – in production you would use ``anthropic`` SDK.
    return f"[Claude ({model})] {prompt}"


def _run_opencode(prompt: str, model: str) -> str:
    # Placeholder – in production you would use ``openai`` SDK.
    return f"[OpenCode ({model})] {prompt}"


def _run_hermes(prompt: str, model: str) -> str:
    # Placeholder – in production you would use ``transformers`` pipeline.
    return f"[Hermes ({model})] {prompt}"


def _run_antigravity(prompt: str, model: str) -> str:
    # Placeholder – could invoke an Antigravity sub‑agent.
    return f"[Antigravity ({model})] {prompt}"


def run_agent(agent_name: str, prompt: str) -> str:
    model = get_model(agent_name)
    agent = agent_name.lower()
    if agent == "claude":
        return _run_claude(prompt, model)
    if agent == "opencode":
        return _run_opencode(prompt, model)
    if agent == "hermes":
        return _run_hermes(prompt, model)
    if agent == "antigravity":
        return _run_antigravity(prompt, model)
    raise ValueError(f"Unsupported agent: {agent_name}")


def main(argv: List[str] = None) -> None:
    if argv is None:
        argv = sys.argv[1:]
    if len(argv) < 2:
        print("Usage: run_agent.py <agent_name> <prompt>")
        sys.exit(1)
    agent_name, prompt = argv[0], argv[1]
    result = run_agent(agent_name, prompt)
    print(result)


if __name__ == "__main__":
    main()
