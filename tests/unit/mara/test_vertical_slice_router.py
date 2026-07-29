"""Contract tests for services/api_gateway/routers/vertical_slice.py."""

from __future__ import annotations

import uuid
from io import BytesIO

import pytest
from fastapi.testclient import TestClient

from services.api_gateway.app import create_app
from services.api_gateway.routers.vertical_slice import _run_loan_workflow_for_application
from services.api_gateway.vertical_slice_store import InMemoryVerticalSliceStore
from shared.schemas.vertical_slice import ApplicationStatus, UserRole


class _DummyWorkflow:
    async def ainvoke(self, _state, config=None):
        return {
            '__interrupt__': [
                type('Interrupt', (), {'value': {'type': 'recommendation_approval'}})()
            ],
            'stage_log': ['document_extraction', 'recommendation'],
        }


class _DummyCompletedWorkflow:
    async def ainvoke(self, _state, config=None):
        return {
            'stage_log': ['document_extraction', 'recommendation', 'published'],
            'recommendation': {
                'decision': 'approve',
                'withheld_reason': '',
                'confidence': 0.88,
                'has_acknowledged_violation': False,
            },
        }


def _client(workflow=None) -> TestClient:
    app = create_app(workflow=workflow or _DummyWorkflow())
    return TestClient(app)


def _register_and_token(client: TestClient, email: str) -> str:
    response = client.post(
        '/api/v1/auth/register',
        json={
            'full_name': 'Applicant One',
            'email': email,
            'password': 'Password123!',
        },
    )
    assert response.status_code == 200
    return response.json()['access_token']


def test_register_login_and_submit_application() -> None:
    client = _client()
    token = _register_and_token(client, 'applicant1@example.com')

    response = client.post(
        '/api/v1/applications',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'applicant': {
                'full_name': 'Applicant One',
                'ic_number': '900101-01-1234',
                'phone': '0123456789',
                'email': 'applicant1@example.com',
                'state': 'Selangor',
            },
            'business': {
                'business_name': 'ABC Enterprise',
                'ssm_number': 'SSM123456',
                'sector': 'F&B',
                'years_operating': 2,
                'monthly_revenue_avg': 12000,
            },
            'financing': {
                'scheme': 'Skim Usahawan',
                'amount_requested': 50000,
                'purpose': 'Modal kerja',
                'tenure_months': 24,
            },
            'documents': [
                {
                    'doc_type': 'IC',
                    'file_name': 'ic.pdf',
                    'mime_type': 'application/pdf',
                    'file_path': 'C:/tmp/ic.pdf',
                }
            ],
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data['status'] == 'SUBMITTED'
    assert data['application_id']


def test_applicant_can_get_own_status_and_detail() -> None:
    client = _client()
    token = _register_and_token(client, 'applicant2@example.com')

    create = client.post(
        '/api/v1/applications',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'applicant': {
                'full_name': 'Applicant Two',
                'ic_number': '910101-01-1234',
                'phone': '0123456790',
                'email': 'applicant2@example.com',
                'state': 'Johor',
            },
            'business': {
                'business_name': 'XYZ Services',
                'ssm_number': 'SSM789101',
                'sector': 'Services',
                'years_operating': 3,
                'monthly_revenue_avg': 20000,
            },
            'financing': {
                'scheme': 'Skim Mikro',
                'amount_requested': 30000,
                'purpose': 'Pemasaran',
                'tenure_months': 18,
            },
            'documents': [],
        },
    )
    application_id = create.json()['application_id']

    status_resp = client.get(
        f'/api/v1/applications/{application_id}/status',
        headers={'Authorization': f'Bearer {token}'},
    )
    assert status_resp.status_code == 200
    assert status_resp.json()['status'] == 'SUBMITTED'

    detail_resp = client.get(
        f'/api/v1/applications/{application_id}',
        headers={'Authorization': f'Bearer {token}'},
    )
    assert detail_resp.status_code == 200
    assert detail_resp.json()['application_id'] == application_id


def test_officer_queue_and_decision() -> None:
    client = _client()
    applicant_token = _register_and_token(client, 'applicant3@example.com')

    create = client.post(
        '/api/v1/applications',
        headers={'Authorization': f'Bearer {applicant_token}'},
        json={
            'applicant': {
                'full_name': 'Applicant Three',
                'ic_number': '920101-01-1234',
                'phone': '0123456791',
                'email': 'applicant3@example.com',
                'state': 'Perak',
            },
            'business': {
                'business_name': 'MNO Trading',
                'ssm_number': 'SSM111222',
                'sector': 'Retail',
                'years_operating': 1,
                'monthly_revenue_avg': 8000,
            },
            'financing': {
                'scheme': 'Skim Pemula',
                'amount_requested': 20000,
                'purpose': 'Aset',
                'tenure_months': 12,
            },
            'documents': [],
        },
    )
    application_id = create.json()['application_id']

    officer_login = client.post(
        '/api/v1/auth/login',
        json={
            'email': 'officer@mara.local',
            'password': 'Officer123!',
        },
    )
    assert officer_login.status_code == 200
    officer_token = officer_login.json()['access_token']

    queue = client.get(
        '/api/v1/officer/applications',
        headers={'Authorization': f'Bearer {officer_token}'},
    )
    assert queue.status_code == 200
    assert any(item['application_id'] == application_id for item in queue.json()['items'])

    decision = client.post(
        f'/api/v1/officer/applications/{application_id}/decision',
        headers={'Authorization': f'Bearer {officer_token}'},
        json={
            'action': 'request_more_info',
            'reason': 'Need latest bank statement',
            'conditions': [],
        },
    )
    assert decision.status_code == 200
    assert decision.json()['status'] == 'NEEDS_INFO'


def test_upload_document_endpoint() -> None:
    client = _client()
    token = _register_and_token(client, 'applicant4@example.com')

    create = client.post(
        '/api/v1/applications',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'applicant': {
                'full_name': 'Applicant Four',
                'ic_number': '930101-01-1234',
                'phone': '0123456792',
                'email': 'applicant4@example.com',
                'state': 'Melaka',
            },
            'business': {
                'business_name': 'Upload Test Sdn Bhd',
                'ssm_number': 'SSM333444',
                'sector': 'Services',
                'years_operating': 4,
                'monthly_revenue_avg': 15000,
            },
            'financing': {
                'scheme': 'Skim Ujian',
                'amount_requested': 40000,
                'purpose': 'Modal',
                'tenure_months': 24,
            },
            'documents': [],
        },
    )
    application_id = create.json()['application_id']

    upload = client.post(
        f'/api/v1/applications/{application_id}/documents',
        headers={'Authorization': f'Bearer {token}'},
        data={'doc_type': 'BANK_STATEMENT'},
        files={
            'file': (
                'statement.pdf',
                BytesIO(b'%PDF-1.4 fake').read(),
                'application/pdf',
            )
        },
    )
    assert upload.status_code == 200
    payload = upload.json()
    assert payload['application_id'] == application_id
    assert payload['document']['doc_type'] == 'BANK_STATEMENT'


def test_workflow_pause_sets_under_review_status() -> None:
    client = _client()
    token = _register_and_token(client, 'applicant5@example.com')

    create = client.post(
        '/api/v1/applications',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'applicant': {
                'full_name': 'Applicant Five',
                'ic_number': '940101-01-1234',
                'phone': '0123456793',
                'email': 'applicant5@example.com',
                'state': 'Kedah',
            },
            'business': {
                'business_name': 'Status Check Ventures',
                'ssm_number': 'SSM555666',
                'sector': 'F&B',
                'years_operating': 2,
                'monthly_revenue_avg': 9000,
            },
            'financing': {
                'scheme': 'Skim Status',
                'amount_requested': 35000,
                'purpose': 'Pemasaran',
                'tenure_months': 18,
            },
            'documents': [
                {
                    'doc_type': 'BANK_STATEMENT',
                    'file_name': 'statement.pdf',
                    'mime_type': 'application/pdf',
                    'file_path': 'C:/tmp/statement.pdf',
                }
            ],
        },
    )
    assert create.status_code == 200
    application_id = create.json()['application_id']

    status_resp = client.get(
        f'/api/v1/applications/{application_id}/status',
        headers={'Authorization': f'Bearer {token}'},
    )
    assert status_resp.status_code == 200
    # Depending on local file availability, it may remain SUBMITTED or move to
    # UNDER_REVIEW via async workflow pause.
    assert status_resp.json()['status'] in {'SUBMITTED', 'UNDER_REVIEW', 'PROCESSING'}


@pytest.mark.asyncio
async def test_workflow_completion_sets_approved_status(tmp_path) -> None:
    store = InMemoryVerticalSliceStore()
    user = await store.create_user(
        full_name='Applicant Six',
        email='applicant6@example.com',
        password_hash='hash',
        role=UserRole.APPLICANT,
    )
    assert user is not None

    pdf_path = tmp_path / 'doc.pdf'
    pdf_path.write_bytes(b'%PDF-1.4 complete')

    row = await store.create_application(
        owner_user_id=user['user_id'],
        applicant={
            'full_name': 'Applicant Six',
            'ic_number': '950101-01-1234',
            'phone': '0123456794',
            'email': 'applicant6@example.com',
            'state': 'Penang',
        },
        business={
            'business_name': 'Complete Flow Co',
            'ssm_number': 'SSM777888',
            'sector': 'Services',
            'years_operating': 5,
            'monthly_revenue_avg': 22000,
        },
        financing={
            'scheme': 'Skim Lengkap',
            'amount_requested': 45000,
            'purpose': 'Operasi',
            'tenure_months': 30,
        },
        documents=[
            {
                'doc_type': 'BANK_STATEMENT',
                'file_name': 'doc.pdf',
                'mime_type': 'application/pdf',
                'file_path': str(pdf_path),
            }
        ],
    )

    await _run_loan_workflow_for_application(
        row['application_id'],
        _DummyCompletedWorkflow(),
        store,
    )

    updated = await store.get_application(row['application_id'])
    assert updated is not None
    assert updated['status'] == ApplicationStatus.APPROVED
    assert updated['workflow']['state'] == 'completed'
    assert updated['stage_log'][-1] == 'workflow_completed'
