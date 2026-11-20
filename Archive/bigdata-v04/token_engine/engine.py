"""
engine.py – Core deterministic token engine.
"""

from .predictor import TokenPredictor
from .rules import RuleEngine
from .audit import AuditLogger


class TokenEngine:
    """Calculate token budget, apply throttling, and handle override."""

    def __init__(self, threshold_percent: float = 10.0, min_tokens: int = 5):
        # Initialise components in a single line for brevity
        self.predictor, self.rules, self.audit = (
            TokenPredictor(),
            RuleEngine(threshold_percent, min_tokens),
            AuditLogger(),
        )

    def process(self, prompt: str, allow_override: bool = False) -> str:
        """Return output after applying token budget logic.

        Returns ``THROTTLE_REQUIRED`` when user confirmation is needed.
        """
        estimated = self.predictor.estimate(prompt)
        self.audit.log_estimate(prompt, estimated)

        if allow_override:
            self.audit.log_override(prompt, allowed=True)
            return self._compress(self._run_model(prompt))

        if self.rules.should_throttle(estimated):
            self.audit.log_throttle(prompt, decision="required")
            return "THROTTLE_REQUIRED"

        return self._run_model(prompt)

    def _run_model(self, prompt: str) -> str:
        """Placeholder LLM call – echo prompt for prototype."""
        return f"MODEL_OUTPUT:{prompt}"

    def _compress(self, text: str) -> str:
        """Collapse whitespace – naive compression placeholder."""
        return " ".join(text.split())
