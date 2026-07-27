"""Recommendation contract — docs/architecture/05-agent-architecture.md §5.8.

    Outputs: "Draft recommendation with explicit reasoning trail — this is
    a *draft for officer judgment*, never a final decision."
    Escalation rules: "Escalates (declines to recommend) if any upstream
    agent flagged a hard compliance violation, or if overall confidence is
    below threshold — presents the evidence and explicitly declines to
    suggest an outcome rather than guessing."
    Failure handling: "Missing upstream input results in 'recommendation
    withheld pending [X]', never a recommendation computed on a partial
    picture."

``decision`` is ``None`` exactly when ``withheld_reason`` is set — the
schema enforces that a withheld recommendation carries no decision value a
UI could mistake for a real one, the same invariant
``shared/schemas/risk.py``'s ``RiskRating`` applies to
``overall_score``/``qualitative_range``.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, model_validator

from shared.schemas.knowledge import PolicyCitation


class RecommendationDecision(str, Enum):
    APPROVE = 'approve'
    DECLINE = 'decline'
    APPROVE_WITH_CONDITIONS = 'approve_with_conditions'


class RecommendationOutput(BaseModel):
    """The Recommendation Agent's complete output — inert until an officer
    acts on it (§5.8: "output is inert until an officer acts on it").
    """

    document_id: str = Field(min_length=1)
    decision: RecommendationDecision | None = Field(
        default=None,
        description='None exactly when withheld_reason is set — a withheld '
        'recommendation has no decision, not a default one.',
    )
    reasoning_trail: str = Field(default='')
    conditions: list[str] = Field(
        default_factory=list,
        description='Only meaningful when decision is APPROVE_WITH_CONDITIONS.',
    )
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    precedent_citations: list[PolicyCitation] = Field(default_factory=list)
    withheld_reason: str | None = Field(
        default=None,
        description='Set when the agent declines to recommend at all — a '
        'hard compliance violation, missing upstream input, or '
        'below-threshold confidence. §5.8: "presents the evidence and '
        'explicitly declines to suggest an outcome rather than guessing."',
    )
    missing_inputs: list[str] = Field(default_factory=list)

    @model_validator(mode='after')
    def _decision_xor_withheld(self) -> 'RecommendationOutput':
        if self.decision is None and self.withheld_reason is None:
            raise ValueError(
                'RecommendationOutput must have either a decision or a '
                'withheld_reason — it cannot be silently empty'
            )
        if self.decision is not None and self.withheld_reason is not None:
            raise ValueError(
                'RecommendationOutput cannot carry both a decision and a '
                'withheld_reason — a withheld recommendation has no decision'
            )
        if (
            self.conditions
            and self.decision != RecommendationDecision.APPROVE_WITH_CONDITIONS
        ):
            raise ValueError(
                'conditions is only meaningful when decision is APPROVE_WITH_CONDITIONS'
            )
        return self

    def is_low_confidence(self, threshold: float = 0.8) -> bool:
        """§5.8: "below this, output is explicitly labeled 'low-confidence
        — manual assessment recommended' rather than suppressed" — a low-
        confidence recommendation still carries a ``decision`` (unlike the
        hard-violation case, which withholds one entirely); this is what
        the officer console checks to show that label."""
        return self.decision is not None and self.confidence < threshold
