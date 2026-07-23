« [Index](00-index.md) | Step 2 of 7 »

# Step 2 — Problems Found

Every problem below was observed directly in the working tree (Step 1), not inferred. Where a claim would require content-diffing files to confirm (e.g., "these two files are byte-identical"), it is stated as what it actually is — a naming/location collision, not a confirmed duplicate file — since asserting a duplicate without checking would be exactly the kind of false-precision this audit is supposed to prevent.

## Critical

**P-01 — `enterprise/` and its associated `.cloud` release pipeline are carried forward with zero MARA function and real attack-surface cost.**
`enterprise/` is OpenHands' own commercial SaaS product surface: billing, a hosted-multi-tenant Keycloak realm template (`allhands-realm-github-provider.json.tmpl`), its own `pyproject.toml`/`poetry.lock` (~1.1MB), its own `analytics/`, `integrations/`, and database `migrations/`. Nothing in the MARA architecture plan references it. Paired with it: `.release-please-manifest.cloud.json` and `release-please-config.cloud.json` at root, which automate *releases of that same SaaS product*. Left in place, this is: (a) a second, independently-versioned Python dependency tree to patch and audit for a government platform that gets zero benefit from it, (b) a live billing/multi-tenant-auth code path sitting in a repository that a security reviewer (per the architecture review's Milestone 6 gate) will have to explicitly rule out as in-scope rather than being able to assume it isn't there, and (c) a plausible source of accidental exposure if any deploy tooling ever globs `**/Dockerfile` or similar without an explicit exclude. **This is not a style problem — it is undefended surface in a system whose own threat model (architecture plan, Phase 11) is built around minimizing exactly this.**

## High

**P-05 — `CNAME` and `pydoc-markdown.yml` point at (or are configured for) OpenHands' own public docs domain/pipeline, with no MARA-specific reconciliation.**
`CNAME` is a GitHub Pages custom-domain file; in the upstream OpenHands repo this almost certainly resolves to OpenHands' own public documentation domain. `pydoc-markdown.yml` generates API reference docs for that same external docs site. Now that `docs/` holds real, internal MARA architecture content (added this session), there are two live risks: (1) if this repository's Pages/docs-publish pipeline is ever activated as-is, MARA content could attempt to publish under OpenHands' own domain configuration, and (2) nothing currently states where MARA's own generated API docs (mentioned in the target structure, `docs/api/`) should actually be published, leaving a real gap between "we generate API docs" and "here's where they safely go for an internal government system." Neither file should be treated as inert config to leave alone.

**P-06 — Root `README.md` and community-process docs (`COMMUNITY.md`, `ISSUE_TRIAGE.md`, `CREDITS.md`, `CITATION.cff`) still present this repository as the public OpenHands open-source project.**
Anyone opening this repository — including a government security reviewer, per the architecture plan's Milestone 6 gate — lands on a README describing OpenHands' own product, links to OpenHands' Slack/Discord community, an issue-triage process for OpenHands' public issue tracker, and an academic citation for the OpenHands paper. None of this describes what the repository actually is now. This is a documentation-accuracy problem with real audit-optics consequences: a repo whose front door doesn't match its actual contents reads as unmaintained or unreviewed to anyone assessing it formally.

**P-10 — The architecture plan's own target structure names a top-level `documentation/` folder; this session already created and populated `docs/architecture/` instead.**
[../architecture/03-repository-structure.md](../architecture/03-repository-structure.md) specifies `documentation/` as the docs root. That document was written before this audit inventoried the actual repository and noticed `docs/` is the more natural fit (no upstream OpenHands `documentation/` convention exists to conflict with, and `docs/` is already the directory this session used). If this isn't reconciled explicitly now, the two names will keep drifting apart as more content is added to whichever one a given contributor reaches for first — this is exactly how documentation duplication starts, and it's cheapest to fix before any more content accumulates in either location.

## Medium

**P-03 / P-04 — Duplicate-purpose directories: `dev_config/` (root) vs. `enterprise/dev_config/`, and `openhands/analytics/` vs. `enterprise/analytics/`.**
Both pairs share a name and an apparent purpose but live in different trees. Both are fully resolved as a side effect of removing `enterprise/` (P-01) — flagged separately here only so nobody spends effort trying to "reconcile" or "merge" these two pairs before realizing one side of each pair is going away entirely.

**P-07 — Three differently-scoped, similarly-named "agent instruction" locations already exist (`skills/`, `.agents/skills/`, `.openhands/microagents/`), and the architecture plan's proposed `agents/` (MARA's domain agents — Document, Compliance, Finance, etc.) will be a fourth.**
None of the existing three are wrong — each serves a real, distinct purpose for the coding assistant / OpenHands product itself. The problem is purely naming collision risk: a future contributor (human or AI) grepping for "where do agent instructions live" has three existing plausible hits before MARA's actual domain-agent code is even added. Left unaddressed, this is a recurring source of "which agents folder do you mean" confusion, worst-case someone puts a MARA domain-agent prompt inside `.openhands/microagents/` because it's the first match, silently changing its runtime behavior (microagents are an OpenHands product mechanism, not inert documentation).

**P-08 — Root has both `poetry.lock` and `uv.lock`, with no stated authoritative tool.**
Two Python dependency lockfiles for the same `pyproject.toml`, if both are real and maintained, will drift — one gets updated on a dependency bump and the other silently doesn't, and whichever CI/dev-setup path uses the stale one gets a different environment than intended. This reads as a mid-migration state (Poetry → `uv`, a common and reasonable modernization) rather than an accident, but an in-progress migration with no stated target/deadline is itself a maintenance hazard.

**P-11 — `.agents/` (dot-prefixed, root) and the architecture plan's proposed `agents/` (undotted, MARA domain agents) are one character apart.**
Related to P-07 but specifically a *typo-distance* risk rather than a conceptual-overlap risk: `.agents/` vs `agents/` is exactly the kind of pair that produces a wrong `cd`, a wrong glob pattern in a script, or a wrong path in a `.gitignore` rule. Both need to keep existing (different real purposes), but this pairing specifically should be called out in the naming conventions (Step 5), not left to be discovered by accident.

**P-09 — `scripts/check_enterprise_migration_integrity.py` exists solely to support `enterprise/`, which is marked for removal (P-01).**
Not a problem on its own — flagged so it's handled as part of the P-01 removal rather than orphaned as a script that silently starts failing (or silently stops being run and nobody notices) once its target directory is gone.

## Low

**P-12 — No environment-specific configuration separation exists yet (dev/staging/production).**
`config.template.toml` is a single generic template; the architecture plan's `configs/{dev,staging,production}/` (Phase 3) hasn't been created yet. Not a defect — nothing has outgrown a single template yet — but worth resolving in the migration plan (Step 4) before configuration values start accumulating without a clear environment boundary, which is a much more disruptive thing to retrofit than to establish early.

**P-13 — `LICENSE` (OpenHands' own open-source license) and `CITATION.cff` (academic citation for the OpenHands paper) need an explicit legal/procurement decision, not a technical one.**
This audit cannot resolve whether OpenHands' license terms are fully understood and accepted for a derivative government platform, or what MARA's own citation/attribution requirements are — that determination belongs to MARA legal/procurement, not to this repository audit. Recorded here so it isn't silently dropped.

## What was checked and found clean

No stray temporary files (`.tmp`, editor swap files, orphaned build artifacts) were found at any level inspected. No MARA-specific code exists yet in the wrong location, because none exists yet at all — the repository is, encouragingly, still in a state where every structural decision in Step 3 can be applied cleanly rather than retrofitted around existing misplaced code.

## Severity summary

| Severity | Count | Items |
|---|---|---|
| Critical | 1 | P-01 |
| High | 3 | P-05, P-06, P-10 |
| Medium | 6 | P-03, P-04, P-07, P-08, P-09, P-11 |
| Low | 2 | P-12, P-13 |
