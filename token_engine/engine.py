"""
engine.py – Core deterministic token engine.
"""

from .predictor import TokenPredictor
from .rules import RuleEngine
from .audit import AuditLogger


class TokenEngine:
    """Calculate token budget, apply throttling, and handle override."""

    def __init__(self, threshold_percent: float = 10.0, min_tokens: int = 5):
        self.predictor = TokenPredictor()
        self.rules = RuleEngine(threshold_percent, min_tokens)
        self.audit = AuditLogger()

    def process(self, prompt: str, allow_override: bool = False) -> str:
        """Return the final output after applying token budget logic.

        If throttling is required and no override, returns the sentinel
        ``THROTTLE_REQUIRED`` so the CLI layer can ask the user.
        """
        estimated = self.predictor.estimate(prompt)
        self.audit.log_estimate(prompt, estimated)

        if allow_override:
            self.audit.log_override(prompt, allowed=True)
            output = self._run_model(prompt)
            return self._compress(output)

        if self.rules.should_throttle(estimated):
            self.audit.log_throttle(prompt, decision="required")
            return "THROTTLE_REQUIRED"

        output = self._run_model(prompt)
        return output

    # ---- internal helpers -------------------------------------------------
    def _run_model(self, prompt: str) -> str:
        """Placeholder for a real LLM call.
        In the prototype we simply echo the prompt.
        """
        return f"MODEL_OUTPUT:{prompt}"

    def _compress(self, text: str) -> str:
        """Very naive compression – just collapse whitespace.
        Replace with a proper summarizer/compressor later.
        """
        return " ".join(text.split())
