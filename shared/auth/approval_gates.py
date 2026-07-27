"""Which role may act at which approval gate — docs/architecture/
10-human-in-the-loop.md §10.2.

§10.2 gives every gate a different approver, and the difference is the point:
a Finance Officer signing off a risk rating, or an officer acknowledging a
compliance violation on the Compliance Officer's behalf, defeats the
separation the gates exist to create. Authentication alone does not enforce
that — a signed-in officer is authenticated for *some* gate, not for the one
in front of them.

So the mapping is declared here, once, as data, and checked at the Gateway
before a decision reaches the workflow. Same reasoning as
shared/agent_profiles: a policy spread across call sites is one nobody can
review as a whole, and one that drifts when only some call sites are updated.

**Which gate is pending is read from the workflow, never from the request.**
A client-supplied gate name would let a caller nominate the gate they happen
to hold the role for, which is the whole control inverted.
"""

from __future__ import annotations

from enum import StrEnum


class ApprovalGate(StrEnum):
    """The six durable-pause gates a Loan Assessment can be waiting at.

    Values match the ``type`` field each workflow node passes to
    ``interrupt()`` (workflows/loan_assessment), so a pending interrupt maps
    to a gate without a translation table that could fall out of step.
    """

    CONFIRM_EXTRACTION = 'confirm_extraction'
    COMPLIANCE_ACKNOWLEDGMENT = 'compliance_acknowledgment'
    FINANCIAL_SIGN_OFF = 'financial_sign_off'
    RISK_REVIEW = 'risk_review'
    RECOMMENDATION_APPROVAL = 'recommendation_approval'
    PUBLISH_APPROVAL = 'publish_approval'


# Realm role names, as defined in
# infrastructure/compose/init/keycloak-realm-mara-ai-etc.json.
ENTREPRENEURSHIP_OFFICER = 'entrepreneurship_officer'
COMPLIANCE_OFFICER = 'compliance_officer'
FINANCE_OFFICER = 'finance_officer'
RISK_OFFICER = 'risk_officer'
BRANCH_MANAGER = 'branch_manager'
COMMITTEE_SECRETARY = 'committee_secretary'


# Gate -> the roles that may act at it. Holding *any* one of them suffices;
# §10.2's table is transcribed directly, and the two entries that list more
# than one role are explained below rather than silently widened.
GATE_ROLES: dict[ApprovalGate, frozenset[str]] = {
    # "Any assigned Entrepreneurship Officer."
    ApprovalGate.CONFIRM_EXTRACTION: frozenset({ENTREPRENEURSHIP_OFFICER}),
    # "Compliance Officer."
    ApprovalGate.COMPLIANCE_ACKNOWLEDGMENT: frozenset({COMPLIANCE_OFFICER}),
    # "Finance Officer."
    ApprovalGate.FINANCIAL_SIGN_OFF: frozenset({FINANCE_OFFICER}),
    # "Risk Officer."
    ApprovalGate.RISK_REVIEW: frozenset({RISK_OFFICER}),
    # "Entrepreneurship Officer (case owner); escalates to Branch Manager
    # above a configurable exposure threshold." Both roles appear because the
    # escalated path is a legitimate approver — the *threshold* that decides
    # when escalation is required is not modelled yet (see §10.2 note below).
    ApprovalGate.RECOMMENDATION_APPROVAL: frozenset(
        {ENTREPRENEURSHIP_OFFICER, BRANCH_MANAGER}
    ),
    # "Case owner + Committee Secretary" — genuinely dual-control, and only
    # half-enforced here (see below).
    ApprovalGate.PUBLISH_APPROVAL: frozenset(
        {ENTREPRENEURSHIP_OFFICER, COMMITTEE_SECRETARY}
    ),
}


# Two parts of §10.2 this module does NOT yet enforce, recorded here rather
# than left for a reader to discover by their absence:
#
# 1. **Dual control on PUBLISH_APPROVAL.** §10.2 says "Case owner + Committee
#    Secretary" — two distinct people, not one person holding either role.
#    The workflow pauses once at that gate, so there is nowhere to collect a
#    second signature; modelling it needs the gate to interrupt twice and the
#    workflow to track who has already signed. Until then this check confirms
#    the actor holds *one* of the two roles, which is weaker than specified.
#
# 2. **The exposure threshold on RECOMMENDATION_APPROVAL.** Escalation to
#    Branch Manager is "above a configurable exposure threshold"; that
#    threshold does not exist in config yet, so a Branch Manager is currently
#    accepted at any exposure rather than required above one.
#
# Both are widenings relative to §10.2, not narrowings — they let through
# approvals the spec would gate further, and neither lets through an approver
# §10.2 excludes entirely.


class UnauthorizedForGateError(PermissionError):
    """The authenticated officer holds no role permitted at this gate.

    A ``PermissionError`` rather than a domain-specific base because the
    Gateway maps it straight to 403 — this is an authorization outcome, not a
    workflow failure, and it should read that way in logs and to the caller.
    """

    def __init__(self, gate: ApprovalGate, held_roles: frozenset[str]) -> None:
        self.gate = gate
        self.held_roles = held_roles
        super().__init__(
            f'This decision is at the {gate.value!r} gate, which requires one '
            f'of {sorted(GATE_ROLES[gate])}. The signed-in officer holds '
            f'{sorted(held_roles) or "no realm roles"}.'
        )


def roles_for_gate(gate: ApprovalGate) -> frozenset[str]:
    return GATE_ROLES[gate]


def authorize_gate(gate: ApprovalGate, held_roles: frozenset[str]) -> None:
    """Raise unless ``held_roles`` includes a role permitted at ``gate``.

    Fails closed by construction: a gate absent from ``GATE_ROLES`` raises
    ``KeyError`` rather than defaulting to permitted, so adding a gate to the
    workflow without deciding who may approve it breaks loudly at the first
    request instead of quietly accepting anyone.
    """

    if not (held_roles & GATE_ROLES[gate]):
        raise UnauthorizedForGateError(gate, held_roles)
