"""Thin LiteLLM wrapper enforcing model-tiering at the call site.

This is the *only* sanctioned way agent/service code calls an LLM — never
`litellm.acompletion(model=...)` directly with a hardcoded model string. That
constraint is what makes docs/architecture/04-technology-stack.md §4.6.1's
per-agent tier assignment an enforced routing rule rather than a convention
agents are trusted to follow.
"""

from __future__ import annotations

from typing import Any

import litellm

from shared.llm.model_tiers import (
    DEFAULT_TIER_MODEL_CONFIG,
    SERVICE_DEFAULT_TIER,
    AgentName,
    ModelTier,
    TierModelConfig,
)


class TieredLLMClient:
    """Routes every completion call through the agent/service's assigned tier.

    One instance is constructed at process start from ``Settings`` (see
    shared/config) and passed down explicitly, mirroring the reasoning in
    shared/config/settings.py for why config is resolved once, not re-read
    ad hoc mid-workflow.
    """

    def __init__(
        self, tier_model_config: TierModelConfig = DEFAULT_TIER_MODEL_CONFIG
    ) -> None:
        self._tier_model_config = tier_model_config

    async def complete_for_agent(
        self,
        agent: AgentName,
        messages: list[dict[str, str]],
        **litellm_kwargs: Any,
    ) -> litellm.ModelResponse:
        """Completion call attributed to one of the 7 true agents.

        The model used is *not* a caller-supplied parameter — it is derived
        from the agent's fixed tier assignment, closing off the failure mode
        where a new agent's code path accidentally defaults to the largest
        (most expensive) model.
        """

        model = self._tier_model_config.model_for_agent(agent)
        return await litellm.acompletion(
            model=model, messages=messages, **litellm_kwargs
        )

    async def complete_for_service(
        self,
        service_name: str,
        messages: list[dict[str, str]],
        tier: ModelTier = SERVICE_DEFAULT_TIER,
        **litellm_kwargs: Any,
    ) -> litellm.ModelResponse:
        """Completion call for a reclassified service's narrow, optional LLM
        use (e.g. the Audit Service's narrative-summarization layer — docs/
        architecture/05-agent-architecture.md §5.11.3). Defaults to the
        smallest capable tier, since no reclassified service performs the
        kind of ambiguous judgment that would justify a larger model
        (docs/architecture/05-agent-architecture.md §5.14).
        """

        model = self._tier_model_config.model_for_tier(tier)
        return await litellm.acompletion(
            model=model,
            messages=messages,
            metadata={
                'mara_service': service_name,
                **litellm_kwargs.pop('metadata', {}),
            },
            **litellm_kwargs,
        )
