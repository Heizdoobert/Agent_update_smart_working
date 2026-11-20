# Memory-Augmented Reflection & Dynamic Few-Shot

## 1. The Episodic Memory Loop

The true power of an adaptive agent is persistence across different sessions. When an error is resolved on iteration $k > 0$, the resolution must not vanish with the context window.

### Step 1: Synthesis of Recovery Recipe
When moving to `SUCCESS` after prior failures, generate a compact recipe:
```json
{
  "domain": "api_client_error",
  "error_signature": "TypeError: object of type 'NoneType' has no len()",
  "culprit": "Missing default empty list on API response payload",
  "solution": "Use response.get('items', []) instead of response['items'] directly."
}
```

### Step 2: Storage via CLI
Persist directly to Episodic Memory:
```bash
agent-system memory recipe-record \
  --key "RECIPE_API_CLIENT_NONETYPE" \
  --recipe "When handling API payloads that may be null, initialize with .get('items', []) to avoid TypeError."
```

## 2. Dynamic Few-Shot Injection at Task Start

At the beginning of any task (State `INIT`):
1. Query semantic memory:
   ```bash
   agent-system memory search --query "<task_description_keywords>" --top-k 2
   ```
2. Query error recovery recipe:
   ```bash
   agent-system memory recipe-get --key "<known_error_key>"
   ```
3. Inject the retrieved recipes into the system prompt:
   ```text
   [PRIOR SUCCESSFUL PATTERNS (FEW-SHOT)]:
   - Pattern 1: {recipe_content_1}
   - Pattern 2: {recipe_content_2}
   ```
This primes the LLM with field-tested solutions before it makes its first attempt.
