# Publishing service (merged Report+Presentation)

Implemented (Milestone 4): `publish_committee_materials()` — renders a
real committee report (`render_docx`) and presentation deck
(`render_pptx`) from approved upstream outputs, using `python-docx`/
`python-pptx` (already-pinned dependencies, no vendor-choice gap). Every
citation carried by the source agent outputs is rendered into the output —
compliance policy citations, financial product-term citations, risk
precedent citations inline in the report, and preserved in the deck's
speaker notes rather than cluttering on-slide bullets (§5.11.1: "deck
speaker notes retaining citations").

Refuses to render (raises `MissingApprovedInputError`) rather than
drafting a placeholder when the inputs are structurally unpublishable: a
withheld recommendation (no `decision`) or a risk rating that isn't
`RiskStatus.COMPLETE`. This module cannot itself verify "did this pass its
approval gate" — that's state the calling workflow
(`workflows/loan_assessment`) owns; what it can and does check is
structural publishability regardless of what the caller believes.

**Not registered as separate Tool Runtime modules under `tools/`,
deliberately** — see `services/publishing_service/rendering.py`'s module
docstring: §6.2 catalogues Word/PowerPoint generation as tools whose sole
permitted caller is this service (not one of the 7 agents), and
`shared/agent_profiles`'s `callers_allowed_for_tool()` registry — the
mechanism `tools/README.md` says every tool must use — only covers
agent-side grants. Extending it to service-level grants is a decision for
whoever owns that registry, not made unilaterally here.

The "optional narrative smoothing" §5.11.1 mentions (one constrained LLM
call for prose transitions between sections) is not implemented — every
section renders directly from structured input, no LLM call in this
module at all.

See [05-agent-architecture.md#5111-publishing-service-merged-report--presentation](../../docs/architecture/05-agent-architecture.md#5111-publishing-service-merged-report--presentation)
for the full specification this module implements. Do not add code here
without a corresponding entry in that document, per
docs/repo-audit/05-development-guidelines.md §5.5.
