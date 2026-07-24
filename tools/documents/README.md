# Document parsing/classification tools

Implemented (Milestone 1, first slice): `parse_pdf()` and
`classify_document()`, per
[06-tool-architecture.md §6.2](../../docs/architecture/06-tool-architecture.md)'s
PDF-parse and document-classification rows.

- `parse_pdf()`: real native text-layer extraction via `pypdf` (already a
  pinned dependency — no new package added). OCR fallback for pages with no
  native text only runs if a `page_image_renderer` **and** an `ocr_engine`
  are injected — no PDF-page-to-image renderer is wired yet, so by default a
  blank-native-text page is returned as-is rather than silently guessed at.
  Table extraction (`ParsedTable`) is not implemented — no table-detection
  library is in this repo's dependencies yet; `tables` is always empty until
  that's decided.
- `classify_document()`: timeout/retry/permission/audit-log scaffolding is
  real; no real classifier model is wired (same pattern as `tools/ocr` — the
  default raises `ToolExternalServiceError`, inject a `classifier` callable).
  MARA's actual document-type taxonomy also isn't decided yet — see the note
  in `shared/schemas/documents.py`.

See [06-tool-architecture.md](../../docs/architecture/06-tool-architecture.md)
for the full specification. Do not add code here without a corresponding
entry in that document, per docs/repo-audit/05-development-guidelines.md §5.5.
