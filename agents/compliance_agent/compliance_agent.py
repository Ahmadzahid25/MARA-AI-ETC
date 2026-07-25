"""Compliance Agent — docs/architecture/05-agent-architecture.md §5.4.

    Responsibilities: cross-check application data and documents against
    MARA policy and regulatory requirements; surface compliance gaps/exceptions
    Confidence threshold: 0.9 for auto-pass classification
    Model tier: Sonnet-class (synthesis tier)

**Milestone-1 stub, approved explicitly** (not the original plan — see
docs/architecture/14-roadmap.md §14.3/§14.4, which scopes Compliance Agent
and the Knowledge Service it depends on to Milestone 2). Pulling this agent's
*shape* — checklist structure, hard-violation escalation, the
Document Assessment workflow wiring — into Milestone 1 was a deliberate
scope decision, on the explicit condition that the actual policy-matching
logic stays honestly stubbed until `services/knowledge_service` exists:
every check currently resolves to ``NO_POLICY_FOUND``, which is §5.4's own
specified behavior for "no corpus to check against" — not a shortcut
invented for this task. Replacing the stub `policy_lookup`/`checker` with
real Knowledge Service-backed implementations is the Milestone 2 task; the
call sites here don't need to change when that happens.
"""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable

from shared.agent_profiles import confidence_threshold_for, profile_for
from shared.llm.client import TieredLLMClient
from shared.llm.model_tiers import AgentName
from shared.provenance import ProvenanceLedger
from shared.schemas.compliance import (
    ComplianceChecklist,
    ComplianceChecklistItem,
    ComplianceStatus,
)
from shared.schemas.documents import DocumentExtractionRecord
from shared.schemas.knowledge import PolicyCitation

PROFILE = profile_for(AgentName.COMPLIANCE.value)
# Sourced from the profile registry — see shared/agent_profiles/profiles.py.
CONFIDENCE_THRESHOLD = confidence_threshold_for(AgentName.COMPLIANCE.value)


class ComplianceCheckParsingError(Exception):
    """The compliance-check step (LLM or injected checker) returned output
    that doesn't match the required shape — surfaced, never silently
    defaulted to a pass/fail guess."""


# requirement description -> matching policy clause citations (empty = no
# applicable policy found). The Milestone-2 implementation is
# agents/compliance_agent/policy_lookup.py's make_rag_policy_lookup(); the
# default below stays as the honest no-corpus behavior for environments with no
# Knowledge Service wired up.
PolicyLookup = Callable[[str], Awaitable[list[PolicyCitation]]]

# requirement, the policy citations found for it, and the document under
# review -> (status, notes). Only invoked when policy_lookup found at least
# one citation — with no real Knowledge Service, this path is currently
# unreachable via the default lookup, but is implemented and tested now so
# Milestone 2 only has to swap policy_lookup, not this agent's structure.
ComplianceChecker = Callable[
    [str, list[PolicyCitation], DocumentExtractionRecord],
    Awaitable[tuple[ComplianceStatus, str]],
]


async def _default_policy_lookup(requirement: str) -> list[PolicyCitation]:
    """No corpus wired up: every requirement resolves to NO_POLICY_FOUND.

    §5.4's specified behavior for an inconclusive corpus lookup, kept as the
    default so an environment without a Knowledge Service produces honest
    "no applicable policy found" findings rather than silently absent checks.
    Production wiring is make_rag_policy_lookup() in this package.
    """

    return []


def _build_check_prompt(
    requirement: str,
    citations: list[PolicyCitation],
    record: DocumentExtractionRecord,
) -> str:
    fields_text = '\n'.join(f'- {f.name}: {f.value}' for f in record.fields)
    citations_text = '\n'.join(
        f'- document {c.document_id} v{c.version}, clause {c.locator}'
        for c in citations
    )
    return (
        f'Requirement: {requirement}\n\n'
        f'Applicant document fields:\n{fields_text}\n\n'
        f'Matching policy clauses:\n{citations_text}\n\n'
        f'Does the application satisfy this requirement? Respond with a '
        f'JSON object with exactly these keys: "status" (one of "pass", '
        f'"fail", "exception"), "notes" (a short explanation). Respond with '
        f'the JSON object only, no other text.'
    )


def _parse_llm_check_result(raw_content: str) -> tuple[ComplianceStatus, str]:
    try:
        raw = json.loads(raw_content)
        status = ComplianceStatus(raw['status'])
        notes = str(raw['notes'])
    except (json.JSONDecodeError, KeyError, ValueError, TypeError) as exc:
        raise ComplianceCheckParsingError(
            f'Malformed compliance-check output {raw_content!r}: {exc}'
        ) from exc
    if status == ComplianceStatus.NO_POLICY_FOUND:
        raise ComplianceCheckParsingError(
            'Checker returned NO_POLICY_FOUND for a requirement that had '
            'matching citations — that status is reserved for the '
            'no-citations-found case, decided before the checker runs.'
        )
    return status, notes


class ComplianceAgent:
    """Configuration of the (not-yet-built) Agent Runtime for compliance
    checking — role/goal/tools/confidence-threshold, per docs/architecture/
    05-agent-architecture.md §5.1."""

    profile = PROFILE
    confidence_threshold: float = CONFIDENCE_THRESHOLD
    allowed_tools = PROFILE.allowed_tools

    def __init__(
        self,
        llm_client: TieredLLMClient | None = None,
        policy_lookup: PolicyLookup | None = None,
        checker: ComplianceChecker | None = None,
    ) -> None:
        self._llm_client = llm_client or TieredLLMClient()
        self._policy_lookup = policy_lookup or _default_policy_lookup
        self._checker = checker

    async def check_compliance(
        self,
        document_id: str,
        extraction_record: DocumentExtractionRecord,
        requirements: list[str],
        *,
        ledger: ProvenanceLedger | None = None,
    ) -> ComplianceChecklist:
        """Check ``extraction_record`` against each of ``requirements``.
        Per §5.4's escalation rule, any ``FAIL`` (hard violation) is
        surfaced via ``ComplianceChecklist.has_hard_violation`` — this
        method does not itself halt anything; that's the workflow's
        Validation-stage responsibility (docs/architecture/
        07-workflow-architecture.md §7.1).

        When ``ledger`` is supplied, every policy citation in the finished
        checklist is verified against what the RAG tool actually returned during
        this task, and a citation naming a clause that was never retrieved
        raises ``FabricatedCitationError`` rather than reaching the officer
        (docs/architecture/06-tool-architecture.md §6.1). Pass the same ledger
        that was given to ``make_rag_policy_lookup``; omitting it skips the
        check, which is only appropriate for a caller whose lookup does not
        retrieve — the default stub, or an injected test double.
        """

        items: list[ComplianceChecklistItem] = []
        for requirement in requirements:
            citations = await self._policy_lookup(requirement)
            if not citations:
                items.append(
                    ComplianceChecklistItem(
                        requirement=requirement,
                        status=ComplianceStatus.NO_POLICY_FOUND,
                        policy_citation=None,
                        notes='No applicable policy found in the knowledge base.',
                    )
                )
                continue

            if self._checker is not None:
                status, notes = await self._checker(
                    requirement, citations, extraction_record
                )
            else:
                status, notes = await self._default_checker(
                    requirement, citations, extraction_record
                )
            items.append(
                ComplianceChecklistItem(
                    requirement=requirement,
                    status=status,
                    policy_citation=citations[0],
                    notes=notes,
                )
            )

        checklist = ComplianceChecklist(document_id=document_id, items=items)

        if ledger is not None:
            # §6.1: the check happens before the output reaches a human, and is
            # deterministic — the agent gets no say in whether its own citations
            # count as verified.
            ledger.require_verified(
                tuple(
                    item.policy_citation.to_citable_ref()
                    for item in checklist.items
                    if item.policy_citation is not None
                )
            )

        return checklist

    async def _default_checker(
        self,
        requirement: str,
        citations: list[PolicyCitation],
        record: DocumentExtractionRecord,
    ) -> tuple[ComplianceStatus, str]:
        prompt = _build_check_prompt(requirement, citations, record)
        response = await self._llm_client.complete_for_agent(
            AgentName.COMPLIANCE, [{'role': 'user', 'content': prompt}]
        )
        content = response.choices[0].message.content
        if content is None:
            raise ComplianceCheckParsingError('Model returned no content')
        return _parse_llm_check_result(content)
