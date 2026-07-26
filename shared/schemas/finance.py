"""Financial analysis contract — docs/architecture/05-agent-architecture.md
§5.5:

    Outputs: "Financial analysis report with every figure traced to source
    extraction and every derived number traced to a specific calculation
    tool call."

Every ``FinancialFigure`` is either ``EXTRACTED`` (traced to a Document
Agent field + its citation) or ``CALCULATED`` (traced to a specific
formula ID + version from tools/calculations) — there is no third kind,
which is what makes "every figure traced" a schema-enforced invariant
rather than a convention the Finance Agent's prompt is trusted to follow.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, model_validator

from shared.schemas.documents import Citation
from shared.schemas.knowledge import PolicyCitation


class FigureProvenance(str, Enum):
    EXTRACTED = 'extracted'
    CALCULATED = 'calculated'


class FinancialFigure(BaseModel):
    name: str = Field(min_length=1)
    value: float
    provenance: FigureProvenance
    source_citation: Citation | None = Field(
        default=None, description='Required, and only meaningful, when EXTRACTED.'
    )
    formula_id: str | None = Field(
        default=None, description='Required, and only meaningful, when CALCULATED.'
    )
    formula_version: str | None = None

    @model_validator(mode='after')
    def _provenance_carries_its_required_trace(self) -> 'FinancialFigure':
        if self.provenance == FigureProvenance.EXTRACTED:
            if self.source_citation is None:
                raise ValueError(
                    f'figure {self.name!r} is EXTRACTED but has no source_citation'
                )
            if self.formula_id is not None or self.formula_version is not None:
                raise ValueError(
                    f'figure {self.name!r} is EXTRACTED but carries a formula_id '
                    '— it can only have one provenance kind'
                )
        else:
            if self.formula_id is None or self.formula_version is None:
                raise ValueError(
                    f'figure {self.name!r} is CALCULATED but is missing '
                    'formula_id/formula_version'
                )
            if self.source_citation is not None:
                raise ValueError(
                    f'figure {self.name!r} is CALCULATED but carries a '
                    'source_citation — it can only have one provenance kind'
                )
        return self


class FinancialAnalysis(BaseModel):
    """The Finance Agent's complete output for one document/application —
    written to Shared Memory for Risk/Recommendation agents to consume."""

    document_id: str = Field(min_length=1)
    figures: list[FinancialFigure] = Field(default_factory=list)
    assessment: str = Field(
        default='', description='Qualitative repayment-capacity narrative.'
    )
    assessment_confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    product_term_citations: list[PolicyCitation] = Field(
        default_factory=list,
        description='Corpus citations (product/grant terms), not applicant-'
        'document citations — PolicyCitation, not Citation, since these '
        'point at a versioned knowledge-corpus clause (shared/schemas/'
        "knowledge.py), not a page of the applicant's own submission.",
    )

    def is_low_confidence(self, threshold: float = 0.85) -> bool:
        """§5.5: "0.85 for qualitative judgments" — the arithmetic itself
        has no confidence score to miscalibrate (deterministic), only the
        narrative assessment does."""
        return self.assessment_confidence < threshold
