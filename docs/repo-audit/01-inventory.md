« [Index](00-index.md) | Step 1 of 7 »

# Step 1 — Repository Inventory

Audited directly against the working tree at `MARA AI-ETC/` (which, as established in [../architecture/00-INDEX.md](../architecture/00-INDEX.md), is a full OpenHands checkout being evolved into MARA AI-ETC, not a fresh scaffold). Every top-level entry is accounted for below — nothing skipped, nothing assumed.

## 1.1 Core application directories

```
openhands/

Purpose: OpenHands' Python backend package — the actual runtime this platform is being built on.
Current state: Contains two coexisting server implementations:
  - openhands/server/  — the legacy ("V0") FastAPI server (app.py, listen.py, middleware.py, config/)
  - openhands/app_server/ — explicitly documented (see its own README.md) as "V1 integration": event
    streaming, sandboxed conversation management, MCP, secrets, git, user auth, settings. This is the
    actively-developed surface and the one the MARA AI-ETC architecture plan targets.
  Also contains openhands/db/ (connection/SSL helpers) and openhands/analytics/ (usage-analytics
  service — distinct from enterprise/analytics/, see Problem P-04).
Decision: KEEP. Do not fork/duplicate — extend via the boundary in Step 6.
Reason: This is the substrate every phase of the architecture plan depends on. app_server/ is the
  correct integration point; server/ (V0) should be treated as read-only/reference until upstream
  either removes it or MARA confirms V1 fully supersedes it for our use case.
```

```
frontend/

Purpose: OpenHands' React/Vite officer-facing (currently: developer-facing) web client.
Current state: Full app — src/, tests/, __tests__/, Playwright e2e config, its own package.json /
  package-lock.json (npm), ESLint/Prettier/Husky configured. Built around a coding-agent UX (per the
  architecture review's Finding in architecture/review/01-*, §2.1).
Decision: KEEP the package as the base for the extracted event-stream client (per the review's revised
  Phase-4 verdict), but do NOT treat its existing UI screens as what MARA AI-ETC ships. Officer-facing
  screens are new work layered on top, not a reskin of existing routes.
Reason: Rebuilding the event-stream/WebSocket client from scratch would be pure waste; the coding-agent
  UI chrome (file tree, terminal, browser preview panels) has no role in MARA's officer workflows and
  should not be extended, only bypassed.
```

```
enterprise/

Purpose: OpenHands' own commercial/SaaS add-ons — billing, hosted-multi-tenant auth realm config
  (allhands-realm-github-provider.json.tmpl is Keycloak realm config for OpenHands Cloud specifically),
  its own analytics/, integrations/, migrations/, and a SEPARATE pyproject.toml + poetry.lock from root.
Current state: Fully present, ~1.1MB poetry.lock, independently versioned from the root package.
Decision: DO NOT CARRY FORWARD. Not referenced anywhere in the MARA architecture plan and should be
  excluded from the build/deploy surface entirely (see Problem P-01).
Reason: This is OpenHands' own commercial product surface (billing, their hosted-cloud auth realm). It
  has no MARA function, doubles the Python dependency surface to maintain/patch, and — per the
  architecture review (architecture/review/01-*, §2.3) — every unused module here is attack surface
  with zero offsetting benefit for a government platform.
```

```
openhands-ui/

Purpose: A separate, publishable component/design-system package (Bun-based: .bun-version, bun.lock,
  Storybook configured, its own tsconfig/vite/vitest config, PUBLISHING.md implying it's released to a
  registry independently of the main app).
Current state: Present, self-contained, not yet referenced by the MARA architecture plan at all.
Decision: KEEP, evaluate for reuse as the base design-system layer for the purpose-built officer
  frontend (Step 3), rather than building a component library from zero.
Reason: A working, Storybook-documented design-token system is exactly the kind of solved-problem reuse
  the whole platform strategy is built on — it was simply not inventoried when the original architecture
  plan was written, which is itself Problem P-02.
```

## 1.2 Infrastructure and deployment

```
containers/

Purpose: Dockerfiles for the two OpenHands runtime shapes: containers/app (production image +
  entrypoint.sh) and containers/dev (dev image + compose.yml + dev.sh).
Current state: Minimal, functional, OpenHands-generic (no MARA-specific service images yet).
Decision: KEEP and EXTEND. New service Dockerfiles (per-service images for services/*, per the
  architecture plan's repo structure) get added alongside these, not as a replacement.
Reason: Matches infrastructure/docker/ in the target structure (Step 3) directly — this is already the
  right location, just not yet populated with MARA-specific images.
```

```
kind/

Purpose: Local Kubernetes (via `kind`) cluster config: cluster.yaml + manifests/.
Current state: Present, minimal, generic OpenHands manifests only.
Decision: KEEP and EXTEND under infrastructure/k8s/ conventions (Step 3), do not relocate the existing
  files — add MARA manifests alongside.
Reason: Already the correct local-K8s validation entry point named in the original architecture plan
  (Phase 13); no reason to rename or move it and break existing tooling/scripts that may reference it.
```

```
docker-compose.yml (root)

Purpose: Root-level local dev orchestration (OpenHands app + dependencies).
Current state: Present, single file, OpenHands-generic.
Decision: KEEP as the base; add MARA service overlays as additional compose files
  (docker-compose.mara.yml or infrastructure/compose/*.yml — decided in Step 3), composed via
  `-f docker-compose.yml -f infrastructure/compose/mara.yml`, not by editing this file directly.
Reason: Keeps upstream-mergeable OpenHands compose config untouched (Step 6 protection rule) while
  still giving MARA services a first-class local dev path.
```

```
dev_config/

Purpose: Root-level dev tooling config; contains dev_config/python (interpreter/tooling config for
  local development).
Current state: Present, thin. NOTE: enterprise/dev_config/ also exists as a separate, similarly-named
  directory — see Problem P-03.
Decision: KEEP the root one as-is; flag the enterprise/ duplicate for removal alongside enterprise/
  itself (P-01).
Reason: Root dev_config is referenced by root tooling; no indication it should move.
```

## 1.3 Documentation

```
docs/  [NEW — created this session, not part of the original OpenHands checkout]

Purpose: Currently holds architecture/ (the 16-phase master plan + review board report). No other docs/
  subfolder exists yet.
Current state: New, MARA-only content. The original OpenHands checkout has no docs/ directory at all —
  its documentation lives in a separate docs site repository not present in this tree (evidenced by
  pydoc-markdown.yml at root, which generates API reference docs for an external docs site, and CNAME,
  a GitHub Pages custom-domain file that almost certainly points at OpenHands' own docs domain, not
  MARA's).
Decision: KEEP and become the canonical location for ALL MARA documentation (architecture, runbooks,
  API reference, policy) per the original plan's Phase 3. Reconcile CNAME and pydoc-markdown.yml
  per Problem P-05 rather than silently leaving them pointed at upstream's docs domain.
Reason: This is a genuinely new, clean addition with no upstream conflict risk — the only necessary
  action is making sure the upstream-docs-site tooling (CNAME, pydoc-markdown.yml) doesn't silently
  ship MARA content to, or get confused with, OpenHands' own public docs site.
```

```
AGENTS.md, Development.md, CONTRIBUTING.md, CODE_OF_CONDUCT.md, COMMUNITY.md, ISSUE_TRIAGE.md,
CREDITS.md, CITATION.cff, README.md (root)

Purpose: OpenHands' own contributor/community/citation documentation.
Current state: Present, written for the OpenHands open-source project and community (issue triage
  process, community Slack/Discord references, an academic CITATION.cff for the OpenHands paper).
Decision: KEEP Development.md and CONTRIBUTING.md as living documents to be edited in place for MARA's
  own contribution workflow (Step 5). RENAME/REPLACE README.md content for MARA (see P-06). REMOVE or
  clearly mark as upstream-reference-only: COMMUNITY.md, ISSUE_TRIAGE.md, CREDITS.md, CITATION.cff —
  these describe upstream OpenHands' open-source community process and paper citation, not MARA's.
Reason: Keeping upstream community-process docs in place, unedited, in what is now an internal
  government platform repo is actively misleading to anyone who opens them (P-06).
```

## 1.4 Agent/skill instruction locations (three, inconsistently named)

```
.agents/skills/, skills/ (root), .openhands/microagents/

Purpose: All three hold agent-facing instructional content ("skills"/"microagents") for the coding
  agent itself (OpenHands-the-product's own behavior), NOT for MARA's domain agents.
Current state:
  - skills/ (root): OpenHands' general skill library (github.md, docker.md, code-review.md, etc.)
  - .agents/skills/: a smaller, differently-scoped set (cross-repo-testing/, upcoming-release/,
    update-sdk/, custom-codereview-guide.md) — appears to be this-repo-specific agent instructions
  - .openhands/microagents/: OpenHands' own microagent mechanism (a distinct, product-level concept
    from either of the above two "skills" directories)
Decision: KEEP all three as-is; do NOT let MARA's own domain-agent definitions (agents/* in the target
  structure, Step 3) live in any of them.
Reason: These are three different things that happen to share the word "agent"/"skill": two are
  meta-instructions for the coding assistant helping build this repo, one is an OpenHands product
  feature. MARA's Document/Compliance/Finance/etc. agents are a fourth, unrelated concept and must get
  their own clearly-named directory (Problem P-07) or this naming collision will confuse every future
  contributor, human or AI.
```

## 1.5 Root config and metadata files

| File | Purpose | Decision | Reason |
|---|---|---|---|
| `pyproject.toml`, `poetry.lock` | Root Python package definition + Poetry lock | KEEP, but see P-08 (dual lockfile with uv.lock) | Actively used by Makefile/CI |
| `uv.lock` | Root Python lock for `uv` package manager | KEEP, resolve P-08 | Suggests an in-progress Poetry→uv migration |
| `pytest.ini`, `MANIFEST.in`, `Makefile`, `build.sh` | Python test/build tooling | KEEP | Core to existing CI, no MARA-specific reason to change |
| `config.template.toml` | OpenHands runtime config template | KEEP, extend with MARA-specific config keys via the pattern in Step 6 | Do not fork; extend |
| `pydoc-markdown.yml` | Generates API docs for OpenHands' external docs site | RECONCILE (P-05) | Currently ambiguous target after `docs/` was added this session |
| `.release-please-manifest.json`, `.release-please-manifest.cloud.json`, `release-please-config.json`, `release-please-config.cloud.json` | Automated release/versioning config; `.cloud` variants are for OpenHands Cloud (SaaS) releases | KEEP the non-cloud pair; REMOVE the `.cloud` pair | The cloud-release pipeline belongs to OpenHands' own SaaS product, same category as `enterprise/` (P-01) |
| `CNAME` | GitHub Pages custom domain pointer | RECONCILE (P-05) | Almost certainly points to OpenHands' own docs domain; must not silently apply to a MARA deployment |
| `LICENSE` | OpenHands' open-source license | KEEP, but confirm with MARA legal/procurement that the license terms are understood and accepted for a government derivative | Not a technical decision — flagged for the record, not resolved by this audit |
| `.editorconfig`, `.gitattributes`, `.gitignore`, `.dockerignore`, `.nvmrc` | Standard tooling config | KEEP | No conflict with MARA's needs |
| `.github/` (workflows, actions, ISSUE_TEMPLATE, dependabot.yml, pull_request_template.md) | CI/CD and repo-community automation | KEEP workflows/actions as the base for Step 4's CI/CD updates; REVIEW ISSUE_TEMPLATE and pull_request_template.md for OpenHands-community-specific language to replace with MARA's own (Step 5) | Actively load-bearing infrastructure, not cosmetic |
| `.devcontainer/`, `.vscode/` | Editor/devcontainer setup | KEEP | Generic, useful as-is |

## 1.6 Testing

```
tests/

Purpose: Root-level Python test suite. tests/unit/ already contains subfolders matching the source
  layout: app_server/, enterprise/, frontend/ (Python-side tests touching frontend build?), integrations/,
  mcp/, server/, storage/, plus top-level test_*.py files (analytics, azure_devops, enterprise migration
  integrity, etc.)
Current state: Structured 1:1 against openhands/'s and enterprise/'s existing module layout.
Decision: KEEP as the location for backend unit tests; MARA-specific test categories (agent_evals/,
  integration/, e2e/ named in the original architecture plan's Phase 3) are ADDED as new subfolders
  here, not a parallel top-level tests-v2/ directory.
Reason: One test root, consistent with the "one monorepo" principle already adopted; avoids the
  confusion of two different `tests/` conventions in one repo.
```

```
scripts/

Purpose: Repo maintenance automation — mostly OpenHands-community-process scripts (auto-closing
  duplicate issues, good-first-issue labeling, OpenAPI schema updates, enterprise-migration-integrity
  checks).
Current state: All scripts are OpenHands-project-maintenance-specific; none are MARA-operational
  (no migration/seed/load-test scripts yet, as anticipated by the original architecture plan's Phase 3).
Decision: KEEP existing scripts (still useful if MARA continues syncing from upstream OpenHands issues/
  PRs is not actually happening — see P-09 for the one that should be explicitly evaluated:
  check_enterprise_migration_integrity.py, which exists only to support enterprise/, itself marked for
  removal). ADD MARA operational scripts alongside, not in a separate scripts-mara/ directory.
Reason: Consistent with the "one location per concern" principle applied throughout this audit.
```
