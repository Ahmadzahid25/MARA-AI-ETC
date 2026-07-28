"""Model-tiering strategy — docs/architecture/04-technology-stack.md §4.6.1.

LLM token cost is the dominant cost driver in this platform, and it scales
with agent call volume, not officer headcount (docs/architecture/review/
04-compliance-scale-cost-review.md §10.1). Which model tier each agent uses
is therefore an explicit, reviewed decision here — not left to "use one
capable model everywhere," which is the single most expensive default a
new agent could ship with by accident.

Wraps OpenHands' existing LiteLLM dependency so provider choice stays
swappable per tier without touching agent code (docs/architecture/
04-technology-stack.md §4.1).
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel


class ModelTier(StrEnum):
    """Three tiers, per docs/architecture/04-technology-stack.md §4.6.1."""

    EXTRACTION = 'extraction'
    """High call volume, narrower judgment per call. Haiku-class by default."""

    SYNTHESIS = 'synthesis'
    """Policy interpretation / cross-evidence reasoning. Sonnet-class by default."""

    HIGH_STAKES = 'high_stakes'
    """Lowest call volume, highest stakes. Opus-class by default — reserved
    for the Recommendation Agent only; see docs/architecture/
    05-agent-architecture.md §5.8."""


class AgentName(StrEnum):
    """The 7 true agents — docs/architecture/05-agent-architecture.md §5.14.
    Reclassified components (Supervisor, Publishing, Voice, Audit) are NOT
    listed here: they are services, and if they need any LLM call at all
    (e.g. Audit's narrative-summarization layer, §5.11.3) they route through
    the smallest capable tier explicitly, not through this per-agent map.
    """

    PLANNER = 'planner'
    DOCUMENT = 'document_agent'
    COMPLIANCE = 'compliance_agent'
    FINANCE = 'finance_agent'
    RISK = 'risk_agent'
    MARKET = 'market_agent'
    RECOMMENDATION = 'recommendation_agent'


# Agent -> tier, per the Baseline v1.0 model tier table
# (docs/architecture/05-agent-architecture.md §5.9).
AGENT_TIER: dict[AgentName, ModelTier] = {
    AgentName.PLANNER: ModelTier.EXTRACTION,
    AgentName.DOCUMENT: ModelTier.EXTRACTION,
    AgentName.COMPLIANCE: ModelTier.SYNTHESIS,
    AgentName.FINANCE: ModelTier.SYNTHESIS,
    AgentName.RISK: ModelTier.SYNTHESIS,
    AgentName.MARKET: ModelTier.SYNTHESIS,
    AgentName.RECOMMENDATION: ModelTier.HIGH_STAKES,
}

# The smallest capable tier — the default for any reclassified service's
# optional, narrowly-scoped LLM call (docs/architecture/05-agent-architecture.md
# §5.11.3, the Audit Service's narrative layer).
SERVICE_DEFAULT_TIER = ModelTier.EXTRACTION


class TierModelConfig(BaseModel):
    """Which concrete LiteLLM model string backs each tier.

    Deliberately data, not code: swapping from direct Anthropic API to AWS
    Bedrock for data-residency reasons (docs/architecture/04-technology-stack.md
    §4.6) is a config change here, not a code change anywhere agents live.
    """

    model_by_tier: dict[ModelTier, str] = {
        ModelTier.EXTRACTION: 'anthropic/claude-haiku-4-5',
        ModelTier.SYNTHESIS: 'anthropic/claude-sonnet-5',
        ModelTier.HIGH_STAKES: 'anthropic/claude-opus-4-8',
    }

    openai_model_by_tier: dict[ModelTier, str] = {
        ModelTier.EXTRACTION: 'gpt-4o-mini',
        ModelTier.SYNTHESIS: 'gpt-4o',
        ModelTier.HIGH_STAKES: 'gpt-4o',
    }

    def model_for_tier(self, tier: ModelTier) -> str:
        import os
        if os.environ.get('OPENAI_API_KEY') and not os.environ.get('ANTHROPIC_API_KEY'):
            return self.openai_model_by_tier.get(tier, 'gpt-4o')
        return self.model_by_tier[tier]

    def model_for_agent(self, agent: AgentName) -> str:
        return self.model_for_tier(AGENT_TIER[agent])


DEFAULT_TIER_MODEL_CONFIG = TierModelConfig()

