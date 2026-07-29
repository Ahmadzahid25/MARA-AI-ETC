"""Vertical-slice API v1 router.

Provides the minimal auth/applications/officer endpoints frozen by
docs/architecture/17-vertical-slice-execution-directive.md §17.11 so
frontend lanes can integrate against stable contracts.

This module intentionally uses an in-process store as a temporary wiring
surface for the first vertical slice. Replace with DB-backed repositories in
R1/R3 without changing wire contracts.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import os
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import jwt
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from services.approval_service.approval_service import resume_at_gate
from services.api_gateway.dependencies import get_vertical_slice_store
from services.api_gateway.vertical_slice_store import VerticalSliceStore
from shared.schemas.approval import ApprovalAction, ApprovalDecisionInput
from shared.schemas.vertical_slice import (
    ApplicationDetailOutput,
    ApplicationStatus,
    ApplicationStatusOutput,
    AuthLoginInput,
    AuthRegisterInput,
    AuthTokenOutput,
    CreateApplicationInput,
    CreateApplicationOutput,
    OfficerDecisionAction,
    OfficerDecisionInput,
    OfficerDecisionOutput,
    OfficerQueueItem,
    OfficerQueueOutput,
    UserRole,
)

router = APIRouter(prefix='/api/v1', tags=['vertical-slice'])

_bearer = HTTPBearer(auto_error=True)
_JWT_SECRET_ENV = 'MARA_VS_JWT_SECRET'
_JWT_ALGO = 'HS256'
_UPLOAD_DIR_ENV = 'MARA_UPLOAD_DIR'

_upload_file = File(...)
_upload_doc_type = Form(...)


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()


def _jwt_secret() -> str:
    return os.getenv(_JWT_SECRET_ENV, 'dev-only-change-me')


def _issue_token(user_id: str, role: UserRole) -> str:
    now = _utc_now()
    payload = {
        'sub': user_id,
        'role': role.value,
        'iat': int(now.timestamp()),
        'exp': int((now + timedelta(hours=8)).timestamp()),
    }
    return jwt.encode(payload, _jwt_secret(), algorithm=_JWT_ALGO)


def _require_principal(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> dict:
    try:
        payload = jwt.decode(
            credentials.credentials,
            _jwt_secret(),
            algorithms=[_JWT_ALGO],
        )
        role = UserRole(payload['role'])
        return {'user_id': payload['sub'], 'role': role}
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Invalid or expired access token',
        ) from exc


def _require_role(principal: dict, allowed: set[UserRole]) -> None:
    if principal['role'] not in allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Insufficient role for this action',
        )


def _build_loan_initial_state(application: dict, pdf_bytes: bytes) -> dict:
    return {
        'document_id': application['application_id'],
        'pdf_bytes': pdf_bytes,
        'compliance_requirements': [],
        'calculation_requests': [],
        'product_query': None,
        'sector': application['business'].get('sector', 'general'),
        'region': application['applicant'].get('state', 'unknown'),
        'precedent_query': None,
        'extraction_record': None,
        'extraction_decision': None,
        'compliance_checklist': None,
        'compliance_decision': None,
        'financial_analysis': None,
        'financial_decision': None,
        'market_brief': None,
        'risk_rating': None,
        'risk_decision': None,
        'recommendation': None,
        'recommendation_decision': None,
        'published_docx': None,
        'published_pptx': None,
        'publish_decision': None,
        'publish_error': None,
        'stage_log': [],
    }


def _uploads_root() -> Path:
    return Path(os.getenv(_UPLOAD_DIR_ENV, 'workspace/uploads')).resolve()


def _status_from_workflow(
    workflow_state: str,
    pending_gate: str | None,
    *,
    fallback: ApplicationStatus,
) -> ApplicationStatus:
    if workflow_state in {'queued', 'queued_waiting_pdf'}:
        return ApplicationStatus.SUBMITTED
    if workflow_state == 'running':
        return ApplicationStatus.PROCESSING
    if workflow_state == 'failed':
        return ApplicationStatus.NEEDS_INFO
    if workflow_state == 'resume_failed':
        return ApplicationStatus.NEEDS_INFO
    if workflow_state == 'completed':
        return ApplicationStatus.APPROVED
    if workflow_state == 'paused':
        if pending_gate == 'recommendation_approval':
            return ApplicationStatus.UNDER_REVIEW
        return ApplicationStatus.PROCESSING
    return fallback


def _should_retrigger_on_document_upload(application: dict) -> bool:
    workflow = application.get('workflow', {})
    state = workflow.get('state')
    status = application.get('status')
    return (
        state in {'queued_waiting_pdf', 'failed', 'resume_failed'}
        or status == ApplicationStatus.NEEDS_INFO
    )


def _load_first_pdf_bytes(application: dict) -> bytes | None:
    for doc in application['documents']:
        if 'pdf' not in doc.get('mime_type', '').lower():
            continue
        path = Path(doc['file_path'])
        if path.is_file():
            return path.read_bytes()
    return None


async def _run_loan_workflow_for_application(
    application_id: str,
    workflow,
    store: VerticalSliceStore,
) -> None:
    application = await store.get_application(application_id)
    if application is None:
        return

    pdf_bytes = _load_first_pdf_bytes(application)
    if pdf_bytes is None:
        workflow_meta = application['workflow']
        workflow_meta['state'] = 'queued_waiting_pdf'
        await store.update_application(
            application_id,
            status=ApplicationStatus.SUBMITTED,
            stage_log=[*application['stage_log'], 'workflow_waiting_pdf'],
            ai_assessment={
                **application['ai_assessment'],
                'workflow': workflow_meta,
            },
        )
        return

    workflow_meta = application['workflow']
    workflow_meta['state'] = 'running'
    await store.update_application(
        application_id,
        status=ApplicationStatus.PROCESSING,
        stage_log=[*application['stage_log'], 'workflow_started'],
        ai_assessment={
            **application['ai_assessment'],
            'workflow': workflow_meta,
        },
    )

    state = _build_loan_initial_state(application, pdf_bytes)
    config = {'configurable': {'thread_id': application_id}}

    try:
        result = await workflow.ainvoke(state, config=config)
    except Exception as exc:
        current = await store.get_application(application_id)
        if current is not None:
            failed_meta = current['workflow']
            failed_meta['state'] = 'failed'
            failed_meta['error'] = str(exc)
            await store.update_application(
                application_id,
                stage_log=[*current['stage_log'], 'workflow_failed'],
                ai_assessment={
                    **current['ai_assessment'],
                    'workflow': failed_meta,
                },
            )
        return

    interrupts = result.get('__interrupt__') or []
    pending_gate = None
    if interrupts:
        pending_gate = interrupts[0].value.get('type')

    current = await store.get_application(application_id)
    if current is None:
        return
    updated_meta = current['workflow']
    if interrupts:
        updated_meta['state'] = 'paused'
        updated_meta['pending_gate'] = pending_gate
    else:
        updated_meta['state'] = 'completed'
        updated_meta['pending_gate'] = None
    updated_assessment = current['ai_assessment']
    updated_assessment['stage_log'] = result.get('stage_log', [])
    updated_assessment['workflow'] = updated_meta
    recommendation = result.get('recommendation')
    if recommendation is not None:
        if hasattr(recommendation, 'model_dump'):
            updated_assessment['recommendation'] = recommendation.model_dump(
                mode='json'
            )
        else:
            updated_assessment['recommendation'] = recommendation
    await store.update_application(
        application_id,
        status=_status_from_workflow(
            updated_meta['state'],
            updated_meta.get('pending_gate'),
            fallback=ApplicationStatus.PROCESSING,
        ),
        stage_log=[
            *current['stage_log'],
            'workflow_paused' if interrupts else 'workflow_completed',
        ],
        ai_assessment=updated_assessment,
    )


@router.post('/auth/register', response_model=AuthTokenOutput)
async def register(
    body: AuthRegisterInput,
    store: VerticalSliceStore = Depends(get_vertical_slice_store),
) -> AuthTokenOutput:
    email = body.email.strip().lower()
    role = UserRole.APPLICANT
    user = await store.create_user(
        full_name=body.full_name,
        email=email,
        password_hash=_hash_password(body.password),
        role=role,
    )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail='Email already registered',
        )

    user_id = user['user_id']
    token = _issue_token(user_id, role)
    await store.append_audit(
        actor=user_id,
        action='register',
        application_id=None,
        payload={'email': email},
    )
    return AuthTokenOutput(user_id=user_id, role=role, access_token=token)


@router.post('/applications/{application_id}/documents')
async def upload_application_document(
    application_id: str,
    request: Request,
    file: UploadFile = _upload_file,
    doc_type: str = _upload_doc_type,
    principal: dict = Depends(_require_principal),
    store: VerticalSliceStore = Depends(get_vertical_slice_store),
) -> dict:
    _require_role(principal, {UserRole.APPLICANT})
    row = await store.get_application(application_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Not found')
    if row['owner_user_id'] != principal['user_id']:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Forbidden')

    base_name = Path(file.filename or 'upload.bin').name
    saved_name = f"{uuid.uuid4()}-{base_name}"
    target_dir = _uploads_root() / application_id
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / saved_name
    content = await file.read()
    target_path.write_bytes(content)

    doc = await store.add_document(
        application_id,
        doc_type=doc_type,
        file_name=base_name,
        file_path=str(target_path),
        mime_type=file.content_type or 'application/octet-stream',
    )
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Not found')

    updated = await store.get_application(application_id)
    assert updated is not None
    await store.update_application(
        application_id,
        stage_log=[*updated['stage_log'], f'document_uploaded:{doc_type}'],
    )
    await store.append_audit(
        actor=principal['user_id'],
        action='document_uploaded',
        application_id=application_id,
        payload={
            'doc_type': doc_type,
            'file_name': base_name,
        },
    )

    refreshed = await store.get_application(application_id)
    loan_workflow = getattr(request.app.state, 'loan_workflow', None)
    if (
        refreshed is not None
        and loan_workflow is not None
        and _should_retrigger_on_document_upload(refreshed)
    ):
        workflow_meta = refreshed['workflow']
        workflow_meta['state'] = 'queued'
        workflow_meta['pending_gate'] = None
        assessment = refreshed['ai_assessment']
        assessment['workflow'] = workflow_meta
        await store.update_application(
            application_id,
            status=ApplicationStatus.SUBMITTED,
            stage_log=[
                *refreshed['stage_log'],
                'workflow_retriggered_on_document_upload',
            ],
            ai_assessment=assessment,
        )
        asyncio.create_task(
            _run_loan_workflow_for_application(
                application_id,
                loan_workflow,
                store,
            )
        )

    return {
        'application_id': application_id,
        'document': doc,
    }


@router.post('/auth/login', response_model=AuthTokenOutput)
async def login(
    body: AuthLoginInput,
    store: VerticalSliceStore = Depends(get_vertical_slice_store),
) -> AuthTokenOutput:
    email = body.email.strip().lower()
    user = await store.get_user_by_email(email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Invalid credentials',
        )

    expected = user['password_hash']
    supplied = _hash_password(body.password)
    if not hmac.compare_digest(expected, supplied):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Invalid credentials',
        )

    role = user['role']
    token = _issue_token(user['user_id'], role)
    await store.append_audit(
        actor=user['user_id'],
        action='login',
        application_id=None,
        payload={'email': email},
    )
    return AuthTokenOutput(user_id=user['user_id'], role=role, access_token=token)


@router.post('/applications', response_model=CreateApplicationOutput)
async def create_application(
    body: CreateApplicationInput,
    request: Request,
    principal: dict = Depends(_require_principal),
    store: VerticalSliceStore = Depends(get_vertical_slice_store),
) -> CreateApplicationOutput:
    _require_role(principal, {UserRole.APPLICANT})

    row = await store.create_application(
        owner_user_id=principal['user_id'],
        applicant=body.applicant.model_dump(),
        business=body.business.model_dump(),
        financing=body.financing.model_dump(),
        documents=[d.model_dump() for d in body.documents],
    )

    await store.append_audit(
        actor=principal['user_id'],
        action='application_submitted',
        application_id=row['application_id'],
        payload={'status': ApplicationStatus.SUBMITTED.value},
    )

    loan_workflow = getattr(request.app.state, 'loan_workflow', None)
    if loan_workflow is not None:
        asyncio.create_task(
            _run_loan_workflow_for_application(
                row['application_id'], loan_workflow, store
            )
        )

    return CreateApplicationOutput(
        application_id=row['application_id'],
        status=ApplicationStatus.SUBMITTED,
    )


@router.get('/applications/{application_id}', response_model=ApplicationDetailOutput)
async def get_application(
    application_id: str,
    principal: dict = Depends(_require_principal),
    store: VerticalSliceStore = Depends(get_vertical_slice_store),
) -> ApplicationDetailOutput:
    row = await store.get_application(application_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Not found')

    if (
        principal['role'] == UserRole.APPLICANT
        and row['owner_user_id'] != principal['user_id']
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Forbidden')

    return ApplicationDetailOutput(
        application_id=row['application_id'],
        status=row['status'],
        applicant=row['applicant'],
        business=row['business'],
        financing=row['financing'],
        documents=row['documents'],
        ai_assessment=row['ai_assessment'],
        workflow=row['workflow'],
    )


@router.get('/applications/{application_id}/status', response_model=ApplicationStatusOutput)
async def get_application_status(
    application_id: str,
    principal: dict = Depends(_require_principal),
    store: VerticalSliceStore = Depends(get_vertical_slice_store),
) -> ApplicationStatusOutput:
    row = await store.get_application(application_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Not found')

    if (
        principal['role'] == UserRole.APPLICANT
        and row['owner_user_id'] != principal['user_id']
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Forbidden')

    return ApplicationStatusOutput(
        application_id=row['application_id'],
        status=row['status'],
        stage_log=row['stage_log'],
        updated_at=row['updated_at'],
    )


@router.get('/officer/applications', response_model=OfficerQueueOutput)
async def get_officer_queue(
    principal: dict = Depends(_require_principal),
    store: VerticalSliceStore = Depends(get_vertical_slice_store),
) -> OfficerQueueOutput:
    _require_role(principal, {UserRole.OFFICER, UserRole.ADMIN})

    rows = await store.list_applications()
    items = [
        OfficerQueueItem(
            application_id=row['application_id'],
            applicant_name=row['applicant']['full_name'],
            scheme=row['financing']['scheme'],
            amount_requested=row['financing']['amount_requested'],
            status=row['status'],
            updated_at=row['updated_at'],
        )
        for row in rows
    ]
    items.sort(key=lambda item: item.updated_at, reverse=True)
    return OfficerQueueOutput(items=items)


@router.post(
    '/officer/applications/{application_id}/decision',
    response_model=OfficerDecisionOutput,
)
async def officer_decision(
    application_id: str,
    body: OfficerDecisionInput,
    request: Request,
    principal: dict = Depends(_require_principal),
    store: VerticalSliceStore = Depends(get_vertical_slice_store),
) -> OfficerDecisionOutput:
    _require_role(principal, {UserRole.OFFICER, UserRole.ADMIN})
    row = await store.get_application(application_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Not found')

    if body.action == OfficerDecisionAction.APPROVE:
        new_status = ApplicationStatus.UNDER_REVIEW
    elif body.action == OfficerDecisionAction.REJECT:
        new_status = ApplicationStatus.REJECTED
    else:
        new_status = ApplicationStatus.NEEDS_INFO

    now = _utc_now()
    prior_pending_gate = row['workflow'].get('pending_gate')
    updated = await store.record_decision(
        application_id,
        action=body.action,
        reason=body.reason,
        decided_by=principal['user_id'],
        status=new_status,
    )
    if updated is not None:
        row = updated

    if row['workflow'].get('state') == 'paused':
        loan_workflow = getattr(request.app.state, 'loan_workflow', None)
        if loan_workflow is not None and prior_pending_gate:
            if body.action == OfficerDecisionAction.APPROVE:
                mapped_action = ApprovalAction.APPROVE
            else:
                mapped_action = ApprovalAction.REJECT

            decision = ApprovalDecisionInput(
                action=mapped_action,
                actor=principal['user_id'],
                reason=body.reason,
            )
            try:
                result = await resume_at_gate(
                    loan_workflow,
                    application_id,
                    application_id,
                    prior_pending_gate,
                    decision,
                    audit_writer=None,
                )
                interrupts = result.get('__interrupt__') or []
                workflow_meta = row['workflow']
                workflow_meta['pending_gate'] = (
                    interrupts[0].value.get('type') if interrupts else None
                )
                workflow_meta['state'] = 'paused' if interrupts else 'completed'
                updated_assessment = row['ai_assessment']
                updated_assessment['stage_log'] = result.get('stage_log', [])
                updated_assessment['workflow'] = workflow_meta
                row = await store.update_application(
                    application_id,
                    status=_status_from_workflow(
                        workflow_meta['state'],
                        workflow_meta.get('pending_gate'),
                        fallback=new_status,
                    ),
                    ai_assessment=updated_assessment,
                ) or row
            except Exception as exc:
                workflow_meta = row['workflow']
                workflow_meta['state'] = 'resume_failed'
                workflow_meta['error'] = str(exc)
                updated_assessment = row['ai_assessment']
                updated_assessment['workflow'] = workflow_meta
                row = await store.update_application(
                    application_id,
                    status=ApplicationStatus.NEEDS_INFO,
                    ai_assessment=updated_assessment,
                ) or row

    await store.append_audit(
        actor=principal['user_id'],
        action='officer_decision',
        application_id=application_id,
        payload={'action': body.action.value, 'status': row['status'].value},
    )

    return OfficerDecisionOutput(
        application_id=application_id,
        status=row['status'],
        decision_recorded_at=now,
    )
