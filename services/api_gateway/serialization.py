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
