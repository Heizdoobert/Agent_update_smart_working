import pytest
from tri_modal_router.router import ExecutionTier, TaskDomain, route_execution_tier


def test_route_tabular_aggregation_to_tier_0():
    decision = route_execution_tier(
        task_domain=TaskDomain.TABLE_AGGREGATION,
        estimated_tokens=500_000,
    )
    assert decision["tier"] == ExecutionTier.TIER_0_PURE_CODE
    assert decision["token_cost"] == 0
    assert "pure code" in decision["rationale"].lower()


def test_route_interactive_loop_to_tier_1_realtime():
    decision = route_execution_tier(
        task_domain=TaskDomain.CODE_MODIFICATION,
        is_interactive_or_multi_turn=True,
        estimated_tokens=10_000_000,  # Even with high volume, multi-turn requires realtime
        sla_tolerance_hours=24.0,
    )
    assert decision["tier"] == ExecutionTier.TIER_1_REALTIME_LLM
    assert decision["token_cost"] == 10_000_000
    assert "deadlock" in decision["rationale"].lower()


def test_route_bulk_enrichment_to_tier_2_batch_api():
    decision = route_execution_tier(
        task_domain=TaskDomain.BATCH_DOCUMENT_ENRICHMENT,
        is_interactive_or_multi_turn=False,
        estimated_tokens=8_000_000,
        sla_tolerance_hours=24.0,
    )
    assert decision["tier"] == ExecutionTier.TIER_2_BATCH_API
    assert decision["cost_discount"] == "50% Flat Discount"
    assert decision["token_cost"] == 4_000_000


def test_hard_pinned_interactive_agent_loop_and_code_modification():
    for domain in (TaskDomain.INTERACTIVE_AGENT_LOOP, TaskDomain.CODE_MODIFICATION):
        decision = route_execution_tier(
            task_domain=domain,
            is_interactive_or_multi_turn=False,  # Even if multi-turn flag is False
            estimated_tokens=10_000_000,         # Even with massive volume
            sla_tolerance_hours=48.0,            # Even with large SLA
        )
        assert decision["tier"] == ExecutionTier.TIER_1_REALTIME_LLM
        assert decision["token_cost"] == 10_000_000


def test_fallback_when_volume_qualifies_but_sla_requires_fast_response():
    decision = route_execution_tier(
        task_domain=TaskDomain.BATCH_DOCUMENT_ENRICHMENT,
        is_interactive_or_multi_turn=False,
        estimated_tokens=6_000_000,
        sla_tolerance_hours=8.0,  # SLA < 12h
    )
    assert decision["tier"] == ExecutionTier.TIER_1_REALTIME_LLM
    assert decision["token_cost"] == 6_000_000
    assert decision["rationale"] == "Volume qualifies for Batch API but SLA requirement (<12h) mandates real-time execution"
