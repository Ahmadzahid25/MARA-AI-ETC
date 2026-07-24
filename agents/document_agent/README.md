# Document Agent

Implemented (Milestone 1): `DocumentAgent.process_document()` — classifies
and parses a document via `tools/documents/`, then turns raw page text into
named, confidence-scored fields (`shared/schemas/documents.py`'s
`DocumentExtractionRecord`). Confidence threshold 0.85 per field, per
[05-agent-architecture.md §5.3](../../docs/architecture/05-agent-architecture.md#53-document-agent).

**Not wired into the OpenHands event-stream Agent Runtime**
(`openhands/app_server/event`) that
[02-system-architecture.md §2.2](../../docs/architecture/02-system-architecture.md#22-layer-responsibilities)
describes — that integration is a separate, larger task. `DocumentAgent` is
directly callable and independently testable in the meantime.

No real document classifier or OCR engine is wired underneath this (see
`tools/documents/README.md` and `tools/ocr/README.md`) — `DocumentAgent`
accepts injectable `classifier`/`field_extractor` for testing; production use
needs real implementations chosen and wired first.

See [05-agent-architecture.md](../../docs/architecture/05-agent-architecture.md)
for the full specification. Do not add code here without a corresponding
entry in that document, per docs/repo-audit/05-development-guidelines.md §5.5.
