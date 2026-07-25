"""Invariant tests for the agent capability registry — shared/agent_profiles.

These exist for the same reason tests/unit/mara/test_model_tiers.py does: the
registry's value is that autonomy is adjustable in one place, and that is only
true if widening a grant by accident fails CI rather than passing review as a
one-line diff nobody read closely. Each test below pins a property the
Architecture Baseline v1.0 treats as load-bearing, not a stylistic preference.
"""

from __future__ import annotations

import importlib
import pkgutil
from types import ModuleType

import pytest
from pydantic import ValidationError

from shared.agent_profiles import (
    AGENT_PROFILES,
    EXPLORATION_SANDBOX,
    ApprovalRequirement,
    AutonomyLevel,
    UnknownProfileError,
    assert_can_inform_decision,
    callers_allowed_for_tool,
    confidence_threshold_for,
    llm_tier_for,
    profile_for,
)
from shared.llm.model_tiers import AGENT_TIER, AgentName, ModelTier


def test_every_true_agent_has_a_profile() -> None:
    for agent in AgentName:
        assert agent.value in AGENT_PROFILES


def test_profile_tier_matches_model_tiers_for_every_true_agent() -> None:
    """shared/llm/model_tiers.py stays the single authority for the per-agent
    cost decision (docs/architecture/04-technology-stack.md §4.6.1); the
    registry must not become a second, divergent place to set it."""

    for agent in AgentName:
        assert llm_tier_for(agent.value) == AGENT_TIER[agent]


def test_no_true_agent_overrides_its_tier() -> None:
    for agent in AgentName:
        assert profile_for(agent.value).llm_tier_override is None


# ── Egress — docs/architecture/05-agent-architecture.md §5.7, §11.7 ──


def test_market_agent_is_the_only_profile_with_external_egress() -> None:
    with_egress = [
        name for name, profile in AGENT_PROFILES.items() if profile.external_egress
    ]
    assert with_egress == [AgentName.MARKET.value]


def test_web_search_is_granted_to_the_market_agent_only() -> None:
    assert callers_allowed_for_tool('web_search') == frozenset({AgentName.MARKET.value})


def test_no_profile_is_granted_an_external_transmission_tool() -> None:
    """§6.3: no agent holds email/notification send. The guarantee is that the
    *capability* does not exist inside any grant, so a prompt-injected agent
    has nothing to reach for."""

    assert callers_allowed_for_tool('email_send') == frozenset()


# ── Decision-path isolation — §5.15.3 ──


def test_exploration_sandbox_cannot_inform_a_decision() -> None:
    assert profile_for(EXPLORATION_SANDBOX).can_inform_decision is False


def test_assert_can_inform_decision_rejects_the_sandbox() -> None:
    with pytest.raises(PermissionError, match='barred from the decision path'):
        assert_can_inform_decision(EXPLORATION_SANDBOX)


def test_assert_can_inform_decision_allows_every_true_agent() -> None:
    for agent in AgentName:
        assert_can_inform_decision(agent.value)


def test_exploratory_autonomy_requires_decision_path_isolation() -> None:
    """The one rule that keeps a widened autonomy level from quietly becoming a
    widened decision path: EXPLORATORY is only affordable on a profile whose
    output cannot reach an approval record or committee report."""

    for name, profile in AGENT_PROFILES.items():
        if profile.autonomy is AutonomyLevel.EXPLORATORY:
            assert not profile.can_inform_decision, (
                f'{name} is EXPLORATORY but may inform decisions'
            )


def test_no_decision_bearing_profile_skips_a_confidence_floor() -> None:
    for name, profile in AGENT_PROFILES.items():
        if profile.can_inform_decision:
            assert profile.confidence_threshold is not None, (
                f'{name} informs decisions but declares no confidence floor'
            )


# ── Approval gates — §5.9 ──


def test_recommendation_agent_always_requires_approval() -> None:
    """§5.8: the highest-stakes output in the system, never auto-forwarded."""

    profile = profile_for(AgentName.RECOMMENDATION.value)
    assert profile.approval is ApprovalRequirement.ALWAYS


def test_thresholds_match_the_agent_summary_table() -> None:
    expected = {
        AgentName.PLANNER: 0.75,
        AgentName.DOCUMENT: 0.85,
        AgentName.COMPLIANCE: 0.9,
        AgentName.FINANCE: 0.85,
        AgentName.RISK: 0.8,
        AgentName.MARKET: 0.7,
        AgentName.RECOMMENDATION: 0.8,
    }
    for agent, threshold in expected.items():
        assert confidence_threshold_for(agent.value) == threshold


# ── Tool allow-list derivation — the drift this registry exists to remove ──


def _tool_modules_declaring_an_allow_list() -> list[ModuleType]:
    """Every module under ``tools/`` that enforces a caller allow-list.

    Discovered by walking the package rather than listed here on purpose: a
    hand-maintained list would have to be updated by the same person who just
    added a tool the wrong way, which is precisely the discipline this registry
    exists to stop relying on.
    """

    import tools

    modules: list[ModuleType] = []
    for module_info in pkgutil.walk_packages(tools.__path__, prefix='tools.'):
        module = importlib.import_module(module_info.name)
        if hasattr(module, 'ALLOWED_CALLERS'):
            modules.append(module)
    return modules


def test_the_walker_finds_the_known_tools() -> None:
    """Guards the two tests below from silently passing on an empty set if the
    discovery mechanism itself breaks."""

    found = {m.__name__ for m in _tool_modules_declaring_an_allow_list()}
    assert found >= {
        'tools.ocr.ocr_tool',
        'tools.documents.pdf_parse',
        'tools.documents.classification',
    }


def test_every_tool_names_itself() -> None:
    """A tool that enforces an allow-list must declare TOOL_NAME, since that is
    the key its grant is looked up under."""

    for module in _tool_modules_declaring_an_allow_list():
        assert hasattr(module, 'TOOL_NAME'), (
            f'{module.__name__} enforces ALLOWED_CALLERS but declares no '
            f'TOOL_NAME to resolve its grant against'
        )


def test_tool_allow_lists_are_derived_not_restated() -> None:
    """Every tool's allow-list must *be* the registry's answer, not a copy of
    it that happens to agree today.

    Identity rather than equality, because equality cannot tell a derived
    allow-list from a hand-written ``frozenset({'document_agent'})`` that
    matches by coincidence — and it is the hand-written one, drifting a release
    later, that this registry exists to prevent. ``callers_allowed_for_tool``
    is cached so the derived call returns the same object every time.
    """

    for module in _tool_modules_declaring_an_allow_list():
        expected = callers_allowed_for_tool(module.TOOL_NAME)
        assert module.ALLOWED_CALLERS is expected, (
            f'{module.__name__}.ALLOWED_CALLERS is not derived from the '
            f'profile registry. Replace it with:\n\n'
            f'    ALLOWED_CALLERS = callers_allowed_for_tool(TOOL_NAME)\n\n'
            f'and declare the grant in shared/agent_profiles/profiles.py '
            f'(registry grants {sorted(expected)}, module has '
            f'{sorted(module.ALLOWED_CALLERS)}).'
        )


def test_document_tools_remain_document_agent_only() -> None:
    """§6.2's Permissions column. Pinned separately from the derivation test
    above so that widening the grant fails here with a readable diff, rather
    than silently passing because both sides moved together."""

    for tool_name in ('ocr', 'pdf_parse', 'document_classification'):
        assert callers_allowed_for_tool(tool_name) == frozenset(
            {AgentName.DOCUMENT.value}
        )


def test_ungranted_tool_defaults_closed() -> None:
    assert callers_allowed_for_tool('a_tool_nobody_was_granted') == frozenset()


# ── Lookup errors ──


def test_unknown_profile_raises_a_typed_error() -> None:
    with pytest.raises(UnknownProfileError):
        profile_for('not_an_agent')


def test_confidence_threshold_for_a_profile_without_one_raises() -> None:
    with pytest.raises(ValueError, match='no confidence threshold'):
        confidence_threshold_for(EXPLORATION_SANDBOX)


def test_sandbox_resolves_its_own_tier_without_an_agent_name_entry() -> None:
    assert llm_tier_for(EXPLORATION_SANDBOX) == ModelTier.SYNTHESIS


def test_profiles_are_immutable() -> None:
    """Configuration, not mutable state: code that could widen its own grant
    mid-workflow would make the audit trail's "what was this agent allowed to
    do" unanswerable after the fact."""

    profile = profile_for(AgentName.DOCUMENT.value)
    with pytest.raises(ValidationError):
        profile.external_egress = True  # type: ignore[misc]
