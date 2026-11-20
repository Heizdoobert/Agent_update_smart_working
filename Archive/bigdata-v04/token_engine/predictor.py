"""
predictor.py – Simple token‑prediction estimator.
"""

import re
from typing import Final

AVG_TOKEN_PER_WORD: Final[float] = 1.3  # rough average for mixed English/Vietnamese


class TokenPredictor:
    """Statistical estimator based on word count.

    For the prototype we use a very simple heuristic. In production this could be
    replaced by a small ML model trained on historic token usage.
    """

    def estimate(self, prompt: str) -> int:
        words = len(re.findall(r"\w+", prompt))
        # Ensure at least 1 token is returned.
        return max(1, int(words * AVG_TOKEN_PER_WORD))
