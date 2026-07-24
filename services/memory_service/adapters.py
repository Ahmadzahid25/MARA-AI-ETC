"""Adapters from other components' typed records into ``CalibrationEvent``.
Mirrors ``services/audit_service/adapters.py``'s reasoning — kept separate
from the read/write API so new producers add a function here, not a new
branch inside ``write_calibration_event()``.
"""

from __future__ import annotations

from services.memory_service.calibration import CalibrationEvent
from shared.schemas.documents import DocumentExtractionRecord


def extraction_record_to_calibration_events(
    record: DocumentExtractionRecord,
    *,
    agent_name: str,
    workflow_id: str,
    corrected_field_names: set[str],
) -> list[CalibrationEvent]:
    """One event per extracted field — docs/architecture/10-human-in-the-loop.md
    §10.5: "an agent whose outputs are frequently corrected on a specific
    field type is a signal for prompt/tool improvement." Every field is
    recorded, not just the corrected ones — a low correction rate is only a
    meaningful signal relative to the full population of extractions, not
    just the subset that happened to get fixed.
    """

    return [
        CalibrationEvent(
            agent_name=agent_name,
            workflow_id=workflow_id,
            field_name=field.name,
            document_type=record.classification.document_type,
            stated_confidence=field.confidence,
            was_corrected=field.name in corrected_field_names,
        )
        for field in record.fields
    ]
