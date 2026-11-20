"""
tri_modal_router.router
-----------------------
Enforces the Tri-Modal Token Economics routing rule derived from the War-Room consensus:
1. Tier 0: Pure Code (DuckDB/Polars) - 0 tokens, $0.00, 10M+ rows/sec.
2. Tier 1: Real-Time Worker Pool (Flash/Flash-Lite) - 1s-5s latency.
3. Tier 2: Asynchronous Batch API (Gemini/OpenAI) - 50% discount, separate token quotas, 24h SLA.
"""

from enum import Enum
from typing import Dict, Any, Optional


class ExecutionTier(str, Enum):
    TIER_0_PURE_CODE = "pure_code"          # DuckDB/Polars: math, aggregation, filtering, parsing
    TIER_1_REALTIME_LLM = "realtime_llm"    # Interactive loops, multi-turn ReAct, blocking quality gates
    TIER_2_BATCH_API = "batch_api"          # Embarrassingly parallel, offline, >1k items, >5M tokens


class TaskDomain(str, Enum):
    DATA_TRANSFORMATION = "data_transformation"
    TABLE_AGGREGATION = "table_aggregation"
    REGEX_PARSING = "regex_parsing"
    INTERACTIVE_AGENT_LOOP = "interactive_agent_loop"
    CODE_MODIFICATION = "code_modification"
    BATCH_DOCUMENT_ENRICHMENT = "batch_document_enrichment"
    MASS_SYNTHETIC_DATA_GEN = "mass_synthetic_data_gen"


def route_execution_tier(
    task_domain: TaskDomain,
    is_interactive_or_multi_turn: bool = False,
    estimated_tokens: int = 0,
    sla_tolerance_hours: float = 0.0,
) -> Dict[str, Any]:
    """Determine the optimal execution tier for a given task.

    Returns routing envelope with rationale and cost discount factor.
    """
    # 1. TIER 0: Deterministic Relational & String Operations
    deterministic_domains = {
        TaskDomain.DATA_TRANSFORMATION,
        TaskDomain.TABLE_AGGREGATION,
        TaskDomain.REGEX_PARSING,
    }
    if task_domain in deterministic_domains:
        return {
            "tier": ExecutionTier.TIER_0_PURE_CODE,
            "engine": "DuckDB/Native Python",
            "token_cost": 0,
            "cost_discount": "100% ($0.00)",
            "rationale": "Relational/tabular computation strictly routed to pure code (zero token burn & zero hallucination).",
        }

    # 2. Hard-pinned interactive agent loops and code modification tasks
    interactive_domains = {
        TaskDomain.INTERACTIVE_AGENT_LOOP,
        TaskDomain.CODE_MODIFICATION,
    }
    if task_domain in interactive_domains or is_interactive_or_multi_turn:
        return {
            "tier": ExecutionTier.TIER_1_REALTIME_LLM,
            "engine": "Real-Time Subagent Pool (Flash / Flash-Lite)",
            "token_cost": estimated_tokens,
            "cost_discount": "0% (Full Price)",
            "rationale": "Turnaround time critical or multi-turn agent dependency; Batch API 24h SLA would deadlock workflow.",
        }

    # 3. TIER 2: Large-scale embarrassingly parallel asynchronous jobs
    if estimated_tokens >= 5_000_000:
        if sla_tolerance_hours >= 12.0:
            return {
                "tier": ExecutionTier.TIER_2_BATCH_API,
                "engine": "Gemini / OpenAI Batch API",
                "token_cost": int(estimated_tokens * 0.5),
                "cost_discount": "50% Flat Discount",
                "rationale": "Asynchronous high-volume workload; qualifies for 50% discount on dedicated batch token quotas.",
            }
        else:
            return {
                "tier": ExecutionTier.TIER_1_REALTIME_LLM,
                "engine": "Real-Time Subagent Pool (Flash / Flash-Lite)",
                "token_cost": estimated_tokens,
                "cost_discount": "0% (Full Price)",
                "rationale": "Volume qualifies for Batch API but SLA requirement (<12h) mandates real-time execution",
            }

    # 4. Latency-sensitive fallback (< 4h SLA)
    if sla_tolerance_hours < 4.0:
        return {
            "tier": ExecutionTier.TIER_1_REALTIME_LLM,
            "engine": "Real-Time Subagent Pool (Flash / Flash-Lite)",
            "token_cost": estimated_tokens,
            "cost_discount": "0% (Full Price)",
            "rationale": "Turnaround time critical or multi-turn agent dependency; Batch API 24h SLA would deadlock workflow.",
        }

    # Fallback default: Tier 1
    return {
        "tier": ExecutionTier.TIER_1_REALTIME_LLM,
        "engine": "Real-Time Subagent Pool (Flash / Flash-Lite)",
        "token_cost": estimated_tokens,
        "cost_discount": "0% (Standard)",
        "rationale": "Workload volume below 5M tokens threshold; real-time execution preferred.",
    }
