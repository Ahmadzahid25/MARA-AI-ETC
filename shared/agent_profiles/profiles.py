"""Agent capability profiles — the one adjustable surface for agent autonomy.

Every dial that decides *how much freedom* a given agent has lives here, as
data: which tools it may call, whether it may choose among them or must run a
fixed sequence, the confidence floor below which it must escalate, whether its
output can ever reach a human without an approval gate, and whether it may
reach the network at all.

Why one registry instead of per-agent constants
-----------------------------------------------
Before this module, the same permission relationship was written down twice,
in opposite directions, with nothing checking the two agreed:

    agents/document_agent/document_agent.py
        allowed_tools = ('ocr', 'pdf_parse', 'document_classification')
    tools/ocr/ocr_tool.py
        ALLOWED_CALLERS = frozenset({'document_agent'})

Only the second was enforced; the first was decorative. Widening one agent's
grant therefore meant editing N tool modules plus the agent, and nothing failed
if they drifted apart. Confidence thresholds had the same problem, declared as
module constants next to the agent that happened to use them.

This module makes the grant a single declaration and derives the tool-side
allow-list from it (``callers_allowed_for_tool``), so the two directions cannot
disagree — the same reasoning shared/llm/model_tiers.py applies to model choice
("deliberately data, not code"), extended to the rest of the autonomy surface.

Relationship to the architecture baseline
-----------------------------------------
This module does not grant anything the Architecture Baseline v1.0 does not
already grant. Every profile below encodes the allow-list from
docs/architecture/06-tool-architecture.md §6.2 and the confidence/approval
columns from docs/architecture/05-agent-architecture.md §5.9. What changes is
where those decisions are written down, not what they are — see §5.15 of that
document for the governance rule this registry is subject to.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from shared.llm.model_tiers import AGENT_TIER, AgentName, ModelTier


class AutonomyLevel(StrEnum):
    """How much latitude an agent has *within* its tool grant.

    This is deliberately separate from the grant itself: "which tools may you
    touch" and "may you decide the order you touch them in" are different
    risks, and conflating them is what makes autonomy hard to adjust
    incrementally later.
    """

    BOUNDED = 'bounded'
    """Fixed tool sequence, decided by the workflow template's node, not by the
    agent. The agent contributes judgment at one step (e.g. turning parsed page
    text into confidence-scored fields) but does not choose what runs next.
    Every agent is BOUNDED today because the Agent Runtime's action/observation
    loop (docs/architecture/02-system-architecture.md, Layer 4) is not built
    yet — this is the level the current direct-call implementations actually
    have, recorded honestly rather than aspirationally."""

    GUIDED = 'guided'
    """Free choice of tool and ordering, iterating tool -> observation until the
    agent emits a result — but strictly inside ``allowed_tools``, and the output
    still passes the same confidence floor and approval gate. This is the
    natural next step for the seven agents once the Agent Runtime lands: it
    widens *how* an agent works without widening what it can reach or weakening
    what a human must sign off."""

    EXPLORATORY = 'exploratory'
    """Full agentic loop with a broad grant and no confidence gate. Only
    permitted on profiles that are structurally barred from the decision path
    (``can_inform_decision=False``) — see ``EXPLORATION_SANDBOX``. Enforced by
    an invariant test, not by convention."""


class ApprovalRequirement(StrEnum):
    """When this profile's output needs a human before it goes anywhere.

    Models the "Human approval" column of docs/architecture/
    05-agent-architecture.md §5.9. Conditional *escalation* rules that depend on
    an output's content rather than its confidence — the Compliance Agent's
    "hard violation halts progression toward approval", for instance — are
    workflow-stage logic (docs/architecture/07-workflow-architecture.md §7.1),
    not a profile field; this enum captures the floor that applies regardless of
    content.
    """

    NONE = 'none'
    """Always visible to the officer, never an independent blocking gate."""

    ON_LOW_CONFIDENCE = 'on_low_confidence'
    """Gated when the output falls below ``confidence_threshold``."""

    ALWAYS = 'always'
    """Never auto-forwarded, at any confidence."""


EXPLORATION_SANDBOX = 'exploration_sandbox'
"""Profile name for the decision-path-isolated exploration agent (§5.15.3).

Deliberately *not* a member of ``AgentName``: that enum is the seven true
agents (docs/architecture/05-agent-architecture.md §5.14), and this is not an
eighth one — it holds no position in any workflow template and produces nothing
a committee report may cite.
"""


class AgentProfile(BaseModel):
    """One agent's complete autonomy declaration.

    Frozen because a profile is configuration resolved at import time, not
    mutable state: code that could widen its own grant mid-workflow would make
    the audit trail's "what was this agent allowed to do" unanswerable after
    the fact.
    """

    model_config = ConfigDict(frozen=True)

    autonomy: AutonomyLevel
    allowed_tools: frozenset[str] = Field(
        description='Tool names from docs/architecture/06-tool-architecture.md '
        '§6.2. The tool modules derive their own caller allow-lists from these '
        'via callers_allowed_for_tool(), so this is the only place a grant is '
        'written down.'
    )
    confidence_threshold: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description='Self-reported confidence below which the agent must '
        'escalate rather than emit a result as final. None only for profiles '
        'that emit nothing a decision depends on.',
    )
    approval: ApprovalRequirement
    can_inform_decision: bool = Field(
        default=True,
        description="Whether this profile's output may enter the audited "
        'decision path at all. False makes the isolation structural rather '
        'than a matter of officer discipline.',
    )
    external_egress: bool = Field(
        default=False,
        description='Outbound network reach. True for the Market Agent only — '
        'docs/architecture/05-agent-architecture.md §5.7 and the '
        'network-policy enforcement in §11.7.',
    )
    llm_tier_override: ModelTier | None = Field(
        default=None,
        description='Only for profiles outside AgentName, which have no entry '
        'in AGENT_TIER. The seven agents resolve their tier from '
        'shared/llm/model_tiers.py, which stays the single authority for the '
        'per-agent cost decision (docs/architecture/04-technology-stack.md '
        '§4.6.1).',
    )


# The single source of truth. Adjusting an agent's autonomy is an edit here and
# nowhere else — see shared/agent_profiles/README.md for the four dials and
# what widening each one costs.
AGENT_PROFILES: dict[str, AgentProfile] = {
    AgentName.PLANNER.value: AgentProfile(
        autonomy=AutonomyLevel.BOUNDED,
        allowed_tools=frozenset({'rag_query'}),
        confidence_threshold=0.75,
        approval=ApprovalRequirement.NONE,
    ),
    AgentName.DOCUMENT.value: AgentProfile(
        autonomy=AutonomyLevel.BOUNDED,
        allowed_tools=frozenset(
            {'ocr', 'pdf_parse', 'document_classification', 'rag_query'}
        ),
        confidence_threshold=0.85,
        approval=ApprovalRequirement.ON_LOW_CONFIDENCE,
    ),
    AgentName.COMPLIANCE.value: AgentProfile(
        autonomy=AutonomyLevel.BOUNDED,
        allowed_tools=frozenset({'rag_query', 'structured_database_query'}),
        confidence_threshold=0.9,
        approval=ApprovalRequirement.ON_LOW_CONFIDENCE,
    ),
    AgentName.FINANCE.value: AgentProfile(
        autonomy=AutonomyLevel.BOUNDED,
        allowed_tools=frozenset({'rag_query', 'calculation', 'excel_generation'}),
        confidence_threshold=0.85,
        approval=ApprovalRequirement.ALWAYS,
    ),
    AgentName.RISK.value: AgentProfile(
        autonomy=AutonomyLevel.BOUNDED,
        allowed_tools=frozenset(
            {'rag_query', 'calculation', 'structured_database_query'}
        ),
        confidence_threshold=0.8,
        approval=ApprovalRequirement.ALWAYS,
    ),
    AgentName.MARKET.value: AgentProfile(
        autonomy=AutonomyLevel.BOUNDED,
        allowed_tools=frozenset({'rag_query', 'web_search'}),
        confidence_threshold=0.7,
        approval=ApprovalRequirement.NONE,
        external_egress=True,
    ),
    AgentName.RECOMMENDATION.value: AgentProfile(
        autonomy=AutonomyLevel.BOUNDED,
        allowed_tools=frozenset({'rag_query'}),
        confidence_threshold=0.8,
        approval=ApprovalRequirement.ALWAYS,
    ),
    EXPLORATION_SANDBOX: AgentProfile(
        autonomy=AutonomyLevel.EXPLORATORY,
        allowed_tools=frozenset(
            {'rag_query', 'structured_database_query', 'calculation'}
        ),
        confidence_threshold=None,
        approval=ApprovalRequirement.NONE,
        # The whole point of this profile: broad latitude is affordable
        # precisely because nothing it produces can reach a decision.
        can_inform_decision=False,
        # Not granted, deliberately. Sole-egress stays the Market Agent's
        # (§5.7) — a second egress path is exactly what §11.7's network policy
        # exists to prevent, and a sandbox is the likeliest place to acquire
        # one by accident.
        external_egress=False,
        llm_tier_override=ModelTier.SYNTHESIS,
    ),
}


class UnknownProfileError(KeyError):
    """No profile is registered under this name.

    A typed error because the alternative — a bare KeyError from a dict lookup
    deep inside a tool's permission check — reads as a crash rather than as
    what it is: a caller identifying itself with a name that was never granted
    anything.
    """


def profile_for(profile_name: str) -> AgentProfile:
    """The profile registered under ``profile_name``.

    Accepts a plain string rather than ``AgentName`` because tool call sites
    already pass ``caller_agent`` as a string (``AgentName.DOCUMENT.value``),
    and because profiles outside the seven agents — the exploration sandbox —
    have no ``AgentName`` member by design.
    """

    try:
        return AGENT_PROFILES[profile_name]
    except KeyError:
        raise UnknownProfileError(
            f'No agent profile registered for {profile_name!r} '
            f'(known: {sorted(AGENT_PROFILES)})'
        ) from None


def callers_allowed_for_tool(tool_name: str) -> frozenset[str]:
    """Every profile granted ``tool_name``, as the tool's caller allow-list.

    This is the inversion that removes the duplicated permission declaration:
    tool modules call this at import time instead of hand-maintaining their own
    ``frozenset`` of caller names, so a grant added here cannot fail to reach
    the tool that enforces it.

    Returns an empty set for a tool no profile has been granted — correct, and
    strict: an ungranted tool rejects every caller rather than defaulting open.
    """

    return frozenset(
        name
        for name, profile in AGENT_PROFILES.items()
        if tool_name in profile.allowed_tools
    )


def confidence_threshold_for(profile_name: str) -> float:
    """The escalation floor for ``profile_name``.

    Raises rather than substituting a default when a profile has no threshold:
    a profile with ``confidence_threshold=None`` emits nothing a decision
    depends on, so code asking it for a threshold has confused two different
    kinds of component, and a quietly-invented default would hide that.
    """

    threshold = profile_for(profile_name).confidence_threshold
    if threshold is None:
        raise ValueError(
            f'Profile {profile_name!r} declares no confidence threshold — it '
            f'is not a decision-bearing profile. See '
            f'shared/agent_profiles/profiles.py.'
        )
    return threshold


def llm_tier_for(profile_name: str) -> ModelTier:
    """The model tier ``profile_name`` routes through.

    Defers to ``AGENT_TIER`` for the seven true agents so that
    shared/llm/model_tiers.py remains the single authority for the per-agent
    cost decision; only profiles with no ``AgentName`` member supply their own.
    """

    profile = profile_for(profile_name)
    if profile.llm_tier_override is not None:
        return profile.llm_tier_override
    return AGENT_TIER[AgentName(profile_name)]


def assert_can_inform_decision(profile_name: str) -> None:
    """Guard for code that is about to let a profile's output reach the
    decision path — a workflow stage, an approval record, a committee report.

    Call sites should prefer this over reading ``can_inform_decision``
    themselves, so that the isolation is enforced the same way everywhere
    rather than re-implemented per caller.
    """

    if not profile_for(profile_name).can_inform_decision:
        raise PermissionError(
            f'Profile {profile_name!r} is barred from the decision path: its '
            f'output may not inform a workflow decision, approval record, or '
            f'committee report. See docs/architecture/'
            f'05-agent-architecture.md §5.15.3.'
        )
