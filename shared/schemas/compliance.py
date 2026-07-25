"""Compliance checklist contract — docs/architecture/05-agent-architecture.md
§5.4:

    Outputs: Compliance checklist with pass/fail/exception per requirement,
    each citing the specific policy clause.
    Failure handling: if policy corpus lookup is inconclusive (no matching
    clause), reports "no applicable policy found" explicitly rather than
    inferring one.

As of this Milestone-1 slice, `services/knowledge_service` (the Dify-backed
policy corpus, Milestone 2 scope per docs/architecture/14-roadmap.md §14.4)
does not exist — every real compliance check currently resolves to
``NO_POLICY_FOUND``, which is the schema's honest, specified behavior for
"no corpus to check against," not a placeholder shortcut invented for this
task.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from shared.schemas.knowledge import PolicyCitation


class ComplianceStatus(str, Enum):
    PASS = 'pass'
    FAIL = 'fail'
    EXCEPTION = 'exception'
    NO_POLICY_FOUND = 'no_policy_found'


class ComplianceChecklistItem(BaseModel):
    """One requirement's check result, citing the specific policy clause it
    was checked against — ``policy_citation`` is ``None`` only when
    ``status`` is ``NO_POLICY_FOUND``, since there's nothing to cite in that
    case.

    The citation is a ``PolicyCitation`` (document + version + clause), not the
    page-based ``Citation`` used for applicant documents: a compliance finding
    has to name the policy *version* it was decided against, or §9.4's
    reproducibility guarantee cannot be checked after the policy is revised.
    """

    requirement: str = Field(min_length=1)
    status: ComplianceStatus
    policy_citation: PolicyCitation | None = None
    notes: str = Field(default='')

    def is_hard_violation(self) -> bool:
        return self.status == ComplianceStatus.FAIL


class ComplianceChecklist(BaseModel):
    """The Compliance Agent's complete output for one document/application.
    docs/architecture/10-human-in-the-loop.md §10.3: any hard violation
    (``FAIL``) is an always-required approval gate — ``has_hard_violation``
    is what a workflow's Validation stage checks to decide whether to halt
    progression toward Approval."""

    document_id: str = Field(min_length=1)
    items: list[ComplianceChecklistItem] = Field(default_factory=list)

    @property
    def has_hard_violation(self) -> bool:
        return any(item.is_hard_violation() for item in self.items)
