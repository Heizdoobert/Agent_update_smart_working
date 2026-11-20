"""Metrics & KPIs — domain-agnostic, file-based (no server, no DB).

Sources: claude-progress.txt, features.json, docs/trace-log/ — computed on demand.
Thresholds are HARD per THIẾT §14.5 / §22 / §18.5:
  context warn@30 / critical@40, KV-cache >80%, in:out <80:1,
  tool count <15 safe / >30 prune, rollback <=0.5%, self-verification >90%,
  token shift ~70%, FLOW retry ceiling = 2.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Optional

# ── Hard ceilings (THIẾT §18.5 / §22) ──────────────────────────────────────
FLOW_RETRY_CEILING = 2          # parallel FLOW loop: fail 2 rounds -> Human Gate (M4)
FLOW_RETRY_CEILING_SINGLE = 3   # single-agent loop keeps 3 (reflect ceiling unchanged)

CONTEXT_WARN = 30               # % of context window
CONTEXT_CRITICAL = 40           # % -> suggest "reset session"
KV_CACHE_TARGET = 80.0          # hit-rate % target
IN_OUT_RATIO_MAX = 80.0         # tokens-in : tokens-out
TOOL_COUNT_SAFE = 15
TOOL_COUNT_PRUNE = 30
ROLLBACK_RATE_MAX = 0.005       # 0.5%
SELF_VERIFICATION_TARGET = 0.90  # 90%
TOKEN_SHIFT_TARGET = 0.70       # ~70%


@dataclass
class Metric:
    name: str
    value: float
    level: str   # safe | warn | critical | no_data
    action: str

    def to_dict(self) -> dict:
        return asdict(self)


def _metric(name: str, value: float, level: str, action: str) -> Metric:
    return Metric(name=name, value=value, level=level, action=action)


def _no_data(name: str, action: str) -> Metric:
    return Metric(name=name, value=float("nan"), level="no_data", action=action)


# ── Context economy (M1, THIẾT §14.5) ──────────────────────────────────────

def context_usage_pct(tokens_used: Optional[int], window: Optional[int]) -> Metric:
    """Context usage %; warn @30, critical @40 (reset session, no summarization)."""
    if not tokens_used or not window or window <= 0:
        return _no_data("context_usage_pct", "no data — pass tokens_used + context window")
    pct = min(100.0, (tokens_used / window) * 100.0)
    if pct >= CONTEXT_CRITICAL:
        return _metric("context_usage_pct", round(pct, 1), "critical",
                       "RESET SESSION NOW (context >40% — no summarization)")
    if pct >= CONTEXT_WARN:
        return _metric("context_usage_pct", round(pct, 1), "warn",
                       "compact via handoff files (claude-progress.txt) before continuing")
    return _metric("context_usage_pct", round(pct, 1), "safe", "continue")


def kv_cache_hit_rate(hits: Optional[int], total: Optional[int]) -> Metric:
    """KV-cache hit rate %; target > 80."""
    if not hits or total is None or total <= 0:
        return _no_data("kv_cache_hit_rate", "no data — pass hits + total requests")
    rate = min(100.0, (hits / total) * 100.0)
    if rate > KV_CACHE_TARGET:
        return _metric("kv_cache_hit_rate", round(rate, 1), "safe", "target met")
    if rate >= KV_CACHE_TARGET - 20:
        return _metric("kv_cache_hit_rate", round(rate, 1), "warn",
                       "below 80% target — batch similar prompts, reuse prefixes")
    return _metric("kv_cache_hit_rate", round(rate, 1), "critical",
                   "far below 80% — restructure prompts to share prefixes")


def input_output_ratio(in_tokens: Optional[int], out_tokens: Optional[int]) -> Metric:
    """Tokens-in : tokens-out ratio; target < 80:1."""
    if not in_tokens or not out_tokens or out_tokens <= 0:
        return _no_data("input_output_ratio", "no data — pass in_tokens + out_tokens")
    ratio = in_tokens / out_tokens
    if ratio < IN_OUT_RATIO_MAX:
        return _metric("input_output_ratio", round(ratio, 1), "safe", "continue")
    if ratio < IN_OUT_RATIO_MAX * 2:
        return _metric("input_output_ratio", round(ratio, 1), "warn",
                       ">80:1 — trim context (FEATURE_MAP lazy loading)")
    return _metric("input_output_ratio", round(ratio, 1), "critical",
                   ">>80:1 — context bloat; reset session + re-verify from handoff files")


def tool_count(n: Optional[int]) -> Metric:
    """Registered tools; <15 safe, >30 prune."""
    if n is None or n < 0:
        return _no_data("tool_count", "no data — pass registered tool count")
    if n < TOOL_COUNT_SAFE:
        return _metric("tool_count", float(n), "safe", "continue")
    if n <= TOOL_COUNT_PRUNE:
        return _metric("tool_count", float(n), "warn",
                       ">15 tools — group rarely-used tools behind one dispatcher")
    return _metric("tool_count", float(n), "critical",
                   ">30 tools — PRUNE; every tool eats context budget")


# ── KPI North Star (M2, THIẾT §22) ─────────────────────────────────────────

def rollback_rate(reverted: Optional[int], total: Optional[int]) -> Metric:
    """Reverted / total changes; North Star <= 0.5%."""
    if reverted is None or total is None or total <= 0:
        return _no_data("rollback_rate", "no data — count reverts (git 'Revert' + features.json rolled_back)")
    rate = reverted / total
    if rate <= ROLLBACK_RATE_MAX:
        return _metric("rollback_rate", round(rate, 4), "safe", "within 0.5% target")
    if rate <= ROLLBACK_RATE_MAX * 5:
        return _metric("rollback_rate", round(rate, 4), "warn",
                       ">0.5% — run ERROR_ANALYSIS on trace-log to find the pattern")
    return _metric("rollback_rate", round(rate, 4), "critical",
                   "rollback storm — stop shipping, audit verification step")


def self_verification_rate(proven: Optional[int], total: Optional[int]) -> Metric:
    """Claims proven with evidence / total claims; target > 90%."""
    if proven is None or total is None or total <= 0:
        return _no_data("self_verification_rate", "no data — mark proven/total in features.json")
    rate = proven / total
    if rate > SELF_VERIFICATION_TARGET:
        return _metric("self_verification_rate", round(rate, 4), "safe", "target met (>90%)")
    if rate >= SELF_VERIFICATION_TARGET - 0.10:
        return _metric("self_verification_rate", round(rate, 4), "warn",
                       "<=90% — every 'done' must cite evidence + commit SHA (rules §8)")
    return _metric("self_verification_rate", round(rate, 4), "critical",
                   "<<90% — verification theater; enforce SESSION_RITUAL step 3")


def token_shift_to_verification(verify_tokens: Optional[int], total_tokens: Optional[int]) -> Metric:
    """Share of tokens spent verifying; target ~70% (estimate from trace-log)."""
    if verify_tokens is None or total_tokens is None or total_tokens <= 0:
        return _no_data("token_shift_to_verification",
                        "no data — estimate verify tokens from trace-log (marked estimate)")
    share = min(1.0, verify_tokens / total_tokens)
    if share >= TOKEN_SHIFT_TARGET - 0.10:
        return _metric("token_shift_to_verification", round(share, 3), "safe",
                       "near ~70% target (estimate)")
    return _metric("token_shift_to_verification", round(share, 3), "warn",
                   "well below ~70% — verification under-invested; add verify_cli checks")


# ── Aggregate dashboard (M3/M6) ────────────────────────────────────────────

def compute_dashboard() -> list:
    """8-metric dashboard with whatever data is available (never crashes on missing files)."""
    return [
        context_usage_pct(None, None),
        kv_cache_hit_rate(None, None),
        input_output_ratio(None, None),
        tool_count(None),
        rollback_rate(None, None),
        self_verification_rate(None, None),
        token_shift_to_verification(None, None),
        Metric(name="flow_retry_ceiling", value=float(FLOW_RETRY_CEILING), level="safe",
               action="parallel FLOW loop: 2 fails -> Human Gate (THIẾT §18.5)"),
    ]


def flow_should_handoff(failed_rounds: int, parallel: bool = True) -> bool:
    """Human Gate policy (M4): parallel FLOW loop -> handoff after 2 failed rounds;
    single-agent loop keeps 3. NEVER higher than these ceilings."""
    ceiling = FLOW_RETRY_CEILING if parallel else FLOW_RETRY_CEILING_SINGLE
    return failed_rounds >= ceiling
