"""Document Assessment — starting a workflow instance from an uploaded
document. docs/architecture/07-workflow-architecture.md §7.3's Document
Assessment template; the literal Milestone 1 deliverable
(docs/architecture/14-roadmap.md §14.3): "An officer can upload a document,
see extracted fields with confidence scores and citations."

Any authenticated officer may start an assessment — docs/architecture/
10-human-in-the-loop.md §10.2 scopes extraction confirmation to "Any
assigned Entrepreneurship Officer," not a privileged role.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, UploadFile

from services.api_gateway.auth import Principal, get_current_principal
from services.api_gateway.dependencies import get_workflow
from services.api_gateway.errors import to_http_exception
from services.api_gateway.serialization import serialize_workflow_result
from services.approval_service.approval_service import ResumableWorkflow
from shared.schemas.tooling import ToolError

router = APIRouter(prefix='/documents', tags=['documents'])

# Module-level singleton rather than a call inline in the signature default
# (ruff B008) — same dependency, just not re-constructed on every import.
_file_upload = File(...)


@router.post('/assessments')
async def start_assessment(
    file: UploadFile = _file_upload,
    principal: Principal = Depends(get_current_principal),
    workflow: ResumableWorkflow = Depends(get_workflow),
) -> dict:
    """Upload a document and start a Document Assessment workflow instance.
    The response reflects the workflow's real state after its first pass —
    normally paused at the confirm-extraction gate
    (docs/architecture/10-human-in-the-loop.md §10.5), not a placeholder.
    """

    document_id = str(uuid.uuid4())
    pdf_bytes = await file.read()

    initial_state = {
        'document_id': document_id,
        'pdf_bytes': pdf_bytes,
        'compliance_requirements': [],
        'extraction_record': None,
        'compliance_checklist': None,
        'validation_notes': [],
        'approval_decision': None,
        'stage_log': [],
    }
    config = {'configurable': {'thread_id': document_id}}

    try:
        result = await workflow.ainvoke(initial_state, config=config)
    except ToolError as exc:
        raise to_http_exception(exc) from exc

    return serialize_workflow_result(document_id, result)
