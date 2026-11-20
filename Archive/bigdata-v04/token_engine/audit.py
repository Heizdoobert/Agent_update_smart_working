"""
audit.py – Audit logger for token‑engine decisions.
"""

import json
from datetime import datetime
from pathlib import Path

LOG_FILE = Path(__file__).with_name("audit.log.jsonl")


class AuditLogger:
    """Simple JSON‑lines logger.

    Each call writes a separate line with a UTC timestamp. The file lives next
    to the module, which is fine for a prototype. In production you would inject
    a configurable path.
    """

    def _write(self, entry: dict) -> None:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def log_estimate(self, prompt: str, tokens: int) -> None:
        self._write({"ts": datetime.utcnow().isoformat(), "event": "estimate", "prompt": prompt, "tokens": tokens})

    def log_override(self, prompt: str, allowed: bool) -> None:
        self._write({"ts": datetime.utcnow().isoformat(), "event": "override", "prompt": prompt, "allowed": allowed})

    def log_throttle(self, prompt: str, decision: str) -> None:
        self._write({"ts": datetime.utcnow().isoformat(), "event": "throttle", "prompt": prompt, "decision": decision})
