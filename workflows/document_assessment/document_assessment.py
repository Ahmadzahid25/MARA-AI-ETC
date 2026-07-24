"""Document Assessment workflow — docs/architecture/07-workflow-architecture.md
§7.3's catalogue: "Officer uploads a document set for review, standalone";
agents "Document → Compliance"; approval gate "Officer confirms extraction
before it's used elsewhere."

Applies the common 8-stage model (§7.1: Start -> Planning -> Delegation ->
Execution -> Validation -> Approval -> Completion -> Audit) to this specific
bounded template. Start/Planning/Delegation are collapsed here rather than
implemented as separate nodes: the Planner and `services/supervisor_service`
that would normally own those stages don't exist yet (later Milestone work)
— this template is invoked directly with its parameters already decided,
which is a legitimate simplification for now, not a deviation from the
target shape. Execution/Validation/Approval/Completion are real nodes.

Per docs/architecture/05-agent-architecture.md §5.3, the extraction-
confirmation Approval gate happens *before* Compliance Agent runs, since
Compliance consumes Document Agent's output and §5.3 requires confirmation
"before use in any downstream calculation or claim." The pause is a real
LangGraph ``interrupt()`` (docs/architecture/07-workflow-architecture.md's
"durable pause ... can resume after days" — the same primitive
shared/workflow_engine/checkpointer.py's Postgres checkpointer already
supports), not a placeholder.

A rejected extraction currently routes straight to Completion rather than a
targeted re-run of Document Agent — real re-run routing per §7.4 is a later
refinement; this template does not yet lose the rejection (it's recorded in
``approval_decision``), it just doesn't automatically retry.
"""

from __future__ import annotations

from typing import TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from agents.compliance_agent.compliance_agent import ComplianceAgent
from agents.document_agent.document_agent import DocumentAgent
from shared.schemas.compliance import ComplianceChecklist
from shared.schemas.documents import DocumentExtractionRecord


class ApprovalDecision(TypedDict, total=False):
    status: str  # 'approved' | 'rejected' | 'corrected'
    actor: str
    reason: str
    corrected_fields: list[dict]


class DocumentAssessmentState(TypedDict):
    document_id: str
    pdf_bytes: bytes
    compliance_requirements: list[str]
    extraction_record: DocumentExtractionRecord | None
    compliance_checklist: ComplianceChecklist | None
    validation_notes: list[str]
    approval_decision: ApprovalDecision | None
    stage_log: list[str]


def build_document_assessment_graph(
    document_agent: DocumentAgent,
    compliance_agent: ComplianceAgent,
) -> StateGraph:
    async def _document_extraction_node(state: DocumentAssessmentState) -> dict:
        record = await document_agent.process_document(
            state['document_id'], state['pdf_bytes']
        )
        return {
            'extraction_record': record,
            'stage_log': [*state['stage_log'], 'document_extraction'],
        }

    def _validation_node(state: DocumentAssessmentState) -> dict:
        record = state['extraction_record']
        assert record is not None  # guaranteed by graph ordering
        low_confidence = record.low_confidence_fields(
            threshold=document_agent.confidence_threshold
        )
        notes = (
            [f'{len(low_confidence)} field(s) below confidence threshold']
            if low_confidence
            else []
        )
        return {
            'validation_notes': notes,
            'stage_log': [*state['stage_log'], 'validation'],
        }

    def _confirm_extraction_node(state: DocumentAssessmentState) -> dict:
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

        updates: dict = {
            'approval_decision': decision,
            'stage_log': [*state['stage_log'], 'confirm_extraction'],
        }

        # docs/architecture/10-human-in-the-loop.md §10.5: a Correct action's
        # values must actually reach downstream consumers (Compliance Agent
        # here), not just be recorded — the correction is attributed
        # separately (services/approval_service owns that audit record) but
        # the *workflow* has to see the corrected value, or "Correct" would
        # record a fix nothing downstream ever uses.
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

    async def _compliance_check_node(state: DocumentAssessmentState) -> dict:
        record = state['extraction_record']
        assert record is not None
        checklist = await compliance_agent.check_compliance(
            state['document_id'], record, state['compliance_requirements']
        )
        return {
            'compliance_checklist': checklist,
            'stage_log': [*state['stage_log'], 'compliance_check'],
        }

    def _completion_node(state: DocumentAssessmentState) -> dict:
        return {'stage_log': [*state['stage_log'], 'completion']}

    def _route_after_confirmation(state: DocumentAssessmentState) -> str:
        decision = state.get('approval_decision') or {}
        if decision.get('status') == 'approved':
            return 'compliance_check'
        return 'completion'

    graph = StateGraph(DocumentAssessmentState)
    graph.add_node('document_extraction', _document_extraction_node)
    graph.add_node('validation', _validation_node)
    graph.add_node('confirm_extraction', _confirm_extraction_node)
    graph.add_node('compliance_check', _compliance_check_node)
    graph.add_node('completion', _completion_node)

    graph.add_edge(START, 'document_extraction')
    graph.add_edge('document_extraction', 'validation')
    graph.add_edge('validation', 'confirm_extraction')
    graph.add_conditional_edges(
        'confirm_extraction',
        _route_after_confirmation,
        {'compliance_check': 'compliance_check', 'completion': 'completion'},
    )
    graph.add_edge('compliance_check', 'completion')
    graph.add_edge('completion', END)
    return graph
