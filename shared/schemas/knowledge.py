"""Knowledge retrieval contract — docs/architecture/09-knowledge-architecture.md.

The shared shape between the RAG tool (tools/rag/), the agents that query it,
and `services/knowledge_service`'s Dify-backed implementation. §9.1 is explicit
that agents never talk to Dify directly: they call the service, "which is what
lets the underlying RAG engine be swapped later without touching agent code."
That swap is only actually cheap if the boundary is a typed contract rather than
Dify's own response shape leaking upward, which is what this module fixes.

Three architectural requirements are encoded here rather than left to the
implementation's discretion:

- **§9.3 metadata filtering.** Retrieval is filterable beyond similarity —
  "policy documents, currently effective, compliance-department-owned" — because
  similarity alone will happily surface a superseded policy version that is
  textually near-identical to the current one. `RetrievalFilters` makes the
  effective-date filter the default rather than an opt-in.
- **§9.4 version pinning.** A chunk carries the version it came from, and that
  version travels into the citation. An audit of a March decision must see March's
  policy text, not today's.
- **§9.5 "no confident match".** A retrieval below the relevance threshold is
  surfaced as an explicit signal, not as a weak match the agent might treat as
  support. The distinction is represented in the result type so an agent cannot
  miss it by only looking at whether `chunks` is empty.
- **§9.7 trust tiers and market-data freshness.** Content that has not passed
  the §9.6 Knowledge Owner approval lifecycle is retrievable only as an
  explicitly labeled low-trust tier, and cached market findings expire. Both are
  encoded as required fields rather than optional metadata — see `TrustTier`.
"""

from __future__ import annotations

from datetime import date
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from shared.provenance import CitableRef


class DocumentKind(StrEnum):
    """The corpora §9.1 scopes this service to."""

    POLICY = 'policy'
    SOP = 'sop'
    PRODUCT_TERMS = 'product_terms'
    PRECEDENT = 'precedent'
    MARKET_DATA = 'market_data'


class SensitivityClass(StrEnum):
    """§9.2: sensitivity is "a gate on the pipeline, not a label added after the
    fact" — it decides whether the self-hosted or cloud-eligible OCR/embedding
    path may be used at all (Phase 11)."""

    NON_SENSITIVE = 'non_sensitive'
    INTERNAL = 'internal'
    CONFIDENTIAL = 'confidential'


class TrustTier(StrEnum):
    """§9.7: whether a chunk has cleared Knowledge Owner approval.

    This exists because of a specific attack, not as general metadata. Review
    Board Finding C3 (review/03-data-and-security-review.md Red Team #7): the
    Market Agent writes findings gathered from the open internet into Knowledge
    Memory, and before v1.0 that content was exempt from the approval lifecycle
    that policy/SOP content had to pass. A single Market Agent run against a
    low-quality or adversarially-optimized source would then become silently
    trusted context for every future Risk and Recommendation Agent run in that
    sector, with no human having reviewed it.

    The fix §9.7 mandates is not "warn about it" — it is that unapproved content
    stays readable *only* by the agent that gathered it, provisionally, and is
    structurally unavailable to the agents whose output drives a lending
    decision. `tools/rag/rag_tool.py` enforces that in both directions.
    """

    APPROVED = 'approved'
    """Passed the §9.6 Draft -> PendingApproval -> Approved -> Active lifecycle.
    A Knowledge Owner signed off on this content."""

    PROVISIONAL = 'provisional'
    """Written into Knowledge Memory but not yet approved — §9.7's "low-trust
    tier". Also the tier assigned when a backend cannot establish which tier
    content belongs to: unknown provenance is the untrusted case, so the mapping
    fails closed rather than presuming approval."""


MARKET_DATA_FRESHNESS_DAYS = 90
"""§9.7's default freshness window for cached market data, in days.

"configurable per sector" in the spec — `RetrievalFilters.max_market_data_age_days`
is that override. The default lives here rather than as a magic number at the
enforcement site so that a sector-specific policy has one documented thing to
deviate from.
"""


class RetrievalFilters(BaseModel):
    """§9.3's metadata filters.

    ``effective_on`` defaults to None meaning "today" at query time rather than
    "unfiltered": the failure this prevents — a superseded clause retrieved
    because it is textually similar to the current one — is silent, produces a
    well-formed citation, and is exactly the kind of error an officer would have
    no way to spot from the output.
    """

    model_config = ConfigDict(frozen=True)

    document_kinds: frozenset[DocumentKind] | None = Field(
        default=None, description='None retrieves across every kind.'
    )
    owning_department: str | None = None
    effective_on: date | None = Field(
        default=None,
        description='Retrieve only versions in force on this date. None means '
        "the query's execution date — never 'any version'.",
    )
    include_superseded: bool = Field(
        default=False,
        description='Opt-in, for audit reconstruction of a past decision. '
        'Normal retrieval must not see superseded text.',
    )
    max_sensitivity: SensitivityClass | None = Field(
        default=None,
        description='Ceiling on what this caller may retrieve. None applies the '
        "backend's default for the caller's role.",
    )
    include_provisional: bool = Field(
        default=False,
        description='§9.7: opt in to the low-trust tier alongside approved '
        'content. Defaults off, and asking for it is a permission-checked act — '
        'only a profile with may_read_provisional_knowledge may set it, which '
        'today is the Market Agent alone. Setting it does not make provisional '
        'chunks approved; they arrive still labeled, and PolicyCitation carries '
        'the label into the agent output so an officer sees which findings rest '
        'on unreviewed material.',
    )
    max_market_data_age_days: int | None = Field(
        default=None,
        ge=1,
        description='§9.7 freshness override for the market-data cache, per '
        'sector. None applies MARKET_DATA_FRESHNESS_DAYS. Applies only to '
        'DocumentKind.MARKET_DATA — policy currency is governed by '
        'effective_on/superseded_on, which is a different question from cache '
        'staleness.',
    )


class RetrievalQuery(BaseModel):
    model_config = ConfigDict(frozen=True)

    query: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=50)
    filters: RetrievalFilters = Field(default_factory=RetrievalFilters)
    min_relevance: float = Field(
        default=0.6,
        ge=0.0,
        le=1.0,
        description='§9.5 threshold. Chunks below this are withheld and the '
        'result reports no confident match, rather than being returned for the '
        'agent to judge — the point of the threshold is that the agent is the '
        'component least able to tell a weak match from a good one.',
    )
    pinned_versions: dict[str, str] | None = Field(
        default=None,
        description='§9.4: document_id -> version, to reproduce exactly what an '
        'earlier workflow run retrieved.',
    )


class RetrievedChunk(BaseModel):
    """One chunk, carrying everything §9.5 requires a citation to preserve."""

    model_config = ConfigDict(frozen=True)

    document_id: str = Field(min_length=1)
    version: str = Field(
        min_length=1,
        description='Required, not optional: an unversioned citation cannot '
        'satisfy §9.4 reproducibility.',
    )
    locator: str = Field(
        min_length=1,
        description='Section reference, clause number, or page — whatever lets '
        'an officer find this text in the source document.',
    )
    text: str
    relevance: float = Field(ge=0.0, le=1.0)
    document_kind: DocumentKind
    sensitivity: SensitivityClass
    trust_tier: TrustTier = Field(
        description='§9.7. Required, with no default, deliberately: a default '
        'would be wrong in one direction or the other. APPROVED would let a '
        'backend that forgot to map the field launder unreviewed content into '
        'the decision path, and PROVISIONAL would silently downgrade the entire '
        'approved corpus. Making every construction site name the tier means '
        'neither can happen by omission — the backends that cannot determine a '
        'tier decide explicitly, and fail closed to PROVISIONAL.'
    )
    owning_department: str | None = None
    effective_from: date | None = None
    cached_at: date | None = Field(
        default=None,
        description='§9.7: when a market-data finding was written into Knowledge '
        'Memory, for the freshness window. Meaningful only for '
        'DocumentKind.MARKET_DATA; None on corpus content that does not expire.',
    )
    superseded_on: date | None = Field(
        default=None,
        description='Set once a later version takes effect. Present on a chunk '
        'only when superseded content was deliberately requested, or when a '
        'previously-cited version has since been superseded — see '
        'is_stale_as_of().',
    )

    def to_citable_ref(self) -> CitableRef:
        """The provenance identity for this chunk.

        Tools record this into the ledger when they return the chunk, and an
        agent's citation is verified against it — so a citation with the right
        document but the wrong version or clause is caught, not accepted for
        being roughly correct.
        """

        return CitableRef(
            document_id=self.document_id, version=self.version, locator=self.locator
        )

    def is_stale_as_of(self, as_of: date) -> bool:
        """Whether this chunk's version had been superseded by ``as_of``.

        Backs Milestone 2's acceptance criterion that "a superseded-policy
        staleness check correctly flags an outdated citation"
        (docs/architecture/14-roadmap.md §14.4). Kept as a query on the chunk
        rather than a boolean baked in at retrieval time because staleness is
        relative to when you ask: a citation that was current when a decision
        was made is not wrong, it is historical, and an audit view must be able
        to tell those apart.
        """

        return self.superseded_on is not None and self.superseded_on <= as_of

    def is_expired_as_of(self, as_of: date, *, max_age_days: int | None = None) -> bool:
        """Whether this cached market finding has passed its §9.7 freshness
        window by ``as_of``.

        Always False for anything other than ``MARKET_DATA``: §9.7's expiry is a
        property of the market-data cache specifically. Whether a *policy* is
        current is decided by ``effective_from``/``superseded_on``, and conflating
        the two would start expiring policy clauses for being old, which is
        exactly backwards — a long-unchanged policy is settled, not stale.

        A ``MARKET_DATA`` chunk with no ``cached_at`` is reported expired. Its age
        cannot be established, and §9.7's requirement is that stale market
        context is never "served silently"; an unknown age is not evidence of
        freshness, and the consequence of the strict reading is a redundant fresh
        search rather than a decision resting on unverifiable-vintage data.
        """

        if self.document_kind is not DocumentKind.MARKET_DATA:
            return False
        if self.cached_at is None:
            return True
        window = MARKET_DATA_FRESHNESS_DAYS if max_age_days is None else max_age_days
        return (as_of - self.cached_at).days > window


class PolicyCitation(BaseModel):
    """A citation into the knowledge corpus, as carried by an agent's output.

    Distinct from `shared.schemas.documents.Citation`, which points at a page of
    an *applicant's* submitted document and optionally a bounding box. A policy
    citation points at a clause of a versioned corpus document, and the version
    is required rather than optional: §9.4's reproducibility guarantee — an audit
    of a March decision sees March's policy text — is unenforceable against a
    citation that only names the document.
    """

    model_config = ConfigDict(frozen=True)

    document_id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    locator: str = Field(min_length=1, description='Clause, section, or page.')
    relevance: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description='The retrieval score behind this citation, kept so an '
        'officer reviewing a finding can see how strong its support was.',
    )
    superseded_on: date | None = None
    trust_tier: TrustTier = Field(
        description='§9.7. Required for the same reason as on RetrievedChunk, '
        'and carried this far for a distinct one: the tier has to survive into '
        'the agent output an officer actually reads. A citation that reaches the '
        'Review & Approval Console indistinguishable from an approved-corpus '
        'citation would defeat the control at the last step — the officer would '
        'be weighing unreviewed internet-sourced material believing a Knowledge '
        'Owner had signed off on it.'
    )

    @classmethod
    def from_chunk(cls, chunk: RetrievedChunk) -> PolicyCitation:
        return cls(
            document_id=chunk.document_id,
            version=chunk.version,
            locator=chunk.locator,
            relevance=chunk.relevance,
            superseded_on=chunk.superseded_on,
            trust_tier=chunk.trust_tier,
        )

    def is_provisional(self) -> bool:
        """Whether this citation rests on content no Knowledge Owner approved.

        A named query rather than an equality check at each call site, so that
        UI and report code asks the question one way — and so the officer-facing
        wording in apps/officer-workspace has one thing to key off.
        """

        return self.trust_tier is TrustTier.PROVISIONAL

    def to_citable_ref(self) -> CitableRef:
        """The provenance identity this citation must match in the ledger."""

        return CitableRef(
            document_id=self.document_id, version=self.version, locator=self.locator
        )

    def is_stale_as_of(self, as_of: date) -> bool:
        """Whether the version cited had been superseded by ``as_of`` —
        Milestone 2's staleness acceptance criterion
        (docs/architecture/14-roadmap.md §14.4)."""

        return self.superseded_on is not None and self.superseded_on <= as_of


class RetrievalResult(BaseModel):
    """§9.5's two distinct outcomes, kept distinguishable.

    ``no_confident_match`` is a separate field rather than something a caller
    infers from an empty ``chunks``, because "the corpus has nothing relevant"
    and "the corpus had candidates but none passed the threshold" call for
    different agent behavior — and an agent checking only for emptiness would
    treat them identically.
    """

    model_config = ConfigDict(frozen=True)

    chunks: tuple[RetrievedChunk, ...] = ()
    no_confident_match: bool = False
    withheld_below_threshold: int = Field(
        default=0,
        ge=0,
        description='How many candidates were dropped for low relevance. '
        'Surfaced so the officer-facing "no confident match" explanation can '
        'distinguish an empty corpus from a weak one.',
    )
    withheld_unverified: int = Field(
        default=0,
        ge=0,
        description='§9.7: how many chunks were dropped for being in the '
        'low-trust tier when the caller may not read it. Counted rather than '
        'dropped silently so that "the corpus has nothing on this" stays '
        'distinguishable from "what exists has not been approved yet" — those '
        'call for opposite responses, one to report a gap and one to chase an '
        'approval.',
    )
    withheld_expired: int = Field(
        default=0,
        ge=0,
        description='§9.7: how many market-data chunks were dropped for being '
        'past their freshness window. This is the signal the spec requires — '
        '"a fresh search is triggered instead of serving stale market context '
        'silently" — so a non-zero value here is what tells the Market Agent to '
        'go and search rather than to report an empty cache.',
    )

    def citable_refs(self) -> tuple[CitableRef, ...]:
        return tuple(chunk.to_citable_ref() for chunk in self.chunks)

    def needs_fresh_search(self) -> bool:
        """§9.7: whether the cache came back empty *because* it had aged out.

        Distinct from ``no_confident_match``, which means candidates existed and
        scored too low. Here the content was relevant enough but too old to
        serve, and the correct response is a live search rather than reporting
        that the corpus is silent on the question.
        """

        return self.withheld_expired > 0 and not self.chunks
