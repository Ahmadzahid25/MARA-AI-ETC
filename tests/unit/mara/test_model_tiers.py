"""Smoke tests for the model-tiering routing rule — docs/architecture/
04-technology-stack.md §4.6.1. These exist specifically to make the tier
table a tested invariant, not just a comment: a future PR that accidentally
routes a new high-volume agent through the Opus-class tier should fail CI,
not get caught in a later cost review.
"""

from __future__ import annotations

from shared.llm.model_tiers import (
    AGENT_TIER,
    DEFAULT_TIER_MODEL_CONFIG,
    AgentName,
    ModelTier,
)


def test_every_true_agent_has_an_assigned_tier() -> None:
    for agent in AgentName:
        assert agent in AGENT_TIER


def test_recommendation_agent_is_the_only_high_stakes_tier_agent() -> None:
    high_stakes_agents = [agent for agent, tier in AGENT_TIER.items() if tier == ModelTier.HIGH_STAKES]
    assert high_stakes_agents == [AgentName.RECOMMENDATION]


def test_document_and_planner_use_the_extraction_tier() -> None:
    assert AGENT_TIER[AgentName.DOCUMENT] == ModelTier.EXTRACTION
    assert AGENT_TIER[AgentName.PLANNER] == ModelTier.EXTRACTION


def test_every_tier_resolves_to_a_concrete_model() -> None:
    for tier in ModelTier:
        model = DEFAULT_TIER_MODEL_CONFIG.model_for_tier(tier)
        assert isinstance(model, str) and model
