"""Unit tests for agents/compliance_agent/compliance_agent.py."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from agents.compliance_agent.compliance_agent import (
    ComplianceAgent,
    ComplianceCheckParsingError,
    _parse_llm_check_result,
)
from shared.schemas.compliance import ComplianceStatus
from shared.schemas.documents import (
    Citation,
    DocumentClassification,
    DocumentExtractionRecord,
)


def _record() -> DocumentExtractionRecord:
    return DocumentExtractionRecord(
        document_id='doc-1',
        classification=DocumentClassification(
            document_type='bank_statement', confidence=0.9
        ),
        fields=[],
    )


class TestParseLLMCheckResult:
    def test_valid_pass_result(self) -> None:
        status, notes = _parse_llm_check_result('{"status": "pass", "notes": "ok"}')
        assert status == ComplianceStatus.PASS
        assert notes == 'ok'

    def test_valid_fail_result(self) -> None:
        status, _ = _parse_llm_check_result(
            '{"status": "fail", "notes": "missing doc"}'
        )
        assert status == ComplianceStatus.FAIL

    def test_invalid_json_raises(self) -> None:
        with pytest.raises(ComplianceCheckParsingError):
            _parse_llm_check_result('not json')

    def test_no_policy_found_status_from_checker_rejected(self) -> None:
        # Reserved for the no-citations case, decided before the checker
        # ever runs — a checker claiming it independently is a bug.
        with pytest.raises(ComplianceCheckParsingError):
            _parse_llm_check_result('{"status": "no_policy_found", "notes": "x"}')

    def test_invalid_status_value_raises(self) -> None:
        with pytest.raises(ComplianceCheckParsingError):
            _parse_llm_check_result('{"status": "maybe", "notes": "x"}')


class TestComplianceAgentDefaultStub:
    @pytest.mark.asyncio
    async def test_default_policy_lookup_yields_no_policy_found_for_every_requirement(
        self,
    ) -> None:
        agent = ComplianceAgent()
        checklist = await agent.check_compliance(
            'doc-1', _record(), requirements=['req-A', 'req-B']
        )

        assert len(checklist.items) == 2
        assert all(
            item.status == ComplianceStatus.NO_POLICY_FOUND for item in checklist.items
        )
        assert all(item.policy_citation is None for item in checklist.items)
        assert checklist.has_hard_violation is False

    @pytest.mark.asyncio
    async def test_empty_requirements_yields_empty_checklist(self) -> None:
        agent = ComplianceAgent()
        checklist = await agent.check_compliance('doc-1', _record(), requirements=[])
        assert checklist.items == []
        assert checklist.has_hard_violation is False


class TestComplianceAgentWithInjectedLookupAndChecker:
    @pytest.mark.asyncio
    async def test_hard_violation_is_surfaced(self) -> None:
        async def lookup(requirement: str) -> list[Citation]:
            return [Citation(document_id='policy-1', page=3)]

        async def checker(requirement, citations, record):
            return ComplianceStatus.FAIL, 'business registration expired'

        agent = ComplianceAgent(policy_lookup=lookup, checker=checker)
        checklist = await agent.check_compliance(
            'doc-1', _record(), requirements=['must hold valid business registration']
        )

        assert checklist.has_hard_violation is True
        assert checklist.items[0].policy_citation == Citation(
            document_id='policy-1', page=3
        )

    @pytest.mark.asyncio
    async def test_pass_does_not_count_as_hard_violation(self) -> None:
        async def lookup(requirement: str) -> list[Citation]:
            return [Citation(document_id='policy-1', page=1)]

        async def checker(requirement, citations, record):
            return ComplianceStatus.PASS, 'satisfied'

        agent = ComplianceAgent(policy_lookup=lookup, checker=checker)
        checklist = await agent.check_compliance(
            'doc-1', _record(), requirements=['req-A']
        )

        assert checklist.has_hard_violation is False

    @pytest.mark.asyncio
    async def test_default_checker_calls_llm_with_compliance_tier(self) -> None:
        async def lookup(requirement: str) -> list[Citation]:
            return [Citation(document_id='policy-1', page=1)]

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content='{"status": "pass", "notes": "ok"}'))
        ]
        mock_llm = MagicMock()
        mock_llm.complete_for_agent = AsyncMock(return_value=mock_response)

        agent = ComplianceAgent(llm_client=mock_llm, policy_lookup=lookup)
        checklist = await agent.check_compliance(
            'doc-1', _record(), requirements=['req-A']
        )

        assert checklist.items[0].status == ComplianceStatus.PASS
        mock_llm.complete_for_agent.assert_awaited_once()
        called_agent = mock_llm.complete_for_agent.call_args[0][0]
        assert called_agent.value == 'compliance_agent'
