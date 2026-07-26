"""Market context contract — docs/architecture/05-agent-architecture.md
§5.7:

    Outputs: "Market context brief with every claim cited to a specific
    external source and retrieval date."
    Confidence threshold: "0.7 source-credibility threshold per claim;
    lower-credibility sources are labeled, not excluded silently."

Every ``MarketClaim`` carries its source and retrieval date directly on the
model — there is no separate "claims" text field a caller could populate
without a citation, which is what makes "every claim cited" a schema
invariant rather than a prompt convention.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class MarketClaim(BaseModel):
    claim: str = Field(min_length=1)
    source_url: str = Field(min_length=1)
    retrieved_at: datetime
    credibility_score: float = Field(ge=0.0, le=1.0)

    def is_low_credibility(self, threshold: float = 0.7) -> bool:
        """§5.7: below-threshold sources are *labeled*, not silently
        excluded — this is the label, computed on demand rather than
        stored, so a later threshold change doesn't require rewriting
        already-persisted claims."""
        return self.credibility_score < threshold


class MarketBrief(BaseModel):
    """The Market Agent's complete output for one sector/region query."""

    sector: str = Field(min_length=1)
    region: str = Field(min_length=1)
    claims: list[MarketClaim] = Field(default_factory=list)
    live_search_available: bool = Field(
        default=True,
        description='§5.7 failure handling: False when the search API '
        'failed/timed out and this brief degraded to Knowledge Base-only '
        'results.',
    )
    note: str = Field(
        default='',
        description='Explicit degradation/insufficiency note — e.g. "live '
        'search was unavailable" or "insufficient external data" (§5.7\'s '
        'escalation rule) — never silently absent when one applies.',
    )
