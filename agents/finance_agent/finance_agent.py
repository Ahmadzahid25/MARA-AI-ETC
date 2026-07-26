"""Finance Agent — docs/architecture/05-agent-architecture.md §5.5.

    Responsibilities: perform financial analysis (ratios, cash flow
    assessment, loan-to-value, repayment capacity) from extracted figures
    Confidence threshold: N/A for arithmetic (deterministic); 0.85 for
    qualitative judgments
    Model tier: Sonnet-class (synthesis tier)

Orchestrates tools/calculations (the deterministic arithmetic — never LLM
mental math for a figure that informs a decision, per §6.2) and
tools/rag (product terms lookup), then does the one genuinely agentic step:
interpreting the calculated figures into a qualitative repayment-capacity
narrative is genuine synthesis, per §5.5's model-tier note — exactly the
agent-vs-service test in §5.14 keeping this in ``agents/``, not
``tools/``.

Per §5.5's escalation rule ("If required source figures are missing or
below Document Agent confidence threshold, escalates rather than computing
on unverified input"), ``analyze()`` raises ``MissingSourceFigureError``
rather than silently computing on an unverified or absent field — the
caller (the owning workflow) is responsible for turning that into an
officer escalation, mirroring how ``agents/document_agent`` surfaces
low-confidence fields rather than resolving them itself.

Product-terms lookup goes through the real Milestone-2 Knowledge Service
boundary (``services.knowledge_service.contract.KnowledgeBackend``,
``tools.rag.rag_tool.rag_query``) — the same seam
``agents/compliance_agent/policy_lookup.py`` uses — rather than an
invented shape, so this agent and Compliance/Risk/Market all speak the
same retrieval contract.
"""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable

from services.knowledge_service.contract import KnowledgeBackend
from shared.agent_profiles import confidence_threshold_for, profile_for
from shared.llm.client import TieredLLMClient
from shared.llm.model_tiers import AgentName
from shared.provenance import ProvenanceLedger
from shared.schemas.documents import DocumentExtractionRecord
from shared.schemas.finance import FigureProvenance, FinancialAnalysis, FinancialFigure
from shared.schemas.knowledge import (
    DocumentKind,
    PolicyCitation,
    RetrievalFilters,
    RetrievalQuery,
)
from tools.calculations.calculation_tool import CalculationResult, calculate
from tools.rag.rag_tool import rag_query

PROFILE = profile_for(AgentName.FINANCE.value)
# Sourced from the profile registry — see shared/agent_profiles/profiles.py.
ASSESSMENT_CONFIDENCE_THRESHOLD = confidence_threshold_for(AgentName.FINANCE.value)
DOCUMENT_FIELD_CONFIDENCE_THRESHOLD = 0.85


class MissingSourceFigureError(Exception):
    """§5.5's escalation rule: a calculation's required source field is
    either absent from the extraction record or below the Document Agent's
    own confidence threshold. Never silently computed on anyway."""


class FinancialAssessmentParsingError(Exception):
    """The qualitative-assessment step (LLM or injected assessor) returned
    output that doesn't match the required shape — surfaced, never
    silently defaulted to a guessed narrative/confidence."""


class CalculationRequest:
    """One calculation to run: which formula, and which extraction-record
    field name feeds each of the formula's named inputs. Kept separate from
    ``shared/schemas`` since this is Finance Agent call-shape, not a
    cross-service contract."""

    __slots__ = ('formula_id', 'field_mapping', 'formula_version')

    def __init__(
        self,
        formula_id: str,
        field_mapping: dict[str, str],
        formula_version: str | None = None,
    ) -> None:
        self.formula_id = formula_id
        self.field_mapping = field_mapping
        self.formula_version = formula_version


# (figures so far) -> (assessment narrative, confidence). The default calls
# the LLM (Sonnet tier); tests inject a deterministic fake.
Assessor = Callable[[list[FinancialFigure]], Awaitable[tuple[str, float]]]

CalculateFn = Callable[[str, dict[str, float], str | None], CalculationResult]


def _default_calculate(
    formula_id: str,
    inputs: dict[str, float],
    version: str | None,
    *,
    workflow_id: str | None,
    audit_sink,
) -> CalculationResult:
    return calculate(
        formula_id,
        inputs,
        caller_agent=AgentName.FINANCE.value,
        workflow_id=workflow_id,
        version=version,
        audit_sink=audit_sink,
    )


def _build_assessment_prompt(figures: list[FinancialFigure]) -> str:
    figures_text = '\n'.join(
        f'- {f.name}: {f.value} ({f.provenance.value})' for f in figures
    )
    return (
        f'Financial figures for this application:\n{figures_text}\n\n'
        f'Write a short qualitative repayment-capacity assessment. Respond '
        f'with a JSON object with exactly these keys: "assessment" '
        f'(string), "confidence" (float 0.0-1.0, your genuine confidence in '
        f'this assessment). Respond with the JSON object only, no other '
        f'text.'
    )


def _parse_llm_assessment(raw_content: str) -> tuple[str, float]:
    try:
        raw = json.loads(raw_content)
        assessment = str(raw['assessment'])
        confidence = float(raw['confidence'])
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        raise FinancialAssessmentParsingError(
            f'Malformed assessment output {raw_content!r}: {exc}'
        ) from exc
    if not 0.0 <= confidence <= 1.0:
        raise FinancialAssessmentParsingError(
            f'confidence {confidence} out of range [0.0, 1.0]'
        )
    return assessment, confidence


class FinanceAgent:
    """Configuration of the (not-yet-built) Agent Runtime for financial
    analysis — role/goal/tools/confidence-threshold, per docs/architecture/
    05-agent-architecture.md §5.1."""

    profile = PROFILE
    confidence_threshold: float = ASSESSMENT_CONFIDENCE_THRESHOLD
    allowed_tools = PROFILE.allowed_tools

    def __init__(
        self,
        llm_client: TieredLLMClient | None = None,
        assessor: Assessor | None = None,
        calculate_fn: CalculateFn | None = None,
        backend: KnowledgeBackend | None = None,
    ) -> None:
        self._llm_client = llm_client or TieredLLMClient()
        self._assessor = assessor
        self._calculate_fn = calculate_fn or _default_calculate
        self._backend = backend

    async def analyze(
        self,
        document_id: str,
        extraction_record: DocumentExtractionRecord,
        calculation_requests: list[CalculationRequest],
        *,
        product_query: str | None = None,
        workflow_id: str | None = None,
        rag_top_k: int = 3,
        ledger: ProvenanceLedger | None = None,
        audit_sink=None,
    ) -> FinancialAnalysis:
        """Run each of ``calculation_requests`` over ``extraction_record``,
        then produce a qualitative assessment over the resulting figures.
        Raises ``MissingSourceFigureError`` per §5.5's escalation rule if
        any required source field is absent or unverified.
        """

        field_by_name = {f.name: f for f in extraction_record.fields}
        figures: list[FinancialFigure] = []
        extracted_names_seen: set[str] = set()

        for request in calculation_requests:
            inputs: dict[str, float] = {}
            for formula_input_name, field_name in request.field_mapping.items():
                field = field_by_name.get(field_name)
                if field is None:
                    raise MissingSourceFigureError(
                        f'Required field {field_name!r} not found in the '
                        f'extraction record for document {document_id!r}'
                    )
                if field.confidence < DOCUMENT_FIELD_CONFIDENCE_THRESHOLD:
                    raise MissingSourceFigureError(
                        f'Field {field_name!r} confidence {field.confidence} '
                        f'is below the Document Agent threshold '
                        f'{DOCUMENT_FIELD_CONFIDENCE_THRESHOLD} — requires '
                        'officer confirmation before use in any calculation '
                        '(docs/architecture/05-agent-architecture.md §5.3)'
                    )
                inputs[formula_input_name] = float(field.value)
                if field_name not in extracted_names_seen:
                    figures.append(
                        FinancialFigure(
                            name=field_name,
                            value=float(field.value),
                            provenance=FigureProvenance.EXTRACTED,
                            source_citation=field.citation,
                        )
                    )
                    extracted_names_seen.add(field_name)

            calc_result = self._calculate_fn(
                request.formula_id,
                inputs,
                request.formula_version,
                workflow_id=workflow_id,
                audit_sink=audit_sink,
            )
            figures.append(
                FinancialFigure(
                    name=request.formula_id,
                    value=calc_result.value,
                    provenance=FigureProvenance.CALCULATED,
                    formula_id=calc_result.formula_id,
                    formula_version=calc_result.formula_version,
                )
            )

        product_term_citations: list[PolicyCitation] = []
        if product_query is not None:
            result = await rag_query(
                RetrievalQuery(
                    query=product_query,
                    top_k=rag_top_k,
                    filters=RetrievalFilters(
                        document_kinds=frozenset({DocumentKind.PRODUCT_TERMS})
                    ),
                ),
                caller_agent=AgentName.FINANCE.value,
                workflow_id=workflow_id,
                backend=self._backend,
                ledger=ledger,
                audit_sink=audit_sink,
            )
            if not result.no_confident_match:
                product_term_citations = [
                    PolicyCitation.from_chunk(chunk) for chunk in result.chunks
                ]

        if self._assessor is not None:
            assessment, confidence = await self._assessor(figures)
        else:
            assessment, confidence = await self._default_assessor(figures)

        if ledger is not None:
            # §6.1, mirroring agents/compliance_agent/compliance_agent.py: these
            # citations are built directly from what rag_query just returned
            # (PolicyCitation.from_chunk), so this can never actually reject —
            # kept for the same reason the Compliance Agent keeps it: the
            # invariant should be enforced the same way everywhere, not
            # skipped somewhere on the argument that it happens to be safe
            # here today.
            ledger.require_verified(
                tuple(c.to_citable_ref() for c in product_term_citations)
            )

        return FinancialAnalysis(
            document_id=document_id,
            figures=figures,
            assessment=assessment,
            assessment_confidence=confidence,
            product_term_citations=product_term_citations,
        )

    async def _default_assessor(
        self, figures: list[FinancialFigure]
    ) -> tuple[str, float]:
        prompt = _build_assessment_prompt(figures)
        response = await self._llm_client.complete_for_agent(
            AgentName.FINANCE, [{'role': 'user', 'content': prompt}]
        )
        content = response.choices[0].message.content
        if content is None:
            raise FinancialAssessmentParsingError('Model returned no content')
        return _parse_llm_assessment(content)
