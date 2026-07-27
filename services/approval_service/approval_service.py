"""Approval Service — docs/architecture/10-human-in-the-loop.md §10.1:

    "The Approval Service is the mechanism that makes [officers make the
    final decision] true in the running system... the only path by which a
    paused LangGraph workflow can be unblocked."

Implements the Document Assessment workflow's "confirm extraction" gate
(docs/architecture/07-workflow-architecture.md §7.3) — the first of the
Milestone 1 acceptance criteria this closes: "a correction is fully
attributable in Audit Memory" (docs/architecture/14-roadmap.md §14.3).

Per §3.3's dependency rules, `services/` must not import from `workflows/`
— this module resumes a paused workflow through a structural
``ResumableWorkflow`` protocol (anything with an ``ainvoke`` method taking a
LangGraph ``Command``), not a concrete import of
``workflows.document_assessment``. Whatever wires the API Gateway to a real
workflow instance passes the compiled graph in.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, Protocol

from langgraph.types import Command

from shared.schemas.approval import (
    ApprovalAction,
    ApprovalDecisionInput,
    ApprovalRecord,
    FieldCorrection,
)
from shared.schemas.tooling import AuditSink, ToolInvocationLog, log_tool_invocation


class ResumableWorkflow(Protocol):
    async def ainvoke(self, input: Any, config: dict) -> dict: ...  # noqa: A002


class InspectableWorkflow(ResumableWorkflow, Protocol):
    """A resumable workflow whose *pending* state can also be read.

    Needed wherever a caller must know which gate a paused workflow is
    waiting at before deciding whether the requesting officer may act on it
    (services/api_gateway/routers/loans.py, against
    docs/architecture/10-human-in-the-loop.md §10.2's per-gate roles).

    Separate from ``ResumableWorkflow`` rather than folded into it because
    resuming and inspecting are different capabilities, and the
    single-gate Document Assessment path needs only the first.
    """

    async def aget_state(self, config: dict) -> Any: ...


# A real, async Audit Memory write (e.g. services.audit_service.write_audit_event
# bound to a connection pool, via services.audit_service.adapters
# .approval_record_to_audit_event) — kept as a generic injectable callable
# here rather than an import of services.audit_service, mirroring
# ResumableWorkflow's structural-typing pattern above: this module stays
# usable/testable without a real database, and the composition root is the
# one place that wires a concrete implementation in.
AsyncAuditWriter = Callable[[ApprovalRecord], Awaitable[None]]


def _resume_payload(decision: ApprovalDecisionInput) -> dict:
    status = 'approved' if decision.action != ApprovalAction.REJECT else 'rejected'
    payload: dict = {
        'status': status,
        'actor': decision.actor,
        'reason': decision.reason,
    }
    if decision.action == ApprovalAction.CORRECT:
        payload['corrected_fields'] = [
            {'field_name': c.field_name, 'corrected_value': c.corrected_value}
            for c in decision.corrections
        ]
    return payload


def _log_approval(record: ApprovalRecord, audit_sink: AuditSink | None) -> None:
    # Fallback used only when no real audit_writer is supplied (see
    # confirm_extraction) — e.g. services/audit_service isn't wired yet in
    # this environment. Structured logging, not a silent no-op.
    log_tool_invocation(
        ToolInvocationLog(
            tool_name='approval_decision',
            caller_agent=record.actor,
            workflow_id=record.workflow_thread_id,
            input_hash=record.document_id,
            output_hash=record.action.value,
            latency_ms=0.0,
            outcome='success',
        ),
        sink=audit_sink,
    )


async def confirm_extraction(
    workflow: ResumableWorkflow,
    thread_id: str,
    document_id: str,
    decision: ApprovalDecisionInput,
    *,
    audit_sink: AuditSink | None = None,
    audit_writer: AsyncAuditWriter | None = None,
) -> dict:
    """Resume a Document Assessment workflow paused at its
    ``confirm_extraction`` gate with an officer's decision. The
    ``ApprovalRecord`` is written **before** resuming the workflow, so the
    decision is on record even if resumption itself subsequently fails —
    per docs/architecture/06-tool-architecture.md §6.1's same "audit before
    the caller sees the result" principle applied to tool calls.

    ``audit_writer``, when supplied, is a real async Audit Memory write
    (e.g. services.audit_service) and takes priority over ``audit_sink``'s
    structured-logging fallback — see the ``AsyncAuditWriter`` type alias
    above for why this module doesn't import services.audit_service
    directly.
    """

    record = ApprovalRecord(
        workflow_thread_id=thread_id,
        document_id=document_id,
        action=decision.action,
        actor=decision.actor,
        reason=decision.reason,
        corrections=decision.corrections,
    )
    if audit_writer is not None:
        await audit_writer(record)
    else:
        _log_approval(record, audit_sink)

    config = {'configurable': {'thread_id': thread_id}}
    return await workflow.ainvoke(
        Command(resume=_resume_payload(decision)), config=config
    )


async def resume_at_gate(
    workflow: ResumableWorkflow,
    thread_id: str,
    document_id: str,
    gate: str,
    decision: ApprovalDecisionInput,
    *,
    audit_sink: AuditSink | None = None,
    audit_writer: AsyncAuditWriter | None = None,
) -> dict:
    """Resume a multi-gate workflow paused at ``gate``.

    The generalisation of ``confirm_extraction`` for Loan Assessment, which
    pauses at six different gates rather than one. Same ordering guarantee:
    the ``ApprovalRecord`` is written **before** resuming, so a decision is on
    record even if resumption then fails.

    ``gate`` is recorded on the audit trail rather than used to branch — the
    resume payload is identical at every gate. Without it, an audit reader
    sees six decisions by six officers on one workflow and no way to tell
    which stage each one signed off.
    """

    record = ApprovalRecord(
        workflow_thread_id=thread_id,
        document_id=document_id,
        action=decision.action,
        actor=decision.actor,
        reason=f'[{gate}] {decision.reason}' if decision.reason else f'[{gate}]',
        corrections=decision.corrections,
    )
    if audit_writer is not None:
        await audit_writer(record)
    else:
        _log_approval(record, audit_sink)

    config = {'configurable': {'thread_id': thread_id}}
    return await workflow.ainvoke(
        Command(resume=_resume_payload(decision)), config=config
    )


def build_correction_decision(
    actor: str, corrections: list[FieldCorrection], reason: str = ''
) -> ApprovalDecisionInput:
    """Convenience constructor matching how the Review & Approval Console
    is expected to submit a Correct action — one or more field corrections,
    per docs/architecture/10-human-in-the-loop.md §10.5."""

    return ApprovalDecisionInput(
        action=ApprovalAction.CORRECT,
        actor=actor,
        reason=reason,
        corrections=corrections,
    )
