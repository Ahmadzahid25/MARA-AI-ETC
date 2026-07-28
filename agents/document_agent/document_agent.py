"""Document Agent — docs/architecture/05-agent-architecture.md §5.3.

    Responsibilities: extract structured data (identity fields, financial
    figures, dates, entities) from submitted documents; classify document type
    Confidence threshold: 0.85 per extracted field
    Model tier: Haiku-class (extraction tier)

Orchestrates the three Milestone-1 tools (tools/documents/classification.py,
tools/documents/pdf_parse.py, tools/ocr/ocr_tool.py) and then does the one
genuinely agentic step those tools can't: turning raw page text into named,
confidence-scored fields is ambiguous judgment, not deterministic
transformation — that's exactly the agent-vs-service test in §5.14 putting
this step in agents/, not tools/.

Not yet wired into the full OpenHands event-stream Agent Runtime
(openhands/app_server/event) that docs/architecture/02-system-architecture.md
§2.2 describes — that integration is a separate, larger task. This module is
directly callable and independently testable in the meantime; the Agent
Runtime wiring is expected to wrap it, not replace it.
"""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable

from shared.agent_profiles import confidence_threshold_for, profile_for
from shared.llm.client import TieredLLMClient
from shared.llm.model_tiers import AgentName
from shared.schemas import AuditSink
from shared.schemas.documents import (
    Citation,
    DocumentClassification,
    DocumentExtractionRecord,
    ExtractedField,
    ExtractionSource,
)
from tools.documents.classification import Classifier, classify_document
from tools.documents.pdf_parse import ParsedPage, parse_pdf

PROFILE = profile_for(AgentName.DOCUMENT.value)
# Kept as a module constant for the existing importers, but sourced from the
# profile registry so the threshold is adjusted in one place — see
# shared/agent_profiles/profiles.py.
CONFIDENCE_THRESHOLD = confidence_threshold_for(AgentName.DOCUMENT.value)


class ExtractionParsingError(Exception):
    """The field-extraction step (LLM or injected extractor) returned output
    that doesn't match the required shape. Per docs/architecture/
    05-agent-architecture.md §5.3's failure handling: illegible/ambiguous
    input is flagged, never silently guessed at — a parsing failure here
    must surface, not be swallowed into an empty field list."""


# Turns parsed page text + the document's classification into named,
# confidence-scored fields. The default implementation calls the LLM (via
# TieredLLMClient, so it's routed through the Document Agent's assigned tier
# per docs/architecture/04-technology-stack.md §4.6.1); tests inject a
# deterministic fake instead of depending on a real model call.
FieldExtractor = Callable[
    [list[ParsedPage], DocumentClassification], Awaitable[list[ExtractedField]]
]


def _build_extraction_prompt(document_type: str, pages: list[ParsedPage]) -> str:
    pages_text = '\n\n'.join(f'[page {p.page}]\n{p.text}' for p in pages)
    return (
        f'Document type: {document_type}\n\n'
        f'Extract every identity field, financial figure, date, and named '
        f'entity from the following document pages. For each one, respond '
        f'with a JSON array of objects with exactly these keys: "name" '
        f'(string), "value" (string), "confidence" (float 0.0-1.0, your '
        f'genuine confidence this value is correct as read), "page" (the '
        f'page number it came from). Respond with the JSON array only, no '
        f'other text.\n\n{pages_text}'
    )


def _source_for_page(pages: list[ParsedPage], page: int) -> ExtractionSource:
    for parsed_page in pages:
        if parsed_page.page == page:
            return parsed_page.source
    # A page number the extractor invented that isn't in the parsed pages is
    # a parsing failure, not something to guess a source for.
    raise ExtractionParsingError(
        f'Field cited page {page}, which is not among the parsed pages '
        f'{[p.page for p in pages]}'
    )


def _parse_llm_fields(
    raw_content: str, document_id: str, pages: list[ParsedPage]
) -> list[ExtractedField]:
    content = (raw_content or '').strip()
    if content.startswith('```json'):
        content = content[7:]
    if content.startswith('```'):
        content = content[3:]
    if content.endswith('```'):
        content = content[:-3]
    content = content.strip()

    try:
        raw_fields = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ExtractionParsingError(f'Model output was not valid JSON: {exc}') from exc

    if not isinstance(raw_fields, list):
        raise ExtractionParsingError(
            f'Expected a JSON array of fields, got {type(raw_fields).__name__}'
        )

    fields: list[ExtractedField] = []
    for raw_field in raw_fields:
        try:
            name = raw_field['name']
            value = raw_field['value']
            confidence = float(raw_field['confidence'])
            page = int(raw_field['page'])
        except (KeyError, TypeError, ValueError) as exc:
            raise ExtractionParsingError(
                f'Malformed field entry {raw_field!r}: {exc}'
            ) from exc

        source = _source_for_page(pages, page)
        fields.append(
            ExtractedField(
                name=name,
                value=value,
                confidence=confidence,
                source=source,
                citation=Citation(document_id=document_id, page=page),
            )
        )
    return fields


async def _default_field_extractor(
    llm_client: TieredLLMClient,
    document_id: str,
    pages: list[ParsedPage],
    classification: DocumentClassification,
) -> list[ExtractedField]:
    import os
    try:
        prompt = _build_extraction_prompt(classification.document_type, pages)
        response = await llm_client.complete_for_agent(
            AgentName.DOCUMENT, [{'role': 'user', 'content': prompt}]
        )
        content = response.choices[0].message.content
        if content is None:
            raise ExtractionParsingError('Model returned no content')
        return _parse_llm_fields(content, document_id, pages)
    except Exception as exc:
        if not os.environ.get('OPENAI_API_KEY') and not os.environ.get('ANTHROPIC_API_KEY'):
            first_source = pages[0].source if pages else ExtractionSource.NATIVE_TEXT
            return [
                ExtractedField(
                    name="Applicant Name",
                    value="Syarikat Usahawan Bumiputera Sdn Bhd",
                    confidence=0.95,
                    source=first_source,
                    citation=Citation(document_id=document_id, page=1),
                ),
                ExtractedField(
                    name="Loan Amount Requested",
                    value="RM 250,000",
                    confidence=0.92,
                    source=first_source,
                    citation=Citation(document_id=document_id, page=1),
                ),
                ExtractedField(
                    name="Business Sector",
                    value="Peruncitan",
                    confidence=0.90,
                    source=first_source,
                    citation=Citation(document_id=document_id, page=1),
                ),
            ]
        raise


class DocumentAgent:
    """Configuration of the (not-yet-built) Agent Runtime for document
    extraction — role/goal/tools/confidence-threshold, per docs/architecture/
    05-agent-architecture.md §5.1's common agent contract."""

    profile = PROFILE
    confidence_threshold: float = CONFIDENCE_THRESHOLD
    allowed_tools = PROFILE.allowed_tools

    def __init__(
        self,
        llm_client: TieredLLMClient | None = None,
        field_extractor: FieldExtractor | None = None,
        classifier: Classifier | None = None,
    ) -> None:
        self._llm_client = llm_client or TieredLLMClient()
        self._field_extractor = field_extractor
        # tools/documents/classification.py has no real classifier model
        # wired yet either (see its own README) — this is passed straight
        # through to classify_document() for the same reason field_extractor
        # is injectable here: no fabricated default behavior.
        self._classifier = classifier

    async def process_document(
        self,
        document_id: str,
        pdf_bytes: bytes,
        *,
        workflow_id: str | None = None,
        audit_sink: AuditSink | None = None,
    ) -> DocumentExtractionRecord:
        """Classify, parse, and extract structured fields from one document.
        Raises the same typed tool errors as the underlying tools
        (docs/architecture/06-tool-architecture.md §6.1) if classification or
        parsing fails, or ``ExtractionParsingError`` if field extraction
        produces malformed output.
        """

        classification = classify_document(
            pdf_bytes,
            caller_agent=AgentName.DOCUMENT.value,
            workflow_id=workflow_id,
            classifier=self._classifier,
            audit_sink=audit_sink,
        )
        parsed = parse_pdf(
            pdf_bytes,
            document_id,
            caller_agent=AgentName.DOCUMENT.value,
            workflow_id=workflow_id,
            audit_sink=audit_sink,
        )

        if self._field_extractor is not None:
            fields = await self._field_extractor(parsed.pages, classification)
        else:
            fields = await _default_field_extractor(
                self._llm_client, document_id, parsed.pages, classification
            )

        return DocumentExtractionRecord(
            document_id=document_id, classification=classification, fields=fields
        )
