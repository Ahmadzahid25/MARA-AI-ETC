"""Document extraction contract — docs/architecture/06-tool-architecture.md
§6.1 (every tool output carries a mandatory ``confidence`` field and a
``source`` provenance field) and docs/architecture/10-human-in-the-loop.md
§10.4 (an approval request must show the output, full citations, and the
confidence score together, never a bare claim).

This is the shared contract between the Document Agent (agents/document_agent/,
not yet built) and the Review & Approval Console
(apps/officer-workspace/, built independently against this same module per
apps/officer-workspace/AGENTS.md) — both sides consume this shape rather than
each inventing their own guess at it.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class ExtractionSource(str, Enum):
    """Which tool actually produced a field's value. docs/architecture/
    06-tool-architecture.md §6.2's PDF-parse row: "native text-layer
    extraction before falling back to OCR" — a field's provenance must say
    which path was used, since the two have materially different reliability
    profiles.
    """

    PDF_TEXT_LAYER = 'pdf_text_layer'
    OCR = 'ocr'


class BoundingBox(BaseModel):
    """Pixel/point coordinates of the region a field's value was read from,
    on a specific page. Page numbers are 1-indexed to match how an officer
    would refer to a page when verifying a citation against the source
    document.
    """

    page: int = Field(ge=1)
    x: float = Field(ge=0)
    y: float = Field(ge=0)
    width: float = Field(gt=0)
    height: float = Field(gt=0)


class Citation(BaseModel):
    """Provenance for one claim: which document, which page, and — where the
    extraction path produced one — the bounding box an officer can use to
    visually verify the claim against the source (docs/architecture/
    10-human-in-the-loop.md §10.4's "one-click access to the underlying
    source document").
    """

    document_id: str = Field(min_length=1)
    page: int = Field(ge=1)
    bounding_box: BoundingBox | None = Field(
        default=None,
        description='None when the source path does not produce region '
        'coordinates (e.g. a value read from PDF metadata rather than a '
        'visible text region).',
    )


class ExtractedField(BaseModel):
    """One extracted value with its confidence and provenance. docs/
    architecture/05-agent-architecture.md §5.3: Document Agent's confidence
    threshold is 0.85 per field — this schema doesn't enforce that threshold
    itself (that's the agent's escalation policy, not a schema constraint),
    it only enforces that confidence is a well-formed probability.
    """

    name: str = Field(min_length=1)
    value: str
    confidence: float = Field(ge=0.0, le=1.0)
    source: ExtractionSource
    citation: Citation


class DocumentClassification(BaseModel):
    """Document type label + confidence, per docs/architecture/
    06-tool-architecture.md §6.2's document-classification tool row. The
    type taxonomy itself (identity document, bank statement, business
    registration, ...) is intentionally left as a free-form string rather
    than a closed enum here — MARA's actual document taxonomy needs to be
    confirmed with MARA subject-matter input before it's hard-coded into the
    schema; hard-coding a guessed taxonomy now would be more expensive to
    unwind later than accepting a string today.
    """

    document_type: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)


class DocumentExtractionRecord(BaseModel):
    """The Document Agent's complete output for one document — what gets
    written to Shared Memory (docs/architecture/08-memory-architecture.md
    §8.2) for downstream Finance/Compliance agents, and what the Review &
    Approval Console renders for the officer to confirm/correct.
    """

    document_id: str = Field(min_length=1)
    classification: DocumentClassification
    fields: list[ExtractedField] = Field(default_factory=list)

    def low_confidence_fields(self, threshold: float = 0.85) -> list[ExtractedField]:
        """Fields below the Document Agent's escalation threshold (0.85 by
        default, docs/architecture/05-agent-architecture.md §5.3) — the set
        that must be confirmed by an officer before any downstream agent may
        use this record (§5.3: "blocks downstream Finance Agent calculations
        that depend on it")."""
        return [f for f in self.fields if f.confidence < threshold]
