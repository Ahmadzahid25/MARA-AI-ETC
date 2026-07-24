"""Unit tests for services/approval_service/approval_service.py.

Includes a real end-to-end integration test against the actual
Document Assessment workflow graph (not just a mocked ``ResumableWorkflow``)
to prove approval_service's resume payload genuinely round-trips through
LangGraph's interrupt/resume mechanism the workflow relies on — services/
approval_service.py itself doesn't import workflows/ (dependency rule,
docs/architecture/03-repository-structure.md §3.3), but this test file is
free to wire both together to verify the contract between them.
"""

from __future__ import annotations

import io
from unittest.mock import AsyncMock

import pytest
from langgraph.checkpoint.memory import InMemorySaver
from pydantic import ValidationError
from pypdf import PdfWriter

from services.approval_service.approval_service import (
    _resume_payload,
    build_correction_decision,
    confirm_extraction,
)
from shared.schemas.approval import (
    ApprovalAction,
    ApprovalDecisionInput,
    FieldCorrection,
)


class TestApprovalDecisionInputValidation:
    def test_approve_without_corrections_is_valid(self) -> None:
        decision = ApprovalDecisionInput(
            action=ApprovalAction.APPROVE, actor='officer-1'
        )
        assert decision.corrections == []

    def test_reject_without_corrections_is_valid(self) -> None:
        decision = ApprovalDecisionInput(
            action=ApprovalAction.REJECT, actor='officer-1', reason='blurry scan'
        )
        assert decision.action == ApprovalAction.REJECT

    def test_correct_without_corrections_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ApprovalDecisionInput(action=ApprovalAction.CORRECT, actor='officer-1')

    def test_approve_with_corrections_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ApprovalDecisionInput(
                action=ApprovalAction.APPROVE,
                actor='officer-1',
                corrections=[FieldCorrection(field_name='x', corrected_value='y')],
            )

    def test_correct_with_corrections_is_valid(self) -> None:
        decision = ApprovalDecisionInput(
            action=ApprovalAction.CORRECT,
            actor='officer-1',
            corrections=[FieldCorrection(field_name='x', corrected_value='y')],
        )
        assert len(decision.corrections) == 1


class TestBuildCorrectionDecision:
    def test_builds_a_correct_action(self) -> None:
        decision = build_correction_decision(
            'officer-1', [FieldCorrection(field_name='x', corrected_value='y')]
        )
        assert decision.action == ApprovalAction.CORRECT
        assert decision.actor == 'officer-1'


class TestResumePayload:
    def test_approve_maps_to_approved_status(self) -> None:
        decision = ApprovalDecisionInput(
            action=ApprovalAction.APPROVE, actor='officer-1'
        )
        assert _resume_payload(decision)['status'] == 'approved'

    def test_reject_maps_to_rejected_status(self) -> None:
        decision = ApprovalDecisionInput(
            action=ApprovalAction.REJECT, actor='officer-1'
        )
        assert _resume_payload(decision)['status'] == 'rejected'

    def test_correct_maps_to_approved_status_with_corrected_fields(self) -> None:
        decision = build_correction_decision(
            'officer-1', [FieldCorrection(field_name='x', corrected_value='y')]
        )
        payload = _resume_payload(decision)
        assert payload['status'] == 'approved'
        assert payload['corrected_fields'] == [
            {'field_name': 'x', 'corrected_value': 'y'}
        ]


class TestConfirmExtractionWithMockedWorkflow:
    @pytest.mark.asyncio
    async def test_resumes_workflow_with_correct_thread_id(self) -> None:
        mock_workflow = AsyncMock()
        mock_workflow.ainvoke = AsyncMock(return_value={'stage_log': ['completion']})
        decision = ApprovalDecisionInput(
            action=ApprovalAction.APPROVE, actor='officer-1'
        )

        result = await confirm_extraction(mock_workflow, 'wf-1', 'doc-1', decision)

        assert result == {'stage_log': ['completion']}
        mock_workflow.ainvoke.assert_awaited_once()
        _, kwargs = mock_workflow.ainvoke.call_args
        assert kwargs['config'] == {'configurable': {'thread_id': 'wf-1'}}

    @pytest.mark.asyncio
    async def test_audit_sink_receives_record_before_resume(self) -> None:
        captured = []
        mock_workflow = AsyncMock()
        mock_workflow.ainvoke = AsyncMock(return_value={})
        decision = ApprovalDecisionInput(
            action=ApprovalAction.REJECT, actor='officer-2', reason='needs rescan'
        )

        await confirm_extraction(
            mock_workflow, 'wf-2', 'doc-2', decision, audit_sink=captured.append
        )

        assert len(captured) == 1
        assert captured[0].tool_name == 'approval_decision'
        assert captured[0].caller_agent == 'officer-2'
        assert captured[0].workflow_id == 'wf-2'

    @pytest.mark.asyncio
    async def test_audit_writer_takes_priority_over_audit_sink(self) -> None:
        written = []
        sink_captured = []
        mock_workflow = AsyncMock()
        mock_workflow.ainvoke = AsyncMock(return_value={})
        decision = ApprovalDecisionInput(
            action=ApprovalAction.APPROVE, actor='officer-3'
        )

        async def fake_audit_writer(record) -> None:
            written.append(record)

        await confirm_extraction(
            mock_workflow,
            'wf-3',
            'doc-3',
            decision,
            audit_sink=sink_captured.append,
            audit_writer=fake_audit_writer,
        )

        assert len(written) == 1
        assert written[0].actor == 'officer-3'
        assert written[0].workflow_thread_id == 'wf-3'
        assert sink_captured == []  # sink fallback not used when writer given

    @pytest.mark.asyncio
    async def test_audit_writer_is_awaited_before_workflow_resumes(self) -> None:
        call_order = []
        mock_workflow = AsyncMock()

        async def fake_ainvoke(*args, **kwargs):
            call_order.append('resume')
            return {}

        mock_workflow.ainvoke = fake_ainvoke
        decision = ApprovalDecisionInput(
            action=ApprovalAction.APPROVE, actor='officer-4'
        )

        async def fake_audit_writer(record) -> None:
            call_order.append('audit')

        await confirm_extraction(
            mock_workflow, 'wf-4', 'doc-4', decision, audit_writer=fake_audit_writer
        )

        assert call_order == ['audit', 'resume']


class TestConfirmExtractionEndToEndWithRealWorkflow:
    """Real integration: approval_service.confirm_extraction() resuming an
    actually-paused workflows.document_assessment graph."""

    @pytest.mark.asyncio
    async def test_approve_resumes_real_workflow_into_compliance_check(self) -> None:
        from agents.compliance_agent.compliance_agent import ComplianceAgent
        from agents.document_agent.document_agent import DocumentAgent
        from shared.schemas.documents import Citation, ExtractedField, ExtractionSource
        from workflows.document_assessment.document_assessment import (
            build_document_assessment_graph,
        )

        async def fake_extractor(pages, classification):
            return [
                ExtractedField(
                    name='n',
                    value='v',
                    confidence=0.5,
                    source=ExtractionSource.PDF_TEXT_LAYER,
                    citation=Citation(document_id='doc-1', page=1),
                )
            ]

        document_agent = DocumentAgent(
            field_extractor=fake_extractor,
            classifier=lambda _b: ('bank_statement', 0.9),
        )
        compiled = build_document_assessment_graph(
            document_agent, ComplianceAgent()
        ).compile(checkpointer=InMemorySaver())

        writer = PdfWriter()
        writer.add_blank_page(width=200, height=200)
        buffer = io.BytesIO()
        writer.write(buffer)

        config = {'configurable': {'thread_id': 'wf-integration'}}
        initial_state = {
            'document_id': 'doc-1',
            'pdf_bytes': buffer.getvalue(),
            'compliance_requirements': [],
            'extraction_record': None,
            'compliance_checklist': None,
            'validation_notes': [],
            'approval_decision': None,
            'stage_log': [],
        }
        paused = await compiled.ainvoke(initial_state, config=config)
        assert '__interrupt__' in paused

        decision = ApprovalDecisionInput(
            action=ApprovalAction.APPROVE, actor='officer-1'
        )
        result = await confirm_extraction(compiled, 'wf-integration', 'doc-1', decision)

        assert result['stage_log'][-1] == 'completion'
        assert result['compliance_checklist'] is not None
