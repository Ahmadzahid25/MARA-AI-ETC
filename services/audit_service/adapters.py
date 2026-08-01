"""Adapters from other components' typed records into ``AuditEvent``.

Kept separate from ``audit_service.py`` (the read/write API itself) so this
module can depend on ``shared/schemas/approval.py`` without the core
read/write path needing to know about every producer's specific record
shape — new producers add an adapter function here, not a new branch inside
``write_audit_event()``.
"""

from __future__ import annotations

from services.audit_service.audit_service import AuditEvent, EventType
from shared.schemas.approval import ApprovalAction, ApprovalRecord

_EVENT_TYPE_BY_ACTION: dict[ApprovalAction, EventType] = {
    ApprovalAction.APPROVE: 'approval',
    ApprovalAction.REJECT: 'rejection',
    ApprovalAction.CORRECT: 'correction',
}


def approval_record_to_audit_event(
    record: ApprovalRecord, branch_code: str = 'hq'
) -> AuditEvent:
    """docs/architecture/14-roadmap.md §14.3's acceptance criterion — "a
    correction is fully attributable in Audit Memory" — is this function:
    every field of the officer's decision, including individual field
    corrections, lands in the event payload, not just a pass/fail flag.

    ``branch_code`` stamps which branch database the event belongs to
    (docs/architecture/18-per-branch-database-schema.md §3 Jadual 8); the
    composition root passes ``settings.branch.code`` here at startup.
    """

    return AuditEvent(
        workflow_id=record.workflow_thread_id,
        actor_id=record.actor,
        actor_role='officer',
        branch_code=branch_code,
        event_type=_EVENT_TYPE_BY_ACTION[record.action],
        payload={
            'document_id': record.document_id,
            'action': record.action.value,
            'reason': record.reason,
            'corrections': [c.model_dump() for c in record.corrections],
        },
    )
