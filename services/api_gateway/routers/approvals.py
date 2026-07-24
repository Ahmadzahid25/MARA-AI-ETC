"""Submitting an officer's decision on a paused Document Assessment —
docs/architecture/10-human-in-the-loop.md §10.5's three actions
(Approve/Reject/Correct). Thin HTTP wrapper over
``services/approval_service``; ``actor`` is always taken from the
authenticated principal, never trusted from the request body — an officer
must not be able to submit a decision attributed to someone else.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, ValidationError

from services.api_gateway.auth import Principal, get_current_principal
from services.api_gateway.dependencies import get_audit_writer, get_workflow
from services.api_gateway.errors import to_http_exception
from services.api_gateway.serialization import serialize_workflow_result
from services.approval_service.approval_service import (
    AsyncAuditWriter,
    ResumableWorkflow,
    confirm_extraction,
)
from shared.schemas.approval import (
    ApprovalAction,
    ApprovalDecisionInput,
    FieldCorrection,
)
from shared.schemas.tooling import ToolError

router = APIRouter(prefix='/documents', tags=['documents'])


class ApprovalDecisionRequest(BaseModel):
    """Wire shape for a decision submission — deliberately excludes
    ``actor``; see module docstring."""

    action: ApprovalAction
    reason: str = Field(default='')
    corrections: list[FieldCorrection] = Field(default_factory=list)


@router.post('/assessments/{thread_id}/decision')
async def submit_decision(
    thread_id: str,
    body: ApprovalDecisionRequest,
    principal: Principal = Depends(get_current_principal),
    workflow: ResumableWorkflow = Depends(get_workflow),
    audit_writer: AsyncAuditWriter | None = Depends(get_audit_writer),
) -> dict:
    try:
        decision = ApprovalDecisionInput(
            action=body.action,
            actor=principal.subject,
            reason=body.reason,
            corrections=body.corrections,
        )
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc

    try:
        result = await confirm_extraction(
            workflow, thread_id, thread_id, decision, audit_writer=audit_writer
        )
    except ToolError as exc:
        raise to_http_exception(exc) from exc

    return serialize_workflow_result(thread_id, result)
