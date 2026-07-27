"""Risk rating contract — docs/architecture/05-agent-architecture.md §5.6.

Outputs: "Risk rating with component breakdown (financial, compliance,
market risk) and citations to each contributing agent's output."
Failure handling: "If any required upstream agent output is missing,
the risk rating is marked 'incomplete — pending [X]' rather than
computed on a partial picture."
Confidence threshold: "0.8; below this the rating is presented as a
range/qualitative flag rather than a single score."
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from shared.schemas.knowledge import PolicyCitation


class RiskStatus(str, Enum):
    COMPLETE = 'complete'
    INCOMPLETE = 'incomplete'
    ESCALATED = 'escalated'


class RiskRating(BaseModel):
    """The Risk Agent's complete output for one document/application.
    Exactly one of ``overall_score``/``qualitative_range`` is populated
    when ``status == COMPLETE`` (§5.6: a single score above the confidence
    threshold, a range/flag below it) — neither is populated for
    ``INCOMPLETE`` or ``ESCALATED``, since both statuses mean "no rating
    was computed," not "a rating exists but is presented differently."
    """

    document_id: str = Field(min_length=1)
    status: RiskStatus
    component_scores: dict[str, float] = Field(
        default_factory=dict,
        description='financial/compliance/market -> 0.0 (lowest risk) to '
        '1.0 (highest risk). Empty for INCOMPLETE.',
    )
    overall_score: float | None = Field(default=None, ge=0.0, le=1.0)
    qualitative_range: str | None = None
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    missing_inputs: list[str] = Field(default_factory=list)
    escalation_reason: str | None = None
    citations: list[PolicyCitation] = Field(
        default_factory=list,
        description='Precedent/policy corpus citations (PolicyCitation, '
        'versioned knowledge-corpus clauses), not applicant-document '
        'citations.',
    )
