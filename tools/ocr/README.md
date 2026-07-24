# OCR tool

Implemented (Milestone 1, first slice): `run_ocr()` — timeout (30s/page),
retry (2, exponential backoff), permission check (Document Agent only), and
typed-error/audit-log behavior per
[06-tool-architecture.md §6.1–§6.2](../../docs/architecture/06-tool-architecture.md).

**No real OCR engine is wired.** The default engine raises
`ToolExternalServiceError` — self-hosted PaddleOCR/Tesseract integration
(§6.2's stated default) is a separate follow-up task. Callers (and tests)
inject an `engine: OCREngine` callable in the meantime. A cloud-OCR fallback
path is deliberately not implemented — §6.2 gates it behind a
document-sensitivity flag that doesn't exist yet (Phase 11).

Sandboxing (§6.4 — OCR processes untrusted file content, should run inside
`app_server/sandbox`) is also not wired — out of scope for this slice; the
module has a clean call boundary so sandboxing can wrap it later.

See [06-tool-architecture.md](../../docs/architecture/06-tool-architecture.md)
for the full specification. Do not add code here without a corresponding
entry in that document, per docs/repo-audit/05-development-guidelines.md §5.5.
