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
CONFIDENCE_THRESHOLD = confidence_threshold_for(AgentName.PLANNER.value)

# ---------------------------------------------------------------------------
# System prompt — gives the LLM personality, judgment, and the critical
# rule that it must NOT trigger a workflow just because a message arrived.
#
# This is the single most impactful change for making the agent feel natural:
# without a system prompt the LLM has no context for *why* it is being asked
# to classify intent, so it defaults to the most literal reading ("officer
# said something → run a workflow"). With a system prompt it reasons first.
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """\
You are MARA AI, the intelligent assistant for Pegawai MARA (MARA officers) \
who process loan and grant applications for Malaysian entrepreneurs.

You have access to specialised AI workflows:
- Document Assessment — extract and verify uploaded documents
- Loan Assessment — full evaluation pipeline (Document → Compliance → Finance → Risk → Recommendation)
- Market Research — sector/region analysis
- Risk Analysis — standalone risk spot-checks
- Committee Report, Presentation, Audio Briefing — triggered on completed assessments
- Human Review — approval-gate handler

Your personality and judgment rules:
1. Be friendly, professional, and helpful — like a knowledgeable colleague, not a rigid system.
2. Respond in English by default. Switch naturally to Bahasa Malaysia if the officer writes in BM.
3. **Only trigger a workflow when the officer clearly needs one.** \
   Greetings, questions about your capabilities, small talk, and vague statements \
   must receive a conversational reply — never a workflow.
4. When a workflow is genuinely needed but required information is missing \
   (e.g. no document attached), ask for it conversationally — do not error.
5. Be concise. Officers are busy; do not pad replies unnecessarily.

You are NOT a rigid classifier. You have judgment. Use it.\
"""

# The bounded catalogue — docs/architecture/07-workflow-architecture.md §7.3.
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


# (objective, candidate templates) -> (template_name or "converse" or None, confidence, reply or None).
# Default calls the LLM (Haiku tier); tests inject a deterministic fake.
TemplateMatcher = Callable[
    [str, tuple[WorkflowTemplate, ...]],
    Awaitable[tuple[str | None, float, str | None]],
]


def _build_match_prompt(objective: str, templates: tuple[WorkflowTemplate, ...]) -> str:
    catalogue_text = '\n'.join(f'- {t.name}: {t.description}' for t in templates)
    return (
        f'Officer message: {objective}\n\n'
        f'Available workflow templates:\n{catalogue_text}\n\n'
        f'Decide which of the two intents applies:\n\n'
        f'A) CONVERSE — the officer is greeting you, asking a general question, '
        f'asking about your capabilities, or their message does not clearly '
        f'request one of the listed workflows.\n\n'
        f'B) WORKFLOW — the officer clearly wants to start one of the listed '
        f'workflows right now.\n\n'
        f'Respond with a JSON object. Use one of these two shapes only:\n\n'
        f'Shape A (converse):\n'
        f'{{"intent": "converse", "reply": "<your helpful conversational response>"}}\n\n'
        f'Shape B (workflow):\n'
        f'{{"intent": "workflow", "template_name": "<name from list above>", "confidence": <float 0.0-1.0>}}\n\n'
        f'Rules:\n'
        f'- Prefer CONVERSE when in doubt. Never trigger a workflow on a greeting or vague message.\n'
        f'- For CONVERSE, write the reply as if you are speaking directly to the officer.\n'
        f'- For WORKFLOW, confidence must reflect how certain you are this template matches.\n'
        f'- JSON only. No other text.'
    )


def _parse_match(raw_content: str) -> tuple[str | None, float, str | None]:
    """Parse the LLM's dual-intent JSON.

    Returns ``(template_name_or_None, confidence, conversational_reply_or_None)``.
    ``"converse"`` intent → ``(None, 1.0, reply_text)``.
    ``"workflow"`` intent → ``(template_name, confidence, None)``.
    """
    try:
        raw = json.loads(raw_content)
        intent = raw.get('intent')
    except (json.JSONDecodeError, AttributeError) as exc:
        raise PlanParsingError(
            f'Malformed match output {raw_content!r}: {exc}'
        ) from exc

    if intent == 'converse':
        reply = raw.get('reply')
        if not isinstance(reply, str) or not reply.strip():
            raise PlanParsingError(
                f'Converse intent missing non-empty "reply" field: {raw_content!r}'
            )
        return None, 1.0, reply.strip()

    if intent == 'workflow':
        try:
            template_name = raw['template_name']
            confidence = float(raw['confidence'])
        except (KeyError, TypeError, ValueError) as exc:
            raise PlanParsingError(
                f'Workflow intent missing template_name/confidence: {raw_content!r}: {exc}'
            ) from exc
        if not 0.0 <= confidence <= 1.0:
            raise PlanParsingError(f'confidence {confidence} out of range [0.0, 1.0]')
        return template_name, confidence, None

    raise PlanParsingError(
        f'Unknown intent {intent!r} in {raw_content!r}. Expected "converse" or "workflow".'
    )


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
        """Classify the officer's message and return the appropriate result.

        Three possible outcomes (mirroring ``PlanResult``'s three modes):

        1. **Conversational** — the message was a greeting or general question;
           a ``conversational_reply`` is returned directly without touching any
           workflow.  This is the key change vs the original implementation:
           the Planner is no longer forced to pick a template for every input.

        2. **Workflow selected** — clear intent + all required parameters
           supplied → ``template_name`` + ``parameters`` returned.

        3. **Clarification** — workflow intent detected but confidence below
           threshold, or required parameters missing → ``clarification_question``
           returned (§5.2.1 escalation rule).
        """

        supplied_parameters = parameters or {}

        if self._matcher is not None:
            template_name, confidence, converse_reply = await self._matcher(
                objective, self._templates
            )
        else:
            template_name, confidence, converse_reply = await self._default_matcher(
                objective
            )

        # ── Conversational path ─────────────────────────────────────────────
        if template_name is None and converse_reply is not None:
            return PlanResult(
                template_name=None,
                confidence=1.0,
                conversational_reply=converse_reply,
            )

        # ── Workflow path ───────────────────────────────────────────────────
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
                    f'I could not confidently match your request to a known '
                    f'workflow (confidence {confidence:.2f}). Could you clarify '
                    f'what you want to do — for example, review a document, '
                    f'assess a loan application, or research a market sector?'
                ),
            )

        template = next(t for t in self._templates if t.name == template_name)
        missing = [
            p for p in template.required_parameters if p not in supplied_parameters
        ]
        if missing:
            missing_str = ', '.join(f'"{p}"' for p in missing)
            return PlanResult(
                template_name=None,
                confidence=confidence,
                clarification_question=(
                    f'To start the "{template.name}" workflow I need '
                    f'{missing_str}. Could you provide '
                    f'{"these" if len(missing) > 1 else "this"}?'
                ),
            )

        return PlanResult(
            template_name=template.name,
            parameters=supplied_parameters,
            confidence=confidence,
        )

    async def _default_matcher(
        self, objective: str
    ) -> tuple[str | None, float, str | None]:
        """Call the LLM with a system prompt and the dual-intent prompt."""
        prompt = _build_match_prompt(objective, self._templates)
        response = await self._llm_client.complete_for_agent(
            AgentName.PLANNER,
            [
                {'role': 'system', 'content': SYSTEM_PROMPT},
                {'role': 'user', 'content': prompt},
            ],
        )
        content = response.choices[0].message.content
        if content is None:
            raise PlanParsingError('Model returned no content')
        return _parse_match(content)
