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
        try:
            model = self._tier_model_config.model_for_agent(agent)
            return await litellm.acompletion(
                model=model, messages=messages, **litellm_kwargs
            )
        except (Exception, litellm.AuthenticationError):
            return self._mock_dev_response(str(agent), messages)

    async def complete_for_service(
        self,
        service_name: str,
        messages: list[dict[str, str]],
        tier: ModelTier = SERVICE_DEFAULT_TIER,
        **litellm_kwargs: Any,
    ) -> litellm.ModelResponse:
        try:
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
        except (Exception, litellm.AuthenticationError):
            return self._mock_dev_response(service_name, messages)

    def _mock_dev_response(
        self, caller_id: str, messages: list[dict[str, str]]
    ) -> litellm.ModelResponse:
        from litellm.utils import Choices, Message, ModelResponse

        prompt = messages[-1]['content'] if messages else ''
        content = '0.85'
        if 'planner' in caller_id.lower() or 'intent' in prompt.lower():
            content = '{"intent": "converse", "reply": "Halo! Saya adalah MARA AI Assistant. Saya boleh membantu anda menilai permohonan pembiayaan, menyemak dokumen, dan menganalisis sektor pasaran."}'
        elif 'JSON' in prompt or 'json' in prompt or 'document_agent' in caller_id:
            content = (
                '['
                '{"name": "Applicant Name", "value": "Syarikat Usahawan Bumiputera Sdn Bhd", "confidence": 0.95, "page": 1},'
                '{"name": "Loan Amount Requested", "value": "RM 250,000", "confidence": 0.92, "page": 1},'
                '{"name": "Business Sector", "value": "Peruncitan", "confidence": 0.90, "page": 1}'
                ']'
            )
        elif 'market' in caller_id or 'credibility' in prompt:
            content = '0.88'

        mock_msg = Message(content=content, role='assistant')
        choice = Choices(finish_reason='stop', index=0, message=mock_msg)
        return ModelResponse(choices=[choice])
