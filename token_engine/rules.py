"""
rules.py – Deterministic throttling rules.
"""

class RuleEngine:
    """Apply simple percentage‑based throttling.

    The rule is: if estimated tokens exceed ``min_tokens * (1 + threshold)``
    we require user confirmation.
    """

    def __init__(self, threshold_percent: float, min_tokens: int):
        self.threshold = threshold_percent / 100.0
        self.min_tokens = min_tokens

    def should_throttle(self, estimated_tokens: int) -> bool:
        return estimated_tokens > self.min_tokens * (1 + self.threshold)
