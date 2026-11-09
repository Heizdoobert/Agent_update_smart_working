---
name: adaptive-self-healing-agent
description: Self-improving adaptive agent engine combining Reflexion, trace root-cause analysis (RCA), human-in-the-loop rerun checkpointer, and episodic memory few-shot persistence.
---

# Adaptive & Self-Healing Agent Engine

A closed-loop execution and self-correction architecture that transforms execution failures into durable long-term memory, preventing recurring mistakes across task reruns.

## Core Capabilities

1. **4-Stage Reflexion Graph:** Cyclical state engine (`INIT` -> `EXECUTING` -> `EVALUATING` -> `REFLECTING` / `PENDING_HITL` -> `SUCCESS`).
2. **Deterministic & Critic Evaluation:** First-line validation via linters/unit tests, second-line via static critic scoring.
3. **Automated Root Cause Analysis (RCA):** Classifies faults into `SYNTAX_ERROR`, `MISSING_DEP`, `ASSERTION_FAIL`, `TIMEOUT`, or `RUNTIME_ERROR`.
4. **Episodic Memory Synthesis:** Upon successful self-healing, stores `{error_signature, fix_recipe}` in persistent memory for dynamic few-shot priming in future tasks.
5. **Human-in-the-Loop (HITL) Checkpointer:** Safe escalation when retry limits are reached, resuming execution with human guidance.

## Quick Start & Workflow

Initialize and manage the state machine via `reflexion_runner.py`:

```bash
# 1. Initialize state with goal & memory lookup
python3 scripts/reflexion_runner.py init --goal "Generate clean REST API endpoint" --max-retries 3

# 2. Record action step
python3 scripts/reflexion_runner.py step --action "Generated route handler" --output "SyntaxError at line 14" --exit-code 1

# 3. Evaluate output (command or critic score)
python3 scripts/reflexion_runner.py evaluate --score 65.0

# 4. Generate structured reflection prompt for next attempt
python3 scripts/reflexion_runner.py reflect

# 5. On success after recovery, record recipe to episodic memory
python3 scripts/reflexion_runner.py save-recipe --key "RECIPE_API_HANDLER_SYNTAX" --recipe "Ensure closing parenthesis on decorator."
```

## Modular Reference Links

- [Graph Architecture](file:///mnt/second_drive/SKILL/adaptive-self-healing-agent/references/graph-architecture.md): State schema, transition matrix, and DAG invariants.
- [RCA & Critic Matrix](file:///mnt/second_drive/SKILL/adaptive-self-healing-agent/references/rca-critic-matrix.md): Error classification heuristics, reflection prompt formats, and scoring gates.
- [Memory Few-Shot Injection](file:///mnt/second_drive/SKILL/adaptive-self-healing-agent/references/memory-fewshot-injection.md): Episodic memory recording and dynamic few-shot retrieval protocol.
- [HITL Checkpointer](file:///mnt/second_drive/SKILL/adaptive-self-healing-agent/references/hitl-checkpointer.md): User rerun escalation and checkpoint state persistence.
