# Graph Architecture & State Machine

## 1. State Machine Definition

The `adaptive-self-healing-agent` utilizes a finite state machine (FSM) enforcing bounded cyclic retries with progressive context enrichment.

```
       [INIT] (Inject dynamic few-shots from memory)
          │
          ▼
    [EXECUTING] <─────────────────────────────┐
          │                                   │
          ▼                                   │
    [EVALUATING]                              │
      │        │                              │
(Pass)│        │(Fail & iter < max)           │
      ▼        ▼                              │
  [SUCCESS]  [REFLECTING] (RCA + Feedback) ───┘
      │        │
      │        │(Fail & iter >= max)
      │        ▼
      │    [PENDING_HITL]
      │        │
      ▼        ▼
    [SAVE_RECIPE] ──> [DONE]
```

## 2. Invariants & Guardrails

1. **Max Retry Bound:** Default `max_retries = 3` (hard upper limit = 5). Prevents infinite execution loops and API budget exhaustion.
2. **Context Growth Control (<3KB):** The reflection payload does not append full raw outputs of past iterations. It retains only:
   - Root Cause Diagnosis (1-2 sentences).
   - Culprit snippet / line number.
   - Actionable constraint for the next try.
3. **DAG Non-Cyclic Resolution:** Each iteration index `i` is strictly monotonic (`i + 1`). The state transition graph forms a Directed Acyclic Graph across the temporal dimension.
4. **Deterministic Gate First:** Always run deterministic checks (exit codes, regex assertions, linters) before calling LLM Critic evaluators to conserve latency and token cost.
