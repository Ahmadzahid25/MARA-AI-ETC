"""Deterministic citation verification — docs/architecture/06-tool-architecture.md
§6.1, closing Review Board Finding A2.

The control this implements
---------------------------
Schema validation confirms a citation-shaped string exists. It does not confirm
the thing cited was ever retrieved. An LLM emitting a plausible but fabricated
policy clause reference passes every schema check and reads to a reviewing
officer as *more* trustworthy than an omitted citation — which is why §6.1
requires the check be deterministic and sit outside the agent:

    "the Tool Runtime records the exact set of returned document/chunk/record
    IDs for that task. Before an agent's output reaches a human, every citation
    in its provenance block is checked against that recorded set; a citation
    referencing an ID that was never actually returned is rejected and flagged,
    not passed through on the strength of being well-formed."

So the ledger is written by *tools*, reporting what they actually returned, and
read by the verification step before an agent's output leaves its task. An agent
never writes to it. That asymmetry is the whole design: an agent cannot make a
citation valid by asserting it, only by having caused a tool to return it.

Scope of one ledger
-------------------
One ledger instance covers one agent's task, and is passed explicitly the way
``AuditSink`` already is elsewhere in this codebase rather than resolved from
ambient state. Per-task scoping is what §6.1 specifies, and it is also the
stricter reading: a citation is valid only if *this* task retrieved it, not if
some other concurrent task happened to. It is not designed to be shared across
processes or across agents.

Version pinning
---------------
``version`` participates in identity, so citing v4 of a policy when the tool
returned v3 is a rejection, not a match. That is deliberate and load-bearing for
docs/architecture/09-knowledge-architecture.md §9.4: an audit of a decision made
in March must see the policy text that existed in March, and a citation that
silently drifts to "whatever is current" defeats that.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class CitableRef(BaseModel):
    """One retrievable thing an agent may cite.

    Frozen and hashable so refs can be held in the ledger's set directly —
    identity is the whole of the model's contents, which is exactly the
    comparison §6.1's check needs.
    """

    model_config = ConfigDict(frozen=True)

    document_id: str = Field(min_length=1)
    version: str | None = Field(
        default=None,
        description='Document version, where the source is versioned '
        '(docs/architecture/09-knowledge-architecture.md §9.4). Participates '
        'in identity: citing a different version than was retrieved is a '
        'rejection, not a match.',
    )
    locator: str | None = Field(
        default=None,
        description='Where inside the document — a chunk ID, section '
        'reference, or page. None cites the document as a whole, which only '
        'verifies if a tool returned it that way.',
    )


class CitationVerificationResult(BaseModel):
    """Outcome of checking one agent output's citations against the ledger.

    Returns both sides rather than a bare bool because §6.1 requires a rejected
    citation be *flagged* — naming which citation failed, so an officer sees
    what the agent claimed and what was actually retrieved.
    """

    model_config = ConfigDict(frozen=True)

    verified: tuple[CitableRef, ...] = ()
    rejected: tuple[CitableRef, ...] = ()

    @property
    def ok(self) -> bool:
        return not self.rejected


class FabricatedCitationError(Exception):
    """An agent cited something no tool returned during this task.

    Not a ``ToolError``: this is not a tool failing, it is an agent's output
    failing verification. Raised by ``require_verified_citations`` at the point
    an output would otherwise reach a human.
    """

    def __init__(self, rejected: tuple[CitableRef, ...]) -> None:
        self.rejected = rejected
        detail = ', '.join(
            f'{ref.document_id}'
            + (f'@{ref.version}' if ref.version else '')
            + (f'#{ref.locator}' if ref.locator else '')
            for ref in rejected
        )
        super().__init__(
            f'{len(rejected)} citation(s) reference material no tool returned '
            f'during this task: {detail}'
        )


class ProvenanceLedger:
    """What tools actually returned during one agent task.

    Deliberately not a pydantic model: this is mutable per-task state with a
    narrow write surface, and the constraint worth enforcing is *who* may write
    (tools, via ``record_returned``) rather than immutability.
    """

    def __init__(self) -> None:
        self._returned: set[CitableRef] = set()
        self._by_tool: dict[str, set[CitableRef]] = {}

    def record_returned(self, tool_name: str, refs: tuple[CitableRef, ...]) -> None:
        """Record what ``tool_name`` returned. Called by the tool itself, on the
        way out, for the same reason tools log their own invocations
        (shared/schemas/tooling.py): the record must exist even if the agent's
        subsequent reasoning crashes.
        """

        self._returned.update(refs)
        self._by_tool.setdefault(tool_name, set()).update(refs)

    def verify(self, cited: tuple[CitableRef, ...]) -> CitationVerificationResult:
        """Check ``cited`` against what was actually returned.

        Fails closed: with an empty ledger every citation is rejected, because
        "no tool ran" and "the agent may cite freely" must never be the same
        state. An agent that genuinely has nothing to cite should emit no
        citations, which verifies trivially.
        """

        verified = tuple(ref for ref in cited if ref in self._returned)
        rejected = tuple(ref for ref in cited if ref not in self._returned)
        return CitationVerificationResult(verified=verified, rejected=rejected)

    def require_verified(self, cited: tuple[CitableRef, ...]) -> None:
        """Verify, and raise on any rejection.

        For the call sites where a fabricated citation must stop the output
        rather than annotate it — §6.1's "rejected and flagged, not passed
        through". Callers that need to surface partial results to an officer
        should call ``verify`` and render the rejections instead.
        """

        result = self.verify(cited)
        if not result.ok:
            raise FabricatedCitationError(result.rejected)

    def returned_by(self, tool_name: str) -> frozenset[CitableRef]:
        """What one tool returned — for audit reconstruction and for tests that
        need to assert a specific tool's contribution rather than the union."""

        return frozenset(self._by_tool.get(tool_name, frozenset()))

    @property
    def all_returned(self) -> frozenset[CitableRef]:
        return frozenset(self._returned)

    def __len__(self) -> int:
        return len(self._returned)
