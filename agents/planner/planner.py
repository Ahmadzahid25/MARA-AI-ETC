"""Planner — docs/architecture/05-agent-architecture.md §5.2.

    Responsibilities: select and parameterize a bounded, versioned
    workflow template for an officer's stated objective — not freely
    construct new task-graph topology at runtime (§5.2.1)
    Confidence threshold: 0.75 (template-match)
    Model tier: Haiku-class (extraction tier)

**Milestone 4 slice.** ``KNOWN_TEMPLATES`` catalogues the eight bounded
templates from docs/architecture/07-workflow-architecture.md §7.3 — real,
decided facts from the architecture baseline, not invented here. Matching
an officer's free-text objective against that catalogue is this agent's
one genuinely agentic step (LLM by default, injectable ``matcher`` for
tests); everything else is deterministic validation.

Per §5.2.1, a selected template's parameters are validated against that
template's own ``required_parameters`` before this agent's output is
considered final — a template match that lacks a required parameter is
treated the same as no match at all (escalated), never silently forwarded
with a gap for Delegation to discover later.

Not yet wired to automatically dispatch the selected template's workflow
graph (that integration belongs to the API Gateway / a future
`services/planner_service`, per this repo's established pattern of keeping
each agent directly callable and independently testable before Runtime
wiring — see `agents/document_agent`'s own README for the same note).
"""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable

from shared.agent_profiles import confidence_threshold_for, profile_for
from shared.llm.client import TieredLLMClient
from shared.llm.model_tiers import AgentName
from shared.schemas.planning import PlanResult, WorkflowTemplate

PROFILE = profile_for(AgentName.PLANNER.value)
# Sourced from the profile registry — see shared/agent_profiles/profiles.py.
CONFIDENCE_THRESHOLD = confidence_threshold_for(AgentName.PLANNER.value)

# The bounded catalogue — docs/architecture/07-workflow-architecture.md
# §7.3's table, verbatim. Only `document_assessment` and `loan_assessment`
# have a real LangGraph implementation under workflows/ as of this slice;
# the Planner's own job (selecting a name + parameters) doesn't depend on
# that — see module docstring.
KNOWN_TEMPLATES: tuple[WorkflowTemplate, ...] = (
    WorkflowTemplate(
        name='document_assessment',
        description='Officer uploads a document set for review, standalone '
        '(not yet tied to a full loan case).',
        required_parameters=('document_id', 'pdf_bytes'),
    ),
    WorkflowTemplate(
        name='loan_assessment',
        description='Officer opens a loan/grant application for evaluation: '
        'Document -> {Compliance, Finance, Market} -> Risk -> Recommendation '
        '-> publishing_service.',
        required_parameters=('document_id', 'pdf_bytes', 'compliance_requirements'),
    ),
    WorkflowTemplate(
        name='market_research',
        description='Officer requests sector/market context independent of '
        'a specific application.',
        required_parameters=('sector', 'region'),
    ),
    WorkflowTemplate(
        name='committee_report',
        description='Triggered automatically on Recommendation approval '
        'within Loan Assessment, or manually for a custom report.',
        required_parameters=('document_id',),
    ),
    WorkflowTemplate(
        name='risk_analysis',
        description='Standalone risk review requested outside a full loan '
        'cycle (e.g. portfolio spot-check).',
        required_parameters=('document_id',),
    ),
    WorkflowTemplate(
        name='presentation_generation',
        description='Triggered on report completion, or manually from an '
        'approved report.',
        required_parameters=('document_id',),
    ),
    WorkflowTemplate(
        name='audio_briefing',
        description='Officer requests a spoken summary of an approved report.',
        required_parameters=('document_id',),
    ),
    WorkflowTemplate(
        name='human_review',
        description='Not independently triggered — the generic '
        'Approval-stage handler shared by every workflow above.',
        required_parameters=('workflow_thread_id',),
    ),
)


class PlanParsingError(Exception):
    """The template-matching step (LLM or injected matcher) returned
    output that doesn't match the required shape — surfaced, never
    silently defaulted to a guessed template."""


# (objective, candidate templates) -> (template_name or None, confidence).
# Default calls the LLM (Haiku tier); tests inject a deterministic fake.
TemplateMatcher = Callable[
    [str, tuple[WorkflowTemplate, ...]], Awaitable[tuple[str | None, float]]
]


def _build_match_prompt(objective: str, templates: tuple[WorkflowTemplate, ...]) -> str:
    catalogue_text = '\n'.join(f'- {t.name}: {t.description}' for t in templates)
    return (
        f'Officer objective: {objective}\n\n'
        f'Available workflow templates:\n{catalogue_text}\n\n'
        f'Which template best matches this objective? Respond with a JSON '
        f'object with exactly these keys: "template_name" (one of the '
        f'names above, or null if none apply), "confidence" (float '
        f'0.0-1.0). Respond with the JSON object only, no other text.'
    )


def _parse_match(raw_content: str) -> tuple[str | None, float]:
    try:
        raw = json.loads(raw_content)
        template_name = raw['template_name']
        confidence = float(raw['confidence'])
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        raise PlanParsingError(
            f'Malformed match output {raw_content!r}: {exc}'
        ) from exc
    if not 0.0 <= confidence <= 1.0:
        raise PlanParsingError(f'confidence {confidence} out of range [0.0, 1.0]')
    return template_name, confidence


class Planner:
    """Configuration of the (not-yet-built) Agent Runtime for template
    selection — role/goal/tools/confidence-threshold, per docs/architecture/
    05-agent-architecture.md §5.1."""

    profile = PROFILE
    confidence_threshold: float = CONFIDENCE_THRESHOLD
    allowed_tools = PROFILE.allowed_tools

    def __init__(
        self,
        llm_client: TieredLLMClient | None = None,
        matcher: TemplateMatcher | None = None,
        templates: tuple[WorkflowTemplate, ...] = KNOWN_TEMPLATES,
    ) -> None:
        self._llm_client = llm_client or TieredLLMClient()
        self._matcher = matcher
        self._templates = templates

    async def plan(
        self, objective: str, parameters: dict[str, object] | None = None
    ) -> PlanResult:
        """Select and parameterize a template for ``objective``. Per
        §5.2's escalation rule, returns an escalated ``PlanResult``
        (``template_name=None``, a ``clarification_question``) rather than
        guessing when no template matches with confidence >= threshold, or
        when the matched template is missing a required parameter.
        """

        supplied_parameters = parameters or {}

        if self._matcher is not None:
            template_name, confidence = await self._matcher(objective, self._templates)
        else:
            template_name, confidence = await self._default_matcher(objective)

        known_names = frozenset(t.name for t in self._templates)
        if template_name is not None and template_name not in known_names:
            raise PlanParsingError(
                f'Matcher selected {template_name!r}, which is not in the '
                f'known catalogue ({sorted(known_names)})'
            )

        if template_name is None or confidence < self.confidence_threshold:
            return PlanResult(
                template_name=None,
                confidence=confidence,
                clarification_question=(
                    f'I could not confidently match "{objective}" to a known '
                    f'workflow (confidence {confidence:.2f}, threshold '
                    f'{self.confidence_threshold}). Could you clarify what '
                    f'you want to do — for example, review a document, '
                    f'assess a loan application, or research a market '
                    f'sector?'
                ),
            )

        template = next(t for t in self._templates if t.name == template_name)
        missing = [
            p for p in template.required_parameters if p not in supplied_parameters
        ]
        if missing:
            return PlanResult(
                template_name=None,
                confidence=confidence,
                clarification_question=(
                    f'The "{template.name}" workflow needs {missing} before '
                    f'it can start — could you provide '
                    f'{"these" if len(missing) > 1 else "this"}?'
                ),
            )

        return PlanResult(
            template_name=template.name,
            parameters=supplied_parameters,
            confidence=confidence,
        )

    async def _default_matcher(self, objective: str) -> tuple[str | None, float]:
        prompt = _build_match_prompt(objective, self._templates)
        response = await self._llm_client.complete_for_agent(
            AgentName.PLANNER, [{'role': 'user', 'content': prompt}]
        )
        content = response.choices[0].message.content
        if content is None:
            raise PlanParsingError('Model returned no content')
        return _parse_match(content)
