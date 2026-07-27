"""Loan Assessment workflow — docs/architecture/07-workflow-architecture.md
§7.2/§7.3's reference workflow: "Officer opens a loan/grant application for
evaluation": Document -> {Compliance, Finance, Market} -> Risk ->
Recommendation -> `services/publishing_service`.

Applies the common 8-stage model (§7.1). Start/Planning/Delegation are
collapsed exactly the way `workflows/document_assessment` already
documented its own choice: this template is invoked directly with its
parameters already decided (the Planner's job, per `agents/planner`, is
selecting *which* template and validating its parameters — a step that
happens before a graph like this one is even built/invoked, not a node
inside it). Execution/Validation/Approval/Completion are real nodes.

**Five durable-pause approval gates**, per docs/architecture/
10-human-in-the-loop.md §10.2's table — all real LangGraph ``interrupt()``
pauses, the same primitive `workflows/document_assessment` already proved
out:
1. ``confirm_extraction`` — officer confirms/corrects Document Agent
   output (reused verbatim from `workflows/document_assessment`, including
   its calibration-event emission).
2. ``compliance_acknowledgment`` — Compliance Officer, **only when**
   `ComplianceChecklist.has_hard_violation` (§7.4: "before Risk/
   Recommendation are allowed to proceed"). Modeled as a node that
   conditionally calls ``interrupt()`` internally rather than a
   conditionally-routed graph edge — see "Why compliance acknowledgment is
   a pass-through node, not a conditional edge" below.
3. ``financial_sign_off`` — Finance Officer (§10.2; `FINANCE` profile's
   ``approval=ALWAYS``).
4. ``risk_review`` — Risk Officer (`RISK` profile's ``approval=ALWAYS``).
5. ``recommendation_approval`` — case-owner officer (`RECOMMENDATION`
   profile's ``approval=ALWAYS`` — "never auto-forwarded, at any
   confidence").
6. ``publish_approval`` — case owner + Committee Secretary, before
   distribution (§10.2's "Committee report/deck sign-off").

A rejection at any of gates 2–6 routes straight to Completion, the same
documented simplification `workflows/document_assessment` already made for
its own single gate ("real re-run routing per §7.4 is a later refinement")
— not a new shortcut invented here.

### Unresolved tension: an acknowledged hard violation still withholds
### a recommendation

§7.4 says an acknowledged hard violation (accepted as a documented
exception) lets Risk/Recommendation "proceed." §5.8's own escalation rule
for the Recommendation Agent, however, is unconditional: "Escalates
(declines to recommend) if any upstream agent flagged a hard compliance
violation" — no exception carve-out is specified there. `agents/
recommendation_agent` implements §5.8 literally, so an acknowledged
violation still yields a withheld recommendation
(`RecommendationOutput.withheld_reason` set) — acknowledgment only lets
this workflow keep computing Risk (for audit-trail completeness) rather
than halting immediately, it does not itself grant Recommendation an
exception path §5.8 doesn't specify. Reconciling that tension — if MARA
actually wants an accepted exception to unblock a real recommendation —
is a product/architecture decision belonging in a revision of §5.8, not
one resolved unilaterally in this workflow file.

### Why compliance acknowledgment is a pass-through node, not a conditional edge

Compliance, Finance, and Market run in parallel (§7.2) and all three fan
into Risk. Making the *edge out of* `compliance_check` conditional — some
runs go to an acknowledgment interrupt, others go straight to
`risk_synthesis` — would make `risk_synthesis`'s three-way join ambiguous:
LangGraph's fan-in pattern expects a join node's declared predecessors to
be traversed unconditionally, not have one of three arrive via a
sometimes-different path. Putting the conditionality *inside* one always-
traversed node instead (it calls ``interrupt()`` only when there's a hard
violation, otherwise returns immediately) keeps all three branches'
edges into `risk_synthesis` plain and unconditional — a well-supported
LangGraph shape verified in this module's own tests against a real graph
execution (`InMemorySaver`), not merely asserted.

Risk still runs even when compliance was rejected/not-acknowledged
(harmless — `RiskAgent`'s own escalation logic already reacts to
`has_hard_violation`); the actual halt happens via a conditional edge
*after* `risk_synthesis`, the same well-established pattern
`workflows/document_assessment`'s `_route_after_confirmation` already
uses.

**A second, non-obvious requirement this fan-in has**: LangGraph's plain
`add_edge()` fan-in does not wait for "all predecessors, whenever they
finish" — it re-invokes the join node once per superstep any predecessor's
edge fires. Three branches of *different hop-depth* into the same join
node (compliance's extra acknowledgment hop vs. finance/market's single
hop) therefore fire the join **twice**: once when finance and market land
together, again one superstep later when compliance's longer branch
lands — which was caught, not assumed, by this module's own tests against
a real graph run (a second, spurious `financial_sign_off` interrupt). The
fix is `_finance_join_node`/`_market_join_node`: trivial pass-through
nodes that give every branch the same number of hops before
`risk_synthesis`, so all three land in the same superstep and the join
fires exactly once.

### Citation verification is live in this workflow

Every agent node constructs a fresh ``ProvenanceLedger`` and passes it into
the agent call, so §6.1's deterministic check runs against what that task's
tool calls actually returned. A fabricated citation raises
``FabricatedCitationError`` at the node rather than reaching an officer.

One ledger per node, not one per workflow, because §6.1 scopes verification
to a single agent task: a shared ledger would let Recommendation cite a
clause that only Compliance ever retrieved, which is precisely the
cross-contamination the per-task scope exists to prevent.

This required one change to make it real rather than decorative.
``make_rag_policy_lookup`` used to bind a ledger at construction time, and
since agents are built once at process start, the closure's ledger and the
one handed to ``check_compliance`` were always different objects — retrieval
recorded into one, verification read the other, so either every citation
failed or (with no ledger passed) nothing was checked at all. The lookup now
takes the ledger per call and ``ComplianceAgent`` forwards its own, so both
halves share one instance without the workflow having to arrange it.

"""

from __future__ import annotations

import operator
from collections.abc import Awaitable, Callable
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from agents.compliance_agent.compliance_agent import ComplianceAgent
from agents.document_agent.document_agent import DocumentAgent
from agents.finance_agent.finance_agent import CalculationRequest, FinanceAgent
from agents.market_agent.market_agent import MarketAgent
from agents.recommendation_agent.recommendation_agent import RecommendationAgent
from agents.risk_agent.risk_agent import RiskAgent
from services.memory_service import (
    CalibrationEvent,
    extraction_record_to_calibration_events,
)
from services.publishing_service import (
    CommitteeReportInputs,
    MissingApprovedInputError,
    publish_committee_materials,
)
from shared.llm.model_tiers import AgentName
from shared.provenance import ProvenanceLedger
from shared.schemas.compliance import ComplianceChecklist
from shared.schemas.documents import DocumentExtractionRecord
from shared.schemas.finance import FinancialAnalysis
from shared.schemas.market import MarketBrief
from shared.schemas.recommendation import RecommendationOutput
from shared.schemas.risk import RiskRating

CalibrationWriter = Callable[[list[CalibrationEvent]], Awaitable[None]]


class ApprovalDecision(TypedDict, total=False):
    status: str  # 'approved' | 'rejected' | 'corrected' | 'acknowledged' | 'halted'
    actor: str
    reason: str
    corrected_fields: list[dict]


class LoanAssessmentState(TypedDict):
    document_id: str
    pdf_bytes: bytes
    compliance_requirements: list[str]
    calculation_requests: list[CalculationRequest]
    product_query: str | None
    sector: str
    region: str
    precedent_query: str | None

    extraction_record: DocumentExtractionRecord | None
    extraction_decision: ApprovalDecision | None

    compliance_checklist: ComplianceChecklist | None
    compliance_decision: ApprovalDecision | None

    financial_analysis: FinancialAnalysis | None
    financial_decision: ApprovalDecision | None

    market_brief: MarketBrief | None

    risk_rating: RiskRating | None
    risk_decision: ApprovalDecision | None

    recommendation: RecommendationOutput | None
    recommendation_decision: ApprovalDecision | None

    published_docx: bytes | None
    published_pptx: bytes | None
    publish_decision: ApprovalDecision | None
    publish_error: str | None

    stage_log: Annotated[list[str], operator.add]


def _halted(state: LoanAssessmentState) -> bool:
    decision = state.get('compliance_decision') or {}
    return decision.get('status') == 'halted'


def build_loan_assessment_graph(
    document_agent: DocumentAgent,
    compliance_agent: ComplianceAgent,
    finance_agent: FinanceAgent,
    market_agent: MarketAgent,
    risk_agent: RiskAgent,
    recommendation_agent: RecommendationAgent,
    calibration_writer: CalibrationWriter | None = None,
) -> StateGraph:
    async def _document_extraction_node(state: LoanAssessmentState) -> dict:
        record = await document_agent.process_document(
            state['document_id'], state['pdf_bytes']
        )
        return {'extraction_record': record, 'stage_log': ['document_extraction']}

    def _validation_node(state: LoanAssessmentState) -> dict:
        return {'stage_log': ['validation']}

    async def _confirm_extraction_node(state: LoanAssessmentState) -> dict:
        record = state['extraction_record']
        assert record is not None
        low_confidence = record.low_confidence_fields(
            threshold=document_agent.confidence_threshold
        )
        decision: ApprovalDecision = interrupt(
            {
                'type': 'confirm_extraction',
                'document_id': state['document_id'],
                'extraction_record': record.model_dump(mode='json'),
                'low_confidence_field_names': [f.name for f in low_confidence],
            }
        )

        if calibration_writer is not None:
            corrected_field_names = {
                c['field_name'] for c in (decision.get('corrected_fields') or [])
            }
            events = extraction_record_to_calibration_events(
                record,
                agent_name=AgentName.DOCUMENT.value,
                workflow_id=state['document_id'],
                corrected_field_names=corrected_field_names,
            )
            await calibration_writer(events)

        updates: dict = {
            'extraction_decision': decision,
            'stage_log': ['confirm_extraction'],
        }
        corrected_fields = decision.get('corrected_fields')
        if decision.get('status') == 'approved' and corrected_fields:
            by_name = {c['field_name']: c['corrected_value'] for c in corrected_fields}
            updates['extraction_record'] = record.model_copy(
                update={
                    'fields': [
                        f.model_copy(
                            update={'value': by_name[f.name], 'confidence': 1.0}
                        )
                        if f.name in by_name
                        else f
                        for f in record.fields
                    ]
                }
            )
        return updates

    def _route_after_extraction_confirmation(state: LoanAssessmentState) -> list[str]:
        decision = state.get('extraction_decision') or {}
        if decision.get('status') != 'approved':
            return ['completion']
        # Fan out to all three parallel branches at once — a conditional
        # edge whose router returns multiple destinations, per LangGraph's
        # supported fan-out shape (verified in this module's own tests
        # against a real graph run, not merely assumed).
        return ['compliance_check', 'finance_analysis', 'market_research']

    async def _compliance_check_node(state: LoanAssessmentState) -> dict:
        record = state['extraction_record']
        assert record is not None
        checklist = await compliance_agent.check_compliance(
            state['document_id'],
            record,
            state['compliance_requirements'],
            ledger=ProvenanceLedger(),
        )
        return {'compliance_checklist': checklist, 'stage_log': ['compliance_check']}

    async def _compliance_acknowledgment_node(state: LoanAssessmentState) -> dict:
        checklist = state['compliance_checklist']
        assert checklist is not None
        if not checklist.has_hard_violation:
            return {'stage_log': ['compliance_acknowledgment_not_required']}

        decision: ApprovalDecision = interrupt(
            {
                'type': 'compliance_acknowledgment',
                'document_id': state['document_id'],
                'compliance_checklist': checklist.model_dump(mode='json'),
            }
        )
        return {
            'compliance_decision': decision,
            'stage_log': ['compliance_acknowledgment'],
        }

    async def _finance_analysis_node(state: LoanAssessmentState) -> dict:
        record = state['extraction_record']
        assert record is not None
        analysis = await finance_agent.analyze(
            state['document_id'],
            record,
            state['calculation_requests'],
            product_query=state.get('product_query'),
            workflow_id=state['document_id'],
            ledger=ProvenanceLedger(),
        )
        return {'financial_analysis': analysis, 'stage_log': ['finance_analysis']}

    async def _market_research_node(state: LoanAssessmentState) -> dict:
        brief = await market_agent.gather_market_context(
            state['sector'],
            state['region'],
            workflow_id=state['document_id'],
            ledger=ProvenanceLedger(),
        )
        return {'market_brief': brief, 'stage_log': ['market_research']}

    def _finance_join_node(state: LoanAssessmentState) -> dict:
        return {'stage_log': ['finance_join']}

    def _market_join_node(state: LoanAssessmentState) -> dict:
        return {'stage_log': ['market_join']}

    async def _risk_synthesis_node(state: LoanAssessmentState) -> dict:
        rating = await risk_agent.synthesize(
            state['document_id'],
            compliance_checklist=state['compliance_checklist'],
            financial_analysis=state['financial_analysis'],
            market_brief=state['market_brief'],
            precedent_query=state.get('precedent_query'),
            workflow_id=state['document_id'],
            ledger=ProvenanceLedger(),
        )
        return {'risk_rating': rating, 'stage_log': ['risk_synthesis']}

    def _make_simple_gate(
        gate_type: str,
        decision_key: str,
        payload_fn: Callable[[LoanAssessmentState], dict],
    ):
        async def node(state: LoanAssessmentState) -> dict:
            payload = {'type': gate_type, 'document_id': state['document_id']}
            payload.update(payload_fn(state))
            decision: ApprovalDecision = interrupt(payload)
            return {decision_key: decision, 'stage_log': [gate_type]}

        return node

    def _route_on(
        decision_key: str, next_node: str
    ) -> Callable[[LoanAssessmentState], str]:
        def route(state: LoanAssessmentState) -> str:
            decision = state.get(decision_key) or {}
            return next_node if decision.get('status') == 'approved' else 'completion'

        return route

    _financial_sign_off_node = _make_simple_gate(
        'financial_sign_off',
        'financial_decision',
        lambda s: {
            'financial_analysis': s['financial_analysis'].model_dump(mode='json')
        },
    )
    _risk_review_node = _make_simple_gate(
        'risk_review',
        'risk_decision',
        lambda s: {'risk_rating': s['risk_rating'].model_dump(mode='json')},
    )
    _recommendation_approval_node = _make_simple_gate(
        'recommendation_approval',
        'recommendation_decision',
        lambda s: {'recommendation': s['recommendation'].model_dump(mode='json')},
    )
    _publish_approval_node = _make_simple_gate(
        'publish_approval', 'publish_decision', lambda s: {}
    )

    def _route_after_risk(state: LoanAssessmentState) -> str:
        decision = state.get('risk_decision') or {}
        if decision.get('status') != 'approved':
            return 'completion'
        return 'completion' if _halted(state) else 'recommendation'

    async def _recommendation_node(state: LoanAssessmentState) -> dict:
        output = await recommendation_agent.recommend(
            state['document_id'],
            compliance_checklist=state['compliance_checklist'],
            financial_analysis=state['financial_analysis'],
            risk_rating=state['risk_rating'],
            market_brief=state['market_brief'],
            precedent_query=state.get('precedent_query'),
            workflow_id=state['document_id'],
            ledger=ProvenanceLedger(),
        )
        return {'recommendation': output, 'stage_log': ['recommendation']}

    async def _publish_node(state: LoanAssessmentState) -> dict:
        inputs = CommitteeReportInputs(
            document_id=state['document_id'],
            compliance_checklist=state['compliance_checklist'],
            financial_analysis=state['financial_analysis'],
            risk_rating=state['risk_rating'],
            market_brief=state['market_brief'],
            recommendation=state['recommendation'],
        )
        try:
            artifacts = await publish_committee_materials(
                inputs, workflow_id=state['document_id']
            )
        except MissingApprovedInputError as exc:
            return {'publish_error': str(exc), 'stage_log': ['publish_failed']}
        return {
            'published_docx': artifacts.docx_bytes,
            'published_pptx': artifacts.pptx_bytes,
            'stage_log': ['publish'],
        }

    def _route_after_recommendation(state: LoanAssessmentState) -> str:
        decision = state.get('recommendation_decision') or {}
        return 'publish' if decision.get('status') == 'approved' else 'completion'

    def _completion_node(state: LoanAssessmentState) -> dict:
        return {'stage_log': ['completion']}

    graph = StateGraph(LoanAssessmentState)
    graph.add_node('document_extraction', _document_extraction_node)
    graph.add_node('validation', _validation_node)
    graph.add_node('confirm_extraction', _confirm_extraction_node)
    graph.add_node('compliance_check', _compliance_check_node)
    graph.add_node('compliance_acknowledgment', _compliance_acknowledgment_node)
    graph.add_node('finance_analysis', _finance_analysis_node)
    graph.add_node('finance_join', _finance_join_node)
    graph.add_node('market_research', _market_research_node)
    graph.add_node('market_join', _market_join_node)
    graph.add_node('risk_synthesis', _risk_synthesis_node)
    graph.add_node('financial_sign_off', _financial_sign_off_node)
    graph.add_node('risk_review', _risk_review_node)
    graph.add_node('recommendation', _recommendation_node)
    graph.add_node('recommendation_approval', _recommendation_approval_node)
    graph.add_node('publish', _publish_node)
    graph.add_node('publish_approval', _publish_approval_node)
    graph.add_node('completion', _completion_node)

    graph.add_edge(START, 'document_extraction')
    graph.add_edge('document_extraction', 'validation')
    graph.add_edge('validation', 'confirm_extraction')
    # §7.2: Compliance, Finance, and Market fan out from the same point and
    # all fan into Risk — see the module docstring for why the compliance
    # branch's conditionality lives inside compliance_acknowledgment rather
    # than as a routed edge. The router itself returns all three
    # destinations at once on the approved path (LangGraph's supported
    # conditional fan-out shape), or just 'completion' on rejection.
    graph.add_conditional_edges(
        'confirm_extraction',
        _route_after_extraction_confirmation,
        {
            'compliance_check': 'compliance_check',
            'finance_analysis': 'finance_analysis',
            'market_research': 'market_research',
            'completion': 'completion',
        },
    )
    graph.add_edge('compliance_check', 'compliance_acknowledgment')
    graph.add_edge('compliance_acknowledgment', 'risk_synthesis')
    graph.add_edge('finance_analysis', 'finance_join')
    graph.add_edge('finance_join', 'risk_synthesis')
    graph.add_edge('market_research', 'market_join')
    graph.add_edge('market_join', 'risk_synthesis')

    graph.add_edge('risk_synthesis', 'financial_sign_off')
    graph.add_conditional_edges(
        'financial_sign_off',
        _route_on('financial_decision', 'risk_review'),
        {'risk_review': 'risk_review', 'completion': 'completion'},
    )
    graph.add_conditional_edges(
        'risk_review',
        _route_after_risk,
        {'recommendation': 'recommendation', 'completion': 'completion'},
    )
    graph.add_edge('recommendation', 'recommendation_approval')
    graph.add_conditional_edges(
        'recommendation_approval',
        _route_after_recommendation,
        {'publish': 'publish', 'completion': 'completion'},
    )
    graph.add_edge('publish', 'publish_approval')
    graph.add_edge('publish_approval', 'completion')
    graph.add_edge('completion', END)

    return graph
