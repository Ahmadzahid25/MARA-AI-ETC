"""Approval decision contract — docs/architecture/10-human-in-the-loop.md
§10.5: "An approver has three actions, not two — approve/reject is
insufficient because rejection alone discards useful partial work."

This is the contract between the Review & Approval Console
(apps/officer-workspace/) and services/approval_service/ — the officer's
decision on a pending approval request.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum

from pydantic import BaseModel, Field


class ApprovalAction(str, Enum):
    APPROVE = 'approve'
    REJECT = 'reject'
    CORRECT = 'correct'


class FieldCorrection(BaseModel):
    """One field's corrected value. §10.5: "stored as a distinct, attributed
    record — not merged silently into the agent's original output."""

    field_name: str = Field(min_length=1)
    corrected_value: str
    reason: str = Field(default='')


class ApprovalDecisionInput(BaseModel):
    """What an officer submits from the Review & Approval Console."""

    action: ApprovalAction
    actor: str = Field(min_length=1, description='The deciding officer.')
    reason: str = Field(default='')
    corrections: list[FieldCorrection] = Field(default_factory=list)

    def model_post_init(self, __context: object) -> None:
        if self.action != ApprovalAction.CORRECT and self.corrections:
            raise ValueError(
                'corrections is only meaningful when action is "correct" '
                f'(got action={self.action.value} with '
                f'{len(self.corrections)} correction(s))'
            )
        if self.action == ApprovalAction.CORRECT and not self.corrections:
            raise ValueError('action "correct" requires at least one correction')


class ApprovalRecord(BaseModel):
    """Immutable, attributed record of one approval decision — what
    services/approval_service writes to Audit Memory (docs/architecture/
    08-memory-architecture.md §8.2: "Written by supervisor_service, Tool
    Runtime, and Approval Service independently"). Retained regardless of
    what happens to the workflow afterward — a rejected/corrected attempt is
    never deleted, per docs/architecture/10-human-in-the-loop.md §10.7.
    """

    workflow_thread_id: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    action: ApprovalAction
    actor: str
    reason: str
    corrections: list[FieldCorrection]
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
