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
    # TODO(milestone-1): replace with a real services/audit_service write —
    # see shared/schemas/tooling.py's log_tool_invocation for the same
    # interim pattern applied to tool calls. The Approval Service is
    # required (docs/architecture/08-memory-architecture.md §8.2) to write
    # Audit Memory independently of the Tool Runtime and supervisor_service
    # — reusing the same stub sink here, not a separate ad hoc log, keeps
    # that "independently" property honest once the real write path exists:
    # swapping the sink closes all three call sites identically.
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
) -> dict:
    """Resume a Document Assessment workflow paused at its
    ``confirm_extraction`` gate with an officer's decision. The
    ``ApprovalRecord`` is written **before** resuming the workflow, so the
    decision is on record even if resumption itself subsequently fails —
    per docs/architecture/06-tool-architecture.md §6.1's same "audit before
    the caller sees the result" principle applied to tool calls.
    """

    record = ApprovalRecord(
        workflow_thread_id=thread_id,
        document_id=document_id,
        action=decision.action,
        actor=decision.actor,
        reason=decision.reason,
        corrections=decision.corrections,
    )
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
