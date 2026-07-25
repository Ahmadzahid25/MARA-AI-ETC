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
    owning_department: str | None = None
    effective_from: date | None = None
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

    @classmethod
    def from_chunk(cls, chunk: RetrievedChunk) -> PolicyCitation:
        return cls(
            document_id=chunk.document_id,
            version=chunk.version,
            locator=chunk.locator,
            relevance=chunk.relevance,
            superseded_on=chunk.superseded_on,
        )

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

    def citable_refs(self) -> tuple[CitableRef, ...]:
        return tuple(chunk.to_citable_ref() for chunk in self.chunks)
