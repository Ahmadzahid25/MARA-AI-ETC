"""Publishing Service — docs/architecture/05-agent-architecture.md §5.11.1.

    Responsibilities: assemble a committee-ready document and, on request,
    a presentation deck from approved upstream outputs
    Inputs: "Officer-approved agent outputs only (never drafts pending
    review)"
    Permissions: "Read-only on approved data; cannot include any agent
    output that hasn't passed its required human approval gate"
    Escalation rules: "If required approved inputs are missing ... or
    report content doesn't map cleanly to slide structure, refuses/flags
    rather than drafting a placeholder"

Reclassified as a service, not an agent (§5.14's test): assembling
already-decided content into a document is deterministic transformation,
not ambiguous judgment — no LLM call, no confidence threshold here (the
"optional narrative smoothing" §5.11.1 mentions is not implemented in this
slice; every section is rendered directly from the structured inputs).

This module cannot itself verify "did this pass its approval gate" — that
state lives in the calling workflow (`workflows/loan_assessment`), which
only reaches the publish step after its own approval-gate nodes have
resolved. What this module *can* and does check: a recommendation with no
``decision`` (withheld) or a risk rating that isn't ``COMPLETE`` are
structurally not publishable, regardless of what gate state the caller
believes it's in — refusing rather than rendering a placeholder for either.
"""

from __future__ import annotations

from services.publishing_service.rendering import (
    CommitteeReportInputs,
    render_docx,
    render_pptx,
)
from shared.schemas.risk import RiskStatus
from shared.schemas.tooling import AuditSink, ToolInvocationLog, log_tool_invocation


class MissingApprovedInputError(Exception):
    """§5.11.1's escalation rule: a required approved input is missing or
    structurally unpublishable (a withheld recommendation, an incomplete/
    escalated risk rating) — refused, never rendered as a placeholder."""


class RenderingError(Exception):
    """§5.11.1's failure handling: "Rendering failures surface the
    specific error to the officer, with underlying data preserved for
    retry" — the caller still has ``inputs``; nothing is consumed or lost
    on a failed render."""


class PublishedArtifacts:
    __slots__ = ('docx_bytes', 'pptx_bytes')

    def __init__(self, docx_bytes: bytes, pptx_bytes: bytes | None) -> None:
        self.docx_bytes = docx_bytes
        self.pptx_bytes = pptx_bytes


def _validate_publishable(inputs: CommitteeReportInputs) -> None:
    if inputs.recommendation.decision is None:
        raise MissingApprovedInputError(
            'Recommendation has no decision (withheld) — cannot publish '
            'committee materials without an actual recommendation to report'
        )
    if inputs.risk_rating.status != RiskStatus.COMPLETE:
        raise MissingApprovedInputError(
            f'Risk rating is {inputs.risk_rating.status.value}, not '
            'complete — cannot publish an incomplete or escalated risk '
            'picture as though it were a finished assessment'
        )


async def publish_committee_materials(
    inputs: CommitteeReportInputs,
    *,
    generate_deck: bool = True,
    workflow_id: str | None = None,
    audit_sink: AuditSink | None = None,
) -> PublishedArtifacts:
    """Render the committee report (.docx) and, unless ``generate_deck`` is
    False, the presentation deck (.pptx) from ``inputs``. Raises
    ``MissingApprovedInputError`` if ``inputs`` is structurally
    unpublishable, or ``RenderingError`` if rendering itself fails.
    """

    _validate_publishable(inputs)

    try:
        docx_bytes = render_docx(inputs)
    except Exception as exc:
        _log(inputs.document_id, workflow_id, 'external_error', audit_sink)
        raise RenderingError(f'.docx rendering failed: {exc}') from exc

    pptx_bytes: bytes | None = None
    if generate_deck:
        try:
            pptx_bytes = render_pptx(inputs)
        except Exception as exc:
            _log(inputs.document_id, workflow_id, 'external_error', audit_sink)
            raise RenderingError(f'.pptx rendering failed: {exc}') from exc

    _log(inputs.document_id, workflow_id, 'success', audit_sink)
    return PublishedArtifacts(docx_bytes=docx_bytes, pptx_bytes=pptx_bytes)


def _log(
    document_id: str, workflow_id: str | None, outcome: str, audit_sink: AuditSink | None
) -> None:
    log_tool_invocation(
        ToolInvocationLog(
            tool_name='publishing_service',
            caller_agent='publishing_service',
            workflow_id=workflow_id,
            input_hash=document_id,
            output_hash=None,
            latency_ms=0.0,
            outcome=outcome,  # type: ignore[arg-type]
        ),
        sink=audit_sink,
    )
