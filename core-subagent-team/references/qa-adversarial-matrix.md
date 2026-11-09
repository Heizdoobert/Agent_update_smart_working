# Ruthless QA Adversarial Testing Matrix

This matrix defines the non-negotiable test criteria enforced by `ruthless-qa` in **"NO MERCY"** mode. Every code change must be subjected to these checks before receiving a PASS verdict.

---

## 1. Adversarial Test Dimensions

```text
┌────────────────────────────────────────────────────────────────────────┐
│                   RUTHLESS QA ADVERSARIAL MATRIX                       │
├──────────────────────┬─────────────────────────────────────────────────┤
│ 1. Boundary & Fuzz   │ Extreme numbers, null, empty, Unicode, malformed│
├──────────────────────┼─────────────────────────────────────────────────┤
│ 2. Error Recovery    │ Missing files, timeouts, permission, broken JSON│
├──────────────────────┼─────────────────────────────────────────────────┤
│ 3. Concurrency/Race  │ Re-entrancy, parallel writes, lock contention   │
├──────────────────────┼─────────────────────────────────────────────────┤
│ 4. Static Compliance │ agent-system critic --strict, 100% type safety  │
├──────────────────────┼─────────────────────────────────────────────────┤
│ 5. Regression Blast  │ Side-effects on sibling modules & imports       │
└──────────────────────┴─────────────────────────────────────────────────┘
```

---

## 2. Dimension Checklist & Execution Guides

### Dimension 1: Boundary & Input Fuzzing
- [ ] **Empty / Null values**: Pass `None`, `null`, `""`, `[]`, `{}`. Verify graceful handling without uncaught `AttributeError`, `TypeError`, or `NullPointerException`.
- [ ] **Numerical extremes**: Test with `0`, negative values (`-1`), floating-point edge cases (`NaN`, `Infinity`), and large integers ($2^{31}-1$, $2^{63}-1$).
- [ ] **String & Encoding attacks**: Test with Unicode (accents, emojis, RTL characters), trailing whitespaces, and string lengths exceeding standard buffers (>10,000 characters).
- [ ] **Malformed payloads**: Test invalid JSON, truncated payloads, unexpected extra keys, and mismatched data types.

### Dimension 2: Error Recovery & Graceful Degradation
- [ ] **Missing dependencies/files**: Delete or mock missing required files or environment variables; ensure clear diagnostic errors rather than unhandled crashes.
- [ ] **Timeout & Network failure**: Simulate high latency or connection dropouts; verify timeouts and retry backoffs function correctly.
- [ ] **Corrupt data files**: Provide corrupted sqlite DBs, invalid JSON configs, or zero-byte files; verify self-healing or explicit recovery behavior.

### Dimension 3: Concurrency & State Mutation
- [ ] **Re-entrancy & Idempotency**: Call the same function multiple times with the same input; ensure subsequent calls produce consistent output without duplicating state or corrupting storage.
- [ ] **Parallel Execution**: Simulate multiple threads or concurrent async tasks executing the target method; ensure no race conditions or lock deadlocks.

### Dimension 4: Static Compliance & Type Integrity
- [ ] **Static Rule Evaluation**:
  ```bash
  agent-system critic --file <target_file> --strict
  ```
  Must return exit code `0` (100/100 score). No missing type annotations, no syntax violations, no unhandled imports.

### Dimension 5: Regression & Blast Radius
- [ ] **Existing Test Suite**: Run all pre-existing tests in the repository to guarantee no regressions were introduced.
- [ ] **Dependency Verification**: Verify that sibling modules importing the modified unit continue to operate without breakages.

---

## 3. Mandatory Test Suite Structure

`ruthless-qa` must organize its written tests according to this pattern:

```python
import unittest

class TestTargetAdversarial(unittest.TestCase):
    def setUp(self):
        # Clean isolated fixture setup
        pass

    def test_nominal_path(self):
        """Verify baseline expected behavior."""
        pass

    def test_boundary_and_fuzz(self):
        """Pass extreme and malformed inputs to expose unhandled crashes."""
        pass

    def test_error_recovery_and_exceptions(self):
        """Verify explicit exceptions and recovery under fault injection."""
        pass

    def test_idempotency_and_state(self):
        """Verify repeated invocation leaves state uncorrupted."""
        pass

if __name__ == "__main__":
    unittest.main()
```

---

## 4. Acceptance Gate (No Mercy)

Code is **REJECTED** if:
1. Any test case in the adversarial suite fails or produces an unhandled exception.
2. `agent-system critic --strict` returns any warnings or violations.
3. Code silently catches and swallows exceptions without logging or structured recovery.
4. Existing test suites fail due to unintended side-effects.

Code is **APPROVED (PASS)** only when:
- 100% of nominal, boundary, and error-injection test cases pass cleanly.
- Code passes all static audits with 100/100 score.
- Full execution evidence and log output are captured and attached to the report.
