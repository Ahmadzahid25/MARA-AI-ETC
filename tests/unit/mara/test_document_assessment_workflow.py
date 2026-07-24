"""Unit tests for workflows/document_assessment/document_assessment.py.

Uses a real LangGraph ``InMemorySaver`` checkpointer (not a mock) to
exercise the actual durable-pause/resume mechanism the graph relies on for
its Approval stage — the same ``interrupt()``/``Command(resume=...)``
primitive shared/workflow_engine/checkpointer.py's Postgres checkpointer
supports in production.
"""

from __future__ import annotations

import io

import pytest
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command
from pypdf import PdfWriter

from agents.compliance_agent.compliance_agent import ComplianceAgent
from agents.document_agent.document_agent import DocumentAgent
from shared.schemas.compliance import ComplianceStatus
from shared.schemas.documents import Citation, ExtractedField, ExtractionSource
from workflows.document_assessment.document_assessment import (
    DocumentAssessmentState,
    build_document_assessment_graph,
)


def _blank_pdf_bytes() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


async def _fake_field_extractor(pages, classification) -> list[ExtractedField]:
    return [
        ExtractedField(
            name='applicant_name',
            value='Ali bin Ahmad',
            confidence=0.6,
            source=ExtractionSource.PDF_TEXT_LAYER,
            citation=Citation(document_id='doc-1', page=1),
        )
    ]


def _initial_state(requirements: list[str] | None = None) -> DocumentAssessmentState:
    return {
        'document_id': 'doc-1',
        'pdf_bytes': _blank_pdf_bytes(),
        'compliance_requirements': requirements or [],
        'extraction_record': None,
        'compliance_checklist': None,
        'validation_notes': [],
        'approval_decision': None,
        'stage_log': [],
    }


def _compiled_graph(calibration_writer=None):
    document_agent = DocumentAgent(
        field_extractor=_fake_field_extractor,
        classifier=lambda _b: ('bank_statement', 0.9),
    )
    compliance_agent = ComplianceAgent()
    graph = build_document_assessment_graph(
        document_agent, compliance_agent, calibration_writer=calibration_writer
    )
    return graph.compile(checkpointer=InMemorySaver())


class TestPauseAtConfirmExtraction:
    @pytest.mark.asyncio
    async def test_workflow_pauses_before_compliance_check(self) -> None:
        compiled = _compiled_graph()
        config = {'configurable': {'thread_id': 'wf-1'}}

        result = await compiled.ainvoke(_initial_state(), config=config)

        assert result['stage_log'] == ['document_extraction', 'validation']
        assert '__interrupt__' in result
        assert result['compliance_checklist'] is None

    @pytest.mark.asyncio
    async def test_interrupt_payload_flags_low_confidence_field(self) -> None:
        compiled = _compiled_graph()
        config = {'configurable': {'thread_id': 'wf-2'}}

        result = await compiled.ainvoke(_initial_state(), config=config)

        payload = result['__interrupt__'][0].value
        assert payload['type'] == 'confirm_extraction'
        assert payload['document_id'] == 'doc-1'
        assert payload['low_confidence_field_names'] == ['applicant_name']


class TestApprovedResumption:
    @pytest.mark.asyncio
    async def test_approval_resumes_into_compliance_check(self) -> None:
        compiled = _compiled_graph()
        config = {'configurable': {'thread_id': 'wf-3'}}
        await compiled.ainvoke(_initial_state(['req-A']), config=config)

        result = await compiled.ainvoke(
            Command(resume={'status': 'approved', 'actor': 'officer-1'}), config=config
        )

        assert result['stage_log'] == [
            'document_extraction',
            'validation',
            'confirm_extraction',
            'compliance_check',
            'completion',
        ]
        assert result['compliance_checklist'] is not None
        assert result['compliance_checklist'].items[0].status == (
            ComplianceStatus.NO_POLICY_FOUND
        )
        assert result['approval_decision']['status'] == 'approved'

    @pytest.mark.asyncio
    async def test_approval_decision_is_recorded_in_final_state(self) -> None:
        compiled = _compiled_graph()
        config = {'configurable': {'thread_id': 'wf-4'}}
        await compiled.ainvoke(_initial_state(), config=config)

        result = await compiled.ainvoke(
            Command(resume={'status': 'approved', 'actor': 'officer-2'}), config=config
        )

        assert result['approval_decision'] == {
            'status': 'approved',
            'actor': 'officer-2',
        }


class TestRejectedResumption:
    @pytest.mark.asyncio
    async def test_rejection_routes_straight_to_completion_without_compliance_check(
        self,
    ) -> None:
        compiled = _compiled_graph()
        config = {'configurable': {'thread_id': 'wf-5'}}
        await compiled.ainvoke(_initial_state(['req-A']), config=config)

        result = await compiled.ainvoke(
            Command(
                resume={'status': 'rejected', 'actor': 'officer-1', 'reason': 'blurry'}
            ),
            config=config,
        )

        assert result['stage_log'] == [
            'document_extraction',
            'validation',
            'confirm_extraction',
            'completion',
        ]
        assert result['compliance_checklist'] is None
        assert result['approval_decision']['status'] == 'rejected'


class TestCorrectedResumption:
    @pytest.mark.asyncio
    async def test_corrected_value_reaches_extraction_record(self) -> None:
        compiled = _compiled_graph()
        config = {'configurable': {'thread_id': 'wf-7'}}
        await compiled.ainvoke(_initial_state(), config=config)

        result = await compiled.ainvoke(
            Command(
                resume={
                    'status': 'approved',
                    'actor': 'officer-1',
                    'corrected_fields': [
                        {
                            'field_name': 'applicant_name',
                            'corrected_value': 'Ali bin Ahmad Jr',
                        }
                    ],
                }
            ),
            config=config,
        )

        corrected = result['extraction_record'].fields[0]
        assert corrected.value == 'Ali bin Ahmad Jr'
        assert corrected.confidence == 1.0
        # Corrected records still flow into the compliance check.
        assert result['compliance_checklist'] is not None


class TestValidationNotes:
    @pytest.mark.asyncio
    async def test_validation_notes_flag_low_confidence_count(self) -> None:
        compiled = _compiled_graph()
        config = {'configurable': {'thread_id': 'wf-6'}}

        result = await compiled.ainvoke(_initial_state(), config=config)

        assert result['validation_notes'] == ['1 field(s) below confidence threshold']


class TestCalibrationWriter:
    @pytest.mark.asyncio
    async def test_approval_emits_calibration_event_marked_not_corrected(self) -> None:
        written = []

        async def fake_calibration_writer(events) -> None:
            written.extend(events)

        compiled = _compiled_graph(calibration_writer=fake_calibration_writer)
        config = {'configurable': {'thread_id': 'wf-8'}}
        await compiled.ainvoke(_initial_state(), config=config)

        await compiled.ainvoke(
            Command(resume={'status': 'approved', 'actor': 'officer-1'}), config=config
        )

        assert len(written) == 1
        event = written[0]
        assert event.field_name == 'applicant_name'
        assert event.stated_confidence == 0.6
        assert event.was_corrected is False
        assert event.agent_name == 'document_agent'
        assert event.document_type == 'bank_statement'

    @pytest.mark.asyncio
    async def test_correction_emits_calibration_event_marked_corrected(self) -> None:
        written = []

        async def fake_calibration_writer(events) -> None:
            written.extend(events)

        compiled = _compiled_graph(calibration_writer=fake_calibration_writer)
        config = {'configurable': {'thread_id': 'wf-9'}}
        await compiled.ainvoke(_initial_state(), config=config)

        await compiled.ainvoke(
            Command(
                resume={
                    'status': 'approved',
                    'actor': 'officer-1',
                    'corrected_fields': [
                        {
                            'field_name': 'applicant_name',
                            'corrected_value': 'Ali bin Ahmad Jr',
                        }
                    ],
                }
            ),
            config=config,
        )

        assert len(written) == 1
        # The calibration signal is the *original* stated confidence against
        # whether it needed correction — not the post-correction confidence.
        assert written[0].stated_confidence == 0.6
        assert written[0].was_corrected is True

    @pytest.mark.asyncio
    async def test_no_calibration_writer_does_not_break_the_workflow(self) -> None:
        compiled = _compiled_graph(calibration_writer=None)
        config = {'configurable': {'thread_id': 'wf-10'}}
        await compiled.ainvoke(_initial_state(), config=config)

        result = await compiled.ainvoke(
            Command(resume={'status': 'approved', 'actor': 'officer-1'}), config=config
        )

        assert result['stage_log'][-1] == 'completion'
