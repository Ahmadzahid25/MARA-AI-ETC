"""Loan Assessment — docs/architecture/07-workflow-architecture.md §7.2's
reference workflow, exposed over HTTP.

The graph itself (workflows/loan_assessment) has existed and been tested for a
while; nothing could invoke it. Seven agents and six approval gates were
reachable only from a test harness, which meant no officer could run one and
the frontend had no endpoint to build the Review Console against.

Two endpoints, mirroring the Document Assessment pair:

- ``POST /loans/assessments`` starts an instance and runs until the first gate.
- ``POST /loans/assessments/{thread_id}/decision`` resumes it at whichever gate
  it is currently paused at.

**The client does not say which gate it is answering.** The pending gate is read
from the workflow's own checkpointed state, then checked against the roles §10.2
assigns to it (shared/auth/approval_gates.py). Accepting a client-supplied gate
would let a caller nominate whichever gate they happen to hold the role for —
the control inverted. That is the whole reason this router depends on
``InspectableWorkflow`` rather than ``ResumableWorkflow``.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, Field, ValidationError

from services.api_gateway.auth import Principal, get_current_principal
from services.api_gateway.dependencies import get_audit_writer, get_loan_workflow
from services.api_gateway.errors import to_http_exception
from services.api_gateway.serialization import serialize_loan_result
from services.approval_service.approval_service import (
    AsyncAuditWriter,
    InspectableWorkflow,
    resume_at_gate,
)
from shared.auth import ApprovalGate, UnauthorizedForGateError, authorize_gate
from shared.schemas.approval import (
    ApprovalAction,
    ApprovalDecisionInput,
    FieldCorrection,
)
from shared.schemas.tooling import ToolError

router = APIRouter(prefix='/loans', tags=['loans'])


class LoanDecisionRequest(BaseModel):
    """Wire shape for a decision. Deliberately carries no ``actor`` and no
    gate name: the actor comes from the verified token, and the gate from the
    workflow's own state — both are authorization inputs, and neither may be
    something the caller asserts about themselves."""

    action: ApprovalAction
    reason: str = Field(default='')
    corrections: list[FieldCorrection] = Field(default_factory=list)


# Module-level singletons rather than calls inline in signature defaults
# (ruff B008) — same dependencies, just not re-constructed on every import.
_file_upload = File(...)
_sector = Form(...)
_region = Form(...)
_requirements = Form(default_factory=list)
_product_query = Form(default=None)
_precedent_query = Form(default=None)


async def pending_gate(workflow: InspectableWorkflow, thread_id: str) -> ApprovalGate:
    """The gate this workflow instance is currently paused at.

    Raises 409 when nothing is pending — a decision submitted against a
    workflow that is finished, never started, or mid-execution is a client
    sequencing error, not a server fault, and saying so beats resuming into
    an undefined state.
    """

    snapshot = await workflow.aget_state({'configurable': {'thread_id': thread_id}})
    interrupts = getattr(snapshot, 'interrupts', ()) or ()
    if not interrupts:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f'Workflow {thread_id!r} is not paused at an approval gate.',
        )

    raw_type = interrupts[0].value.get('type')
    try:
        return ApprovalGate(raw_type)
    except ValueError as exc:
        # A gate the workflow can reach but shared/auth has no role rule for.
        # 500 rather than letting it through: an unmapped gate means nobody
        # decided who may approve it, and defaulting to "anyone" is the one
        # answer that must never be automatic.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Workflow paused at unrecognised gate {raw_type!r}; no '
            f'approval role is defined for it in shared/auth/approval_gates.py.',
        ) from exc


@router.post('/assessments')
async def start_loan_assessment(
    file: UploadFile = _file_upload,
    sector: str = _sector,
    region: str = _region,
    compliance_requirements: list[str] = _requirements,
    product_query: str | None = _product_query,
    precedent_query: str | None = _precedent_query,
    principal: Principal = Depends(get_current_principal),
    workflow: InspectableWorkflow = Depends(get_loan_workflow),
) -> dict:
    """Start a Loan Assessment and run to the first approval gate.

    ``sector`` and ``region`` are required because the Market Agent is scoped
    to them and — per §6.6 — must never receive applicant-identifying detail;
    taking them as explicit, generalized fields is what keeps an applicant's
    business name from reaching an outbound search in the first place.

    ``calculation_requests`` is not accepted over HTTP yet, so the workflow
    runs with none and the Finance Agent produces a qualitative assessment
    without derived figures. Its shape (formula ID plus a field mapping per
    input) is agent call-shape rather than a wire contract, and exposing it
    needs a decision about which formulas an officer may select — deferred
    rather than guessed at.
    """

    document_id = str(uuid.uuid4())
    pdf_bytes = await file.read()

    initial_state = {
        'document_id': document_id,
        'pdf_bytes': pdf_bytes,
        'compliance_requirements': compliance_requirements,
        'calculation_requests': [],
        'product_query': product_query,
        'sector': sector,
        'region': region,
        'precedent_query': precedent_query,
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
    config = {'configurable': {'thread_id': document_id}}

    try:
        result = await workflow.ainvoke(initial_state, config=config)
    except ToolError as exc:
        raise to_http_exception(exc) from exc

    return serialize_loan_result(document_id, result)


@router.post('/assessments/{thread_id}/decision')
async def submit_loan_decision(
    thread_id: str,
    body: LoanDecisionRequest,
    principal: Principal = Depends(get_current_principal),
    workflow: InspectableWorkflow = Depends(get_loan_workflow),
    audit_writer: AsyncAuditWriter | None = Depends(get_audit_writer),
) -> dict:
    """Record a decision at whichever gate this workflow is paused at.

    Authorization is per gate, not per endpoint: §10.2 gives each of the six
    gates a different approver, so being signed in is not by itself
    permission to act here.
    """

    gate = await pending_gate(workflow, thread_id)

    try:
        authorize_gate(gate, principal.realm_roles)
    except UnauthorizedForGateError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)
        ) from exc

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
        result = await resume_at_gate(
            workflow,
            thread_id,
            thread_id,
            gate.value,
            decision,
            audit_writer=audit_writer,
        )
    except ToolError as exc:
        raise to_http_exception(exc) from exc

    return serialize_loan_result(thread_id, result, acted_gate=gate.value)
