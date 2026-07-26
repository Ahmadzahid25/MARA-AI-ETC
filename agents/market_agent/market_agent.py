"""Market Agent — docs/architecture/05-agent-architecture.md §5.7.

    Responsibilities: gather external market context (industry trends,
    comparable business performance, sector risk) relevant to the
    applicant's business
    Inputs: applicant business sector/description, geographic market —
    generalized, never the applicant's identifying details (§5.7.1)
    Confidence threshold: 0.7 source-credibility threshold per claim
    Model tier: Sonnet-class (synthesis tier)

The only agent with outbound external-network tool access
(tools/search/search_tool.py) — every other agent's tools are internal.
Sanitization is enforced *inside* the search tool itself (§6.6), not by
this agent's discipline, but this agent still receives already-generalized
``sector``/``region`` inputs as a second, upstream layer of defense (§5.7.1:
"restricting external egress to this one agent's tool prevents other
agents from leaking data externally, but says nothing about what this
agent's own queries contain").

Per §5.7's failure handling, a live-search failure/timeout degrades to
Knowledge Base-only results with an explicit note — implemented for real
here, since it's pure control flow, not a vendor-choice gap. Per the
escalation rule, an empty claim set is reported as "insufficient external
data" via ``MarketBrief.note``, never papered over with an unsupported
narrative.

Cached-market-data lookup goes through the real Milestone-2
``services.knowledge_service.contract.KnowledgeBackend`` /
``tools.rag.rag_tool.rag_query`` boundary, the same one
``agents/compliance_agent/policy_lookup.py`` and ``agents/finance_agent``
use. §9.7's low-trust-tier provisional visibility (a cached market finding
readable before Knowledge Owner approval) has no equivalent in
``shared/schemas/knowledge.py``'s ``RetrievalFilters`` yet — that filter
dimension doesn't exist upstream — so this agent currently only ever reads
already-approved market data, same as any other corpus query. Writing a
freshly-gathered brief back into Knowledge Memory has the same gap in the
other direction: ``KnowledgeBackend`` is read-only (one method,
``retrieve()``), so there is no ingestion path to bind ``cache_writer`` to
yet. Both are real, open follow-ups, not silently dropped requirements —
see this package's README.
"""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

from services.knowledge_service.contract import (
    KnowledgeBackend,
    KnowledgeBackendNotConfiguredError,
)
from shared.agent_profiles import confidence_threshold_for, profile_for
from shared.llm.client import TieredLLMClient
from shared.llm.model_tiers import AgentName
from shared.provenance import ProvenanceLedger
from shared.schemas import ToolExternalServiceError, ToolTimeoutError
from shared.schemas.knowledge import DocumentKind, RetrievalFilters, RetrievalQuery
from shared.schemas.market import MarketBrief, MarketClaim
from tools.rag.rag_tool import rag_query
from tools.search.search_tool import SearchEngine, run_search

PROFILE = profile_for(AgentName.MARKET.value)
# Sourced from the profile registry — see shared/agent_profiles/profiles.py.
SOURCE_CREDIBILITY_THRESHOLD = confidence_threshold_for(AgentName.MARKET.value)
LIVE_SEARCH_UNAVAILABLE_NOTE = 'Live search was unavailable; results are Knowledge Base-only.'
INSUFFICIENT_DATA_NOTE = 'Insufficient external data — no credible sources found.'


class MarketCredibilityParsingError(Exception):
    """The credibility-assessment step (LLM or injected assessor) returned
    output that doesn't match the required shape — surfaced, never
    silently defaulted to a guessed score."""


# (source_url, snippet) -> credibility 0.0-1.0. Default calls the LLM;
# tests inject a deterministic fake.
CredibilityAssessor = Callable[[str, str], Awaitable[float]]

# Writes an approved-for-caching MarketBrief into Knowledge Memory (§5.7,
# §9.7's market-data lifecycle carve-out). No default, and no real binding
# exists yet — see this module's docstring: KnowledgeBackend has no write/
# ingest method to bind one to. Kept as an injectable seam so a real binder
# can be added later without changing gather_market_context()'s call site.
CacheWriter = Callable[[MarketBrief], Awaitable[None]]


def _build_query_text(sector: str, region: str) -> str:
    # Deterministic, not LLM-formulated — §5.7.1's "generalized, never the
    # applicant's identifying details" is a property of what the *caller*
    # passes as sector/region, not something an LLM call could be trusted
    # to enforce after the fact.
    return f'{sector} sector market outlook {region}'


def _build_credibility_prompt(source_url: str, snippet: str) -> str:
    return (
        f'Source: {source_url}\nContent: {snippet}\n\n'
        f"Assess this source's credibility as evidence for a market/sector "
        f'analysis. Respond with a JSON object with exactly this key: '
        f'"credibility" (float 0.0-1.0). Respond with the JSON object only, '
        f'no other text.'
    )


def _parse_credibility(raw_content: str) -> float:
    try:
        raw = json.loads(raw_content)
        credibility = float(raw['credibility'])
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        raise MarketCredibilityParsingError(
            f'Malformed credibility output {raw_content!r}: {exc}'
        ) from exc
    if not 0.0 <= credibility <= 1.0:
        raise MarketCredibilityParsingError(
            f'credibility {credibility} out of range [0.0, 1.0]'
        )
    return credibility


class MarketAgent:
    """Configuration of the (not-yet-built) Agent Runtime for market
    context gathering — role/goal/tools/confidence-threshold, per
    docs/architecture/05-agent-architecture.md §5.1."""

    profile = PROFILE
    confidence_threshold: float = SOURCE_CREDIBILITY_THRESHOLD
    allowed_tools = PROFILE.allowed_tools

    def __init__(
        self,
        llm_client: TieredLLMClient | None = None,
        credibility_assessor: CredibilityAssessor | None = None,
        search_engine: SearchEngine | None = None,
        backend: KnowledgeBackend | None = None,
        cache_writer: CacheWriter | None = None,
        allowed_domains: frozenset[str] = frozenset(),
    ) -> None:
        self._llm_client = llm_client or TieredLLMClient()
        self._credibility_assessor = credibility_assessor
        self._search_engine = search_engine
        self._backend = backend
        self._cache_writer = cache_writer
        self._allowed_domains = allowed_domains

    async def gather_market_context(
        self,
        sector: str,
        region: str,
        *,
        workflow_id: str | None = None,
        top_k_cache: int = 5,
        ledger: ProvenanceLedger | None = None,
        audit_sink=None,
    ) -> MarketBrief:
        query_text = _build_query_text(sector, region)
        live_search_available = True
        claims: list[MarketClaim] = []

        try:
            search_results = run_search(
                query_text,
                caller_agent=AgentName.MARKET.value,
                allowed_domains=self._allowed_domains,
                engine=self._search_engine,
                workflow_id=workflow_id,
                audit_sink=audit_sink,
            )
        except (ToolTimeoutError, ToolExternalServiceError):
            live_search_available = False
            search_results = []

        for result in search_results:
            score = await self._assess_credibility(result.url, result.snippet)
            claims.append(
                MarketClaim(
                    claim=result.snippet,
                    source_url=result.url,
                    retrieved_at=result.retrieved_at,
                    credibility_score=score,
                )
            )

        # Unlike Compliance's policy lookup, an unconfigured backend here
        # doesn't create a dishonest "confidently searched and found
        # nothing" finding — cached market data is supplementary enrichment
        # on top of live search (this agent's primary source), not the sole
        # basis for a claim. Treated the same as "nothing cached yet."
        try:
            cached_result = await rag_query(
                RetrievalQuery(
                    query=query_text,
                    top_k=top_k_cache,
                    filters=RetrievalFilters(
                        document_kinds=frozenset({DocumentKind.MARKET_DATA})
                    ),
                ),
                caller_agent=AgentName.MARKET.value,
                workflow_id=workflow_id,
                backend=self._backend,
                ledger=ledger,
                audit_sink=audit_sink,
            )
        except KnowledgeBackendNotConfiguredError:
            cached_result = None

        if cached_result is not None and not cached_result.no_confident_match:
            for chunk in cached_result.chunks:
                source_ref = f'knowledge://{chunk.document_id}/v{chunk.version}'
                score = await self._assess_credibility(source_ref, chunk.text)
                claims.append(
                    MarketClaim(
                        claim=chunk.text,
                        source_url=source_ref,
                        retrieved_at=datetime.now(UTC),
                        credibility_score=score,
                    )
                )

        notes = []
        if not live_search_available:
            notes.append(LIVE_SEARCH_UNAVAILABLE_NOTE)
        if not claims:
            notes.append(INSUFFICIENT_DATA_NOTE)

        brief = MarketBrief(
            sector=sector,
            region=region,
            claims=claims,
            live_search_available=live_search_available,
            note=' '.join(notes),
        )

        if self._cache_writer is not None and claims:
            await self._cache_writer(brief)

        return brief

    async def _assess_credibility(self, source_url: str, snippet: str) -> float:
        if self._credibility_assessor is not None:
            return await self._credibility_assessor(source_url, snippet)
        return await self._default_credibility_assessor(source_url, snippet)

    async def _default_credibility_assessor(
        self, source_url: str, snippet: str
    ) -> float:
        prompt = _build_credibility_prompt(source_url, snippet)
        response = await self._llm_client.complete_for_agent(
            AgentName.MARKET, [{'role': 'user', 'content': prompt}]
        )
        content = response.choices[0].message.content
        if content is None:
            raise MarketCredibilityParsingError('Model returned no content')
        return _parse_credibility(content)
