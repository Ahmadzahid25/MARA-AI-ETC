« [Index](00-index.md) | Step 4 of 7 »

# Step 4 — Migration Plan

Each phase is independently mergeable and independently revertible — no phase depends on a later phase already being done, and no phase leaves the repository in a state where `make build`/CI is broken partway through. This ordering (docs before folders before code before CI before validation) is deliberate: it front-loads the zero-risk, high-value fixes (documentation accuracy) and defers anything touching import paths or CI to after the structural target is actually in place and agreed.

## Phase 1 — Documentation cleanup

**Goal:** the repository's front door tells the truth, before anything else changes.

1. Rewrite root `README.md` to describe MARA AI-ETC, its relationship to upstream OpenHands, and link to `docs/architecture/00-INDEX.md`. Preserve a short "Built on OpenHands" attribution section rather than erasing the lineage — this repo's dependency on upstream is a documented architectural decision (Phase 4 of the master plan), not something to obscure.
2. Mark `COMMUNITY.md`, `ISSUE_TRIAGE.md`, `CREDITS.md`, `CITATION.cff` as upstream-reference-only — either move them under a clearly-labeled `docs/upstream-reference/` or prepend a one-line notice to each stating they describe the upstream OpenHands project, not this repository's own process (resolves P-06). Do not delete outright without MARA legal/comms sign-off, since `CITATION.cff` in particular may carry attribution obligations under the OpenHands license (P-13).
3. Resolve `CNAME` and `pydoc-markdown.yml` (P-05): confirm whether the GitHub Pages publish pipeline these support is even active for this fork; if not active, leave a comment in each stating so; if active, repoint to a MARA-controlled domain/target before any docs-publish workflow runs against this repo.
4. Reconcile `documentation/` vs `docs/` (P-10): edit [../architecture/03-repository-structure.md](../architecture/03-repository-structure.md) to reference `docs/` instead of `documentation/`, matching Step 3 of this audit. One-line change, but must happen before any new content gets written against the wrong name.
5. Add the naming-disambiguation table (Step 3, §3.3) to `AGENTS.md`.

**Risk:** none — this phase touches no code path, no import, no CI.

## Phase 2 — Folder restructuring

**Goal:** the new top-level directories from Step 3 exist, populated with nothing but placeholder `README.md` files stating each folder's purpose and linking back to the relevant architecture-plan phase. No agent/tool/service code is written yet — this phase is structure only.

1. Create `apps/officer-workspace/`, `packages/event-stream-client/`, `agents/`, `tools/`, `services/`, `workflows/`, `shared/`, `infrastructure/{docker,k8s,terraform,compose}/`, `configs/{dev,staging,production}/`, each with a `README.md`.
2. Move `openhands-ui/` → `packages/openhands-ui/`. This is the one real move in this plan (Step 3's rationale). Update the one or two internal config references (its own `package.json` workspace path, if the repo uses npm/bun workspaces) and confirm `bun install`/its Storybook build still runs from the new path before merging.
3. Remove `enterprise/`, `.release-please-manifest.cloud.json`, `release-please-config.cloud.json` (P-01). Before deleting: confirm via `git log`/`git blame`-equivalent history search that nothing outside `enterprise/` imports from it (expected: nothing, since `enterprise/` has its own separate `pyproject.toml`), and remove `scripts/check_enterprise_migration_integrity.py` alongside it (P-09).
4. Remove the now-orphaned `enterprise/dev_config/` and `enterprise/analytics/` as part of the same deletion (P-03/P-04 resolve automatically).

**Risk:** Low-Medium. The `openhands-ui/` move is the only step with real blast radius, and it's contained (Step 3 rationale). The `enterprise/` removal is higher-consequence but low-probability-of-breakage given it's already dependency-isolated (its own lockfile) — still, do this as its own commit, separately revertible from the `openhands-ui/` move.

## Phase 3 — Import/path updates

**Goal:** everything created as a placeholder in Phase 2 becomes real, wired-together code — this is where actual agent/tool/service implementation begins, per [../architecture/14-roadmap.md](../architecture/14-roadmap.md)'s Milestone sequencing (which this audit does not change).

1. Extract `packages/event-stream-client/` from `frontend/src`'s actual WebSocket/event-stream handling code — a real code extraction, not a copy, so future OpenHands upstream changes to that logic can still be diffed against and pulled in.
2. Wire `apps/officer-workspace/` to consume `packages/event-stream-client/` and `packages/openhands-ui/`.
3. Begin `agents/`, `tools/`, `services/` implementation per the roadmap's Milestone 0/1 scope — this phase is where Phase 1's "extract subsystems from `openhands/app_server/`, don't fork the whole tree" (review board, Part 1 §2.5) actually gets implemented as real import boundaries (new MARA modules importing `openhands.app_server.*` as a library, not copy-pasting or modifying its internals).
4. Resolve P-08 (dual lockfiles): pick `uv` as authoritative (recommended — it's the newer, faster tool and the presence of both suggests a migration already in progress, not a reason to move backward to Poetry), regenerate `uv.lock` as the single source of truth, and either remove `poetry.lock` or clearly mark it deprecated with a removal date. This is listed here rather than Phase 2 because it's worth doing once Phase 3's new packages exist and need to be in the dependency graph anyway, rather than twice.

**Risk:** Medium — this is genuine new-code-writing, not restructuring, and carries whatever risk normal feature development carries. Structural risk specific to this audit (broken imports, wrong paths) is low because Phase 2 already validated the target locations exist and build.

## Phase 4 — CI/CD updates

**Goal:** `.github/workflows/` and `.github/actions/` know about the new structure.

1. Add CI jobs for `agents/`, `tools/`, `services/`, `workflows/`, `apps/officer-workspace/`, `packages/*` — test, lint, build per the conventions in Step 5.
2. Update any workflow that references `enterprise/` (e.g., a matrix build step, a path filter) to remove it — audit `.github/workflows/*.yml` explicitly for `enterprise` string matches rather than assuming none exist.
3. Update `dependabot.yml` to stop scanning `enterprise/`'s now-removed `pyproject.toml`, and to include the new `packages/*`/`apps/*` package manifests.
4. Update `.github/ISSUE_TEMPLATE/` and `pull_request_template.md` to drop OpenHands-community-specific language (e.g., references to OpenHands' own contribution triage process) in favor of MARA's own (Step 5 defines what that should say).

**Risk:** Medium — CI misconfiguration fails loudly (a red build), which is the safe failure mode; the risk is delay, not silent breakage.

## Phase 5 — Validation testing

**Goal:** prove nothing upstream-facing broke, before declaring the migration complete.

1. Full existing test suite (`tests/unit/`, including `app_server/`, `frontend/`, `mcp/`, `storage/` subfolders) passes unmodified — this is the direct check that Step 6's "avoid breaking OpenHands functionality" mandate held.
2. `make build` / `build.sh` succeed from a clean checkout.
3. `docker-compose.yml` (root, unchanged) plus the new `infrastructure/compose/mara.yml` overlay both bring up a working local environment.
4. `kind/` cluster still stands up unmodified; new `infrastructure/k8s/` manifests deploy alongside it without conflict.
5. A trial upstream-merge dry run (`git fetch upstream && git merge --no-commit upstream/main`, if an upstream remote is configured) to confirm this migration didn't introduce merge-conflict hotspots in files that weren't supposed to move — this is the concrete test of the Step 6 protection rules, not just a documentation promise.

**Risk:** none introduced by this phase — it is entirely detective, not additive. Any failure found here is a signal to revisit the specific earlier phase that caused it, not a reason to add compensating code.
