"""Unit tests for services/api_gateway/routers/documents.py and
approvals.py — exercised against a real compiled Document Assessment
workflow graph (InMemorySaver checkpointer, fake tool-level engines), not a
mocked ``ResumableWorkflow``, so these tests prove the actual HTTP -> agent
-> workflow -> approval wiring works end to end.
"""

from __future__ import annotations

import io

from fastapi.testclient import TestClient
from langgraph.checkpoint.memory import InMemorySaver
from pypdf import PdfWriter

from agents.compliance_agent.compliance_agent import ComplianceAgent
from agents.document_agent.document_agent import DocumentAgent
from services.api_gateway.app import create_app
from services.api_gateway.auth import Principal, get_current_principal
from services.approval_service.approval_service import ResumableWorkflow
from shared.schemas.documents import Citation, ExtractedField, ExtractionSource
from shared.schemas.tooling import ToolExternalServiceError
from workflows.document_assessment.document_assessment import (
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
            citation=Citation(document_id='doc', page=1),
        )
    ]


def _build_test_workflow() -> ResumableWorkflow:
    document_agent = DocumentAgent(
        field_extractor=_fake_field_extractor,
        classifier=lambda _b: ('bank_statement', 0.9),
    )
    graph = build_document_assessment_graph(document_agent, ComplianceAgent())
    return graph.compile(checkpointer=InMemorySaver())


_FAKE_PRINCIPAL = Principal(subject='officer-1', realm_roles=frozenset({'officer'}))


class TestStartAssessmentAndDecide:
    def test_upload_pauses_at_confirm_extraction(self) -> None:
        app = create_app(workflow=_build_test_workflow())
        app.dependency_overrides[get_current_principal] = lambda: _FAKE_PRINCIPAL

        with TestClient(app) as client:
            response = client.post(
                '/documents/assessments',
                files={'file': ('doc.pdf', _blank_pdf_bytes(), 'application/pdf')},
            )

        assert response.status_code == 200
        body = response.json()
        assert body['status'] == 'pending_confirmation'
        assert body['low_confidence_field_names'] == ['applicant_name']
        assert 'thread_id' in body

    def test_approve_completes_the_workflow(self) -> None:
        app = create_app(workflow=_build_test_workflow())
        app.dependency_overrides[get_current_principal] = lambda: _FAKE_PRINCIPAL

        with TestClient(app) as client:
            start = client.post(
                '/documents/assessments',
                files={'file': ('doc.pdf', _blank_pdf_bytes(), 'application/pdf')},
            )
            thread_id = start.json()['thread_id']

            decision = client.post(
                f'/documents/assessments/{thread_id}/decision',
                json={'action': 'approve'},
            )

        assert decision.status_code == 200
        body = decision.json()
        assert body['status'] == 'completed'
        assert body['stage_log'][-1] == 'completion'

    def test_reject_completes_without_compliance_check(self) -> None:
        app = create_app(workflow=_build_test_workflow())
        app.dependency_overrides[get_current_principal] = lambda: _FAKE_PRINCIPAL

        with TestClient(app) as client:
            start = client.post(
                '/documents/assessments',
                files={'file': ('doc.pdf', _blank_pdf_bytes(), 'application/pdf')},
            )
            thread_id = start.json()['thread_id']

            decision = client.post(
                f'/documents/assessments/{thread_id}/decision',
                json={'action': 'reject', 'reason': 'blurry scan'},
            )

        assert decision.status_code == 200
        assert 'compliance_check' not in decision.json()['stage_log']

    def test_correct_requires_at_least_one_correction(self) -> None:
        app = create_app(workflow=_build_test_workflow())
        app.dependency_overrides[get_current_principal] = lambda: _FAKE_PRINCIPAL

        with TestClient(app) as client:
            start = client.post(
                '/documents/assessments',
                files={'file': ('doc.pdf', _blank_pdf_bytes(), 'application/pdf')},
            )
            thread_id = start.json()['thread_id']

            # No corrections attached — the shared ApprovalDecisionInput
            # schema (shared/schemas/approval.py) rejects this before the
            # request even reaches the workflow.
            response = client.post(
                f'/documents/assessments/{thread_id}/decision',
                json={'action': 'correct'},
            )

        assert response.status_code >= 400


class TestAuthRequired:
    def test_upload_without_auth_is_rejected(self) -> None:
        app = create_app(workflow=_build_test_workflow())
        # No dependency override — the real auth dependency runs.

        with TestClient(app) as client:
            response = client.post(
                '/documents/assessments',
                files={'file': ('doc.pdf', _blank_pdf_bytes(), 'application/pdf')},
            )

        assert response.status_code in (401, 403)


class TestToolErrorMapping:
    def test_external_service_error_maps_to_503(self) -> None:
        class _BrokenWorkflow:
            async def ainvoke(self, input, config):  # noqa: A002
                raise ToolExternalServiceError('no OCR engine wired')

        app = create_app(workflow=_BrokenWorkflow())
        app.dependency_overrides[get_current_principal] = lambda: _FAKE_PRINCIPAL

        with TestClient(app) as client:
            response = client.post(
                '/documents/assessments',
                files={'file': ('doc.pdf', _blank_pdf_bytes(), 'application/pdf')},
            )

        assert response.status_code == 503
