"""Dify-backed implementation of the KnowledgeBackend Protocol.

docs/architecture/09-knowledge-architecture.md §9.1:

    "Dify sits behind this interface, and nothing above it knows that.
     Agents call the service, not Dify, which is what lets the
     underlying RAG engine be swapped later without touching agent code."

This module is the **only** place Dify's HTTP API surface is imported or
called. All callers above (RAG tool, Compliance Agent) depend only on
``KnowledgeBackend`` from ``services/knowledge_service/contract.py``.

Invariants that must be preserved:
- Dify is **internal-only**: it has no outbound internet egress.
  docs/architecture/11-security-architecture.md §11.7 — the Market
  Agent's search tool is the ONLY component permitted outbound internet
  access. This adapter must never be configured to call any external URL.
- A missing / unreachable Dify must raise, not return empty results.
  See ``UnconfiguredBackend`` in contract.py for the rationale — "no
  corpus was reached" must be distinguishable from "the corpus had
  nothing". ``DifyAdapter`` preserves this by letting httpx connection
  errors propagate rather than catching and returning empty.
- Dify runs on ``postgres-dify``, NEVER ``postgres-primary`` (ACCB C-5).
  This adapter talks to Dify's HTTP API, not its database directly —
  so the separation is maintained as long as the Dify API URL points at
  the correct container (``http://dify-api:5001`` inside the network,
  ``http://localhost:5001`` for local dev).

Configuration: add to configs/dev/settings.toml or set environment vars:

    MARA_DIFY__API_URL=http://localhost:5001/v1
    MARA_DIFY__API_KEY=<your-dify-dataset-api-key>
    MARA_DIFY__DATASET_ID=<your-dify-dataset-id>

The dataset ID and API key are obtained from the Dify admin UI after
the knowledge base is created.  See infrastructure/compose/docker-compose.dify.yml
for how Dify is deployed; infrastructure/AGENTS.md for wiring guidance.
"""

from __future__ import annotations

import logging
from datetime import date, timezone
from typing import Any

import httpx

from shared.schemas.knowledge import (
    DocumentKind,
    RetrievalQuery,
    RetrievalResult,
    RetrievedChunk,
    SensitivityClass,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Metadata field names as stored in Dify document metadata.
# These must match what the ingestion pipeline writes when uploading docs.
# ---------------------------------------------------------------------------
_META_DOCUMENT_ID = 'mara_document_id'
_META_VERSION = 'mara_version'
_META_LOCATOR = 'mara_locator'
_META_DOCUMENT_KIND = 'mara_document_kind'
_META_SENSITIVITY = 'mara_sensitivity'
_META_OWNING_DEPARTMENT = 'mara_owning_department'
_META_EFFECTIVE_FROM = 'mara_effective_from'   # ISO date string, YYYY-MM-DD
_META_SUPERSEDED_ON = 'mara_superseded_on'     # ISO date string or absent


class DifyAdapter:
    """Retrieve chunks from Dify's dataset retrieval API.

    Implements the ``KnowledgeBackend`` Protocol so it can be used
    anywhere a ``KnowledgeBackend`` is expected without a common base
    class.

    Args:
        api_url: Base URL for Dify's API, e.g. ``http://dify-api:5001/v1``.
            Must be an internal URL — never an external / internet address.
        api_key: Dataset API key obtained from Dify admin console.
        dataset_id: The Dify dataset (knowledge base) to query.
        http_client: Optional pre-constructed ``httpx.AsyncClient`` (for
            testing with a mock transport).  When None, a client is created
            from ``api_url`` with a 30-second timeout.
    """

    def __init__(
        self,
        api_url: str,
        api_key: str,
        dataset_id: str,
        *,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._dataset_id = dataset_id
        self._client = http_client or httpx.AsyncClient(
            base_url=api_url.rstrip('/'),
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
            },
            timeout=30.0,
        )

    async def retrieve(self, query: RetrievalQuery) -> RetrievalResult:
        """Call Dify's ``/datasets/{dataset_id}/retrieve`` endpoint.

        Applies ``query.filters`` as metadata conditions where Dify's API
        supports them.  ``query.min_relevance`` is enforced client-side
        (post-retrieval) rather than server-side, because Dify exposes a
        ``score_threshold`` parameter we can use — but §9.5 requires that
        withheld chunks are *counted* and reported, so we fetch
        ``query.top_k * 3`` candidates and apply the threshold ourselves.
        """

        payload = self._build_payload(query)
        logger.debug(
            'dify.retrieve dataset=%s top_k=%d query_len=%d',
            self._dataset_id,
            query.top_k,
            len(query.query),
        )

        response = await self._client.post(
            f'/datasets/{self._dataset_id}/retrieve',
            json=payload,
        )
        response.raise_for_status()
        data: dict[str, Any] = response.json()

        return self._parse_response(data, query)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_payload(self, query: RetrievalQuery) -> dict[str, Any]:
        """Translate a ``RetrievalQuery`` into Dify's request body."""

        # Fetch more candidates than needed so we can apply the relevance
        # threshold ourselves and accurately report withheld_below_threshold.
        fetch_k = min(query.top_k * 3, 50)

        payload: dict[str, Any] = {
            'query': query.query,
            'retrieval_model': {
                'search_method': 'semantic_search',
                'top_k': fetch_k,
                'score_threshold': 0.0,        # we apply threshold ourselves
                'score_threshold_enabled': False,
                'reranking_enable': False,
            },
        }

        # Metadata filters — Dify supports them as key-value conditions in
        # the retrieval_model.  We add them when they narrow the query.
        metadata_conditions: list[dict[str, Any]] = []

        filters = query.filters
        if not filters.include_superseded:
            # Exclude superseded documents: only retrieve those where
            # mara_superseded_on is absent (not yet superseded).
            metadata_conditions.append({
                'key': _META_SUPERSEDED_ON,
                'comparator': 'not exists',
            })

        if filters.document_kinds:
            kind_values = [k.value for k in filters.document_kinds]
            metadata_conditions.append({
                'key': _META_DOCUMENT_KIND,
                'comparator': 'in',
                'value': kind_values,
            })

        if filters.owning_department:
            metadata_conditions.append({
                'key': _META_OWNING_DEPARTMENT,
                'comparator': '=',
                'value': filters.owning_department,
            })

        if metadata_conditions:
            payload['retrieval_model']['metadata_condition'] = {
                'logical_operator': 'and',
                'conditions': metadata_conditions,
            }

        return payload

    def _parse_response(
        self, data: dict[str, Any], query: RetrievalQuery
    ) -> RetrievalResult:
        """Convert Dify's response into a ``RetrievalResult``."""

        raw_records: list[dict[str, Any]] = data.get('records', [])
        today = date.today()
        effective_on = query.filters.effective_on or today

        kept: list[RetrievedChunk] = []
        withheld = 0

        for record in raw_records:
            score: float = float(record.get('score', 0.0))
            if score < query.min_relevance:
                withheld += 1
                continue

            chunk = self._record_to_chunk(record, score)
            if chunk is None:
                # Missing required metadata — skip and log; don't raise.
                # A noisy skip is better than crashing a whole retrieval
                # because one document was ingested without the mandatory
                # mara_document_id field.
                logger.warning(
                    'dify.retrieve skipping record with missing required metadata: %s',
                    record.get('segment', {}).get('id', '<no id>'),
                )
                withheld += 1
                continue

            # Apply effective-date filter client-side for docs where
            # mara_effective_from is set.
            if chunk.effective_from is not None and chunk.effective_from > effective_on:
                withheld += 1
                continue

            kept.append(chunk)
            if len(kept) == query.top_k:
                # Count remaining as withheld (we fetched fetch_k > top_k).
                remaining = raw_records[raw_records.index(record) + 1:]
                withheld += len(remaining)
                break

        return RetrievalResult(
            chunks=tuple(kept),
            no_confident_match=len(kept) == 0,
            withheld_below_threshold=withheld,
        )

    @staticmethod
    def _record_to_chunk(
        record: dict[str, Any], score: float
    ) -> RetrievedChunk | None:
        """Map one Dify record dict to a ``RetrievedChunk``.

        Returns ``None`` when required MARA metadata fields are absent
        (document_id, version, locator, document_kind) — a caller that
        gets None back should skip and log, not raise.
        """

        segment: dict[str, Any] = record.get('segment', {})
        metadata: dict[str, Any] = segment.get('document', {}).get('metadata', {})

        document_id: str | None = metadata.get(_META_DOCUMENT_ID)
        version: str | None = metadata.get(_META_VERSION)
        locator: str | None = metadata.get(_META_LOCATOR)
        kind_raw: str | None = metadata.get(_META_DOCUMENT_KIND)

        # All four are required — §9.4 (version pinning) and §9.3 filtering
        # are unenforceable without them.
        if not (document_id and version and locator and kind_raw):
            return None

        try:
            doc_kind = DocumentKind(kind_raw)
        except ValueError:
            return None

        sensitivity_raw = metadata.get(_META_SENSITIVITY, SensitivityClass.INTERNAL)
        try:
            sensitivity = SensitivityClass(sensitivity_raw)
        except ValueError:
            sensitivity = SensitivityClass.INTERNAL

        effective_from: date | None = None
        if raw_ef := metadata.get(_META_EFFECTIVE_FROM):
            try:
                effective_from = date.fromisoformat(raw_ef)
            except ValueError:
                pass

        superseded_on: date | None = None
        if raw_so := metadata.get(_META_SUPERSEDED_ON):
            try:
                superseded_on = date.fromisoformat(raw_so)
            except ValueError:
                pass

        return RetrievedChunk(
            document_id=document_id,
            version=version,
            locator=locator,
            text=segment.get('content', ''),
            relevance=min(max(score, 0.0), 1.0),
            document_kind=doc_kind,
            sensitivity=sensitivity,
            owning_department=metadata.get(_META_OWNING_DEPARTMENT),
            effective_from=effective_from,
            superseded_on=superseded_on,
        )

    async def aclose(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()

    async def __aenter__(self) -> DifyAdapter:
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()
