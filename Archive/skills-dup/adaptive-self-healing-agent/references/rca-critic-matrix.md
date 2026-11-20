# Root Cause Analysis (RCA) & Critic Matrix

## 1. Error Taxonomy & Diagnosis Heuristics

When a run fails, the Evaluator or RCA parser classifies the failure into one of five standard archetypes:

| Category | Pattern / Triggers | Remediation Strategy |
| :--- | :--- | :--- |
| `SYNTAX_ERROR` | `SyntaxError`, `IndentationError`, `ParseError` | AST validation; force exact syntax template in next prompt |
| `MISSING_DEP` | `ModuleNotFoundError`, `ImportError`, `command not found` | Add dependency check or graceful standard-library fallback |
| `ASSERTION_FAIL` | Test failures, schema mismatch, missing JSON key | Provide exact diff between expected and actual schema |
| `TIMEOUT_OR_HANG` | Subprocess timeout, lock contention | Reduce search scope, add early termination or streaming |
| `HALLUCINATION` | Fake API methods, nonexistent file paths | Force grounding via `read_file` or `run_command` inspection |

## 2. Structured Reflection Payload

On iteration $k+1$, format the prompt injected into the executing agent:

```text
======================= ADAPTIVE SELF-CORRECTION =======================
Iteration: {iteration} / {max_retries}
Detected Error Class: {error_class}

[FAILED STEP REASONING]:
{prior_step_summary}

[ROOT CAUSE ANALYSIS (RCA)]:
{rca_diagnosis}

[PREVIOUS DEFECT]:
{exact_error_or_diff}

[ACTIONABLE DIRECTIVE FOR NEXT ATTEMPT]:
1. Do NOT repeat: {antipattern_action}
2. Apply mandatory fix: {remediation_advice}
3. Maintain context budget under 3072 bytes.
========================================================================
```

## 3. Critic Scoring Function
- **Score >= 95%**: Approved to transition to `SUCCESS`.
- **Score 70% - 94%**: Marginal; requires self-reflection with targeted patch.
- **Score < 70%**: Critical defect; trigger full plan re-synthesis or human escalation.
