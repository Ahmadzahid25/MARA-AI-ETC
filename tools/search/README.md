# Web/external search tool

Implemented (Milestone 3): `run_search()` — permission check (Market Agent
only), timeout (15s), retry (2), domain allow-list filtering, and
typed-error/audit-log behavior per §6.2's row, with the sanitized query
text and domains hit recorded in `ToolInvocationLog.metadata` (§5.7/§6.2's
"every call logged with query and domains hit").

**Sanitization runs inside this tool** (`tools/search/query_sanitizer.py`),
not merely before it, per §6.6 (ACCB Mandatory Change 1) — a caller cannot
bypass it by sanitizing loosely and calling in anyway; a query that can't
be safely generalized after PII removal is rejected with `ToolInputError`
before any outbound request is constructed. Structured PII (Malaysian IC
numbers, business registration numbers, phone numbers, email addresses, a
common street-address form) is detected and stripped for real, via
deterministic regex — genuine engineering. **Free-text applicant/business
name detection is not implemented** — that needs a real NER model, the
same category of open decision as `tools/ocr`'s OCR engine; the
`name_detector` parameter is the seam for wiring one in once chosen.

**Not yet real:**
- No search provider is wired (`engine` is injectable, no default — same
  pattern as `tools/ocr`).
- §6.6's other mandatory control, Kubernetes network-policy-level egress
  enforcement, is infrastructure-only and out of this module's reach — see
  `infrastructure/AGENTS.md`'s Market Agent egress item. Both controls gate
  the Market Agent's existence in any environment with real applicant data
  (§6.6); this tool implements its half.

See [06-tool-architecture.md#66-query-sanitization-on-the-webexternal-search-tool-added-in-v10--accb-mandatory-change-1](../../docs/architecture/06-tool-architecture.md#66-query-sanitization-on-the-webexternal-search-tool-added-in-v10--accb-mandatory-change-1)
for the full specification this module implements. Do not add code here
without a corresponding entry in that document, per
docs/repo-audit/05-development-guidelines.md §5.5.
