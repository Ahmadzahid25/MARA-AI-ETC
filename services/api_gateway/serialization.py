"""Shared response shaping for the Document Assessment routers
(``documents.py`` and ``approvals.py``) — both need to turn a raw
LangGraph invoke/resume result into the same JSON shape, whether the
workflow just paused again or ran to completion.
"""

from __future__ import annotations


def serialize_workflow_result(document_id: str, result: dict) -> dict:
    interrupts = result.get('__interrupt__')
    if interrupts:
        payload = interrupts[0].value
        return {
            'document_id': document_id,
            'thread_id': document_id,
            'status': 'pending_confirmation',
            'extraction_record': payload['extraction_record'],
            'low_confidence_field_names': payload['low_confidence_field_names'],
        }
    return {
        'document_id': document_id,
        'thread_id': document_id,
        'status': 'completed',
        'stage_log': result.get('stage_log', []),
    }


def serialize_loan_result(
    document_id: str, result: dict, acted_gate: str | None = None
) -> dict:
    """Shape a Loan Assessment invoke/resume result for the client.

    Reports the gate the workflow is *now* waiting at rather than a generic
    "pending", because with six gates the client otherwise cannot tell which
    approver to route to next — and per §10.2 that differs at every stage.
    The payload each gate interrupts with is passed through untouched, since
    what an officer needs to see differs by gate (extraction fields at one,
    a risk rating at another) and flattening them into a common shape would
    lose exactly the evidence §10.4 requires be shown.
    """

    response: dict = {
        'document_id': document_id,
        'thread_id': document_id,
        'stage_log': result.get('stage_log', []),
    }
    if acted_gate is not None:
        response['acted_gate'] = acted_gate

    interrupts = result.get('__interrupt__')
    if interrupts:
        payload = interrupts[0].value
        response['status'] = 'pending_approval'
        response['pending_gate'] = payload.get('type')
        response['pending_payload'] = payload
        return response

    response['status'] = 'completed'
    return response
