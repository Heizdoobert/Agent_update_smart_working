# Human-in-the-Loop (HITL) Checkpointer Protocol

## 1. When to Escalate to Human

Escalation occurs in two cases:
1. **Retry Limit Exceeded:** `iteration >= max_retries` without achieving `SUCCESS`.
2. **Ambiguous Objective:** Evaluator determines multiple valid interpretations exist.

## 2. State Checkpointing & Persistence

The execution state is saved to `.agent/reflexion_state.json`:
```json
{
  "session_id": "c71a39f0",
  "iteration": 3,
  "status": "PENDING_HITL",
  "goal": "Generate SQL query for active users with streak > 7",
  "last_failure": "Column 'streak' does not exist in table 'users'.",
  "suggested_actions": [
    "Table might be 'user_streaks' instead of 'users'",
    "Add schema inspection tool call before generating query"
  ]
}
```

## 3. Resuming Execution with Human Directive

When the user enters a directive (e.g., `"The streak column is inside user_profiles table"`):
1. State is updated:
   - `hitl_feedback` = `"The streak column is inside user_profiles table"`
   - `iteration` = 0 (reset for human-guided loop)
   - `status` = `"REFLECTING"`
2. Prompt is formatted with high priority:
   ```text
   [CRITICAL USER OVERRIDE]:
   The user explicitly guided: "The streak column is inside user_profiles table"
   Prioritize this instruction above all previous assumptions.
   ```
3. Execution resumes seamlessly without losing the prior diagnostic context.
