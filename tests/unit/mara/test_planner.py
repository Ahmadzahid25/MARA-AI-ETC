"""Unit tests for agents/planner/planner.py."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from agents.planner.planner import KNOWN_TEMPLATES, Planner, PlanParsingError


async def _fixed_matcher(template_name: str | None, confidence: float):
    async def matcher(objective, templates):
        return template_name, confidence

    return matcher


class TestPlanSelection:
    @pytest.mark.asyncio
    async def test_confident_match_with_all_parameters_selects_template(self) -> None:
        planner = Planner(matcher=await _fixed_matcher('document_assessment', 0.9))

        result = await planner.plan(
            'review this uploaded document',
            parameters={'document_id': 'doc-1', 'pdf_bytes': b'...'},
        )

        assert result.template_name == 'document_assessment'
        assert result.confidence == 0.9
        assert result.is_escalated is False
        assert result.clarification_question is None

    @pytest.mark.asyncio
    async def test_below_threshold_confidence_escalates(self) -> None:
        planner = Planner(matcher=await _fixed_matcher('document_assessment', 0.5))

        result = await planner.plan('do something vague')

        assert result.is_escalated is True
        assert result.template_name is None
        assert result.clarification_question is not None

    @pytest.mark.asyncio
    async def test_no_match_escalates(self) -> None:
        planner = Planner(matcher=await _fixed_matcher(None, 0.0))

        result = await planner.plan('completely unrelated request')

        assert result.is_escalated is True

    @pytest.mark.asyncio
    async def test_missing_required_parameter_escalates(self) -> None:
        planner = Planner(matcher=await _fixed_matcher('loan_assessment', 0.95))

        result = await planner.plan(
            'assess this loan application', parameters={'document_id': 'doc-1'}
        )

        assert result.is_escalated is True
        assert 'compliance_requirements' in result.clarification_question
        assert 'pdf_bytes' in result.clarification_question

    @pytest.mark.asyncio
    async def test_default_matcher_calls_llm_with_planner_tier(self) -> None:
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content='{"template_name": "market_research", "confidence": 0.8}'
                )
            )
        ]
        mock_llm = MagicMock()
        mock_llm.complete_for_agent = AsyncMock(return_value=mock_response)

        planner = Planner(llm_client=mock_llm)
        result = await planner.plan(
            'what is the outlook for the F&B sector',
            parameters={'sector': 'F&B', 'region': 'Klang Valley'},
        )

        assert result.template_name == 'market_research'
        called_agent = mock_llm.complete_for_agent.call_args[0][0]
        assert called_agent.value == 'planner'

    @pytest.mark.asyncio
    async def test_matcher_selecting_unknown_template_raises(self) -> None:
        planner = Planner(matcher=await _fixed_matcher('not_a_real_template', 0.9))

        with pytest.raises(PlanParsingError):
            await planner.plan('some objective')


class TestKnownTemplates:
    def test_catalogue_has_eight_entries(self) -> None:
        assert len(KNOWN_TEMPLATES) == 8

    def test_loan_assessment_requires_compliance_requirements(self) -> None:
        template = next(t for t in KNOWN_TEMPLATES if t.name == 'loan_assessment')
        assert 'compliance_requirements' in template.required_parameters
