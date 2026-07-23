« [Index](00-index.md) | Step 7 of 7 »

# Step 7 — Final Output

## 1. Current Repository Analysis

Full detail: [01-inventory.md](01-inventory.md).

This is a full OpenHands checkout, not a scaffold — `openhands/` (backend, with two coexisting server generations, V0 `server/` and the actively-developed V1 `app_server/`), `frontend/` (coding-agent-oriented React app), `openhands-ui/` (standalone, reusable design-system package), `enterprise/` (OpenHands' own SaaS/commercial add-ons), plus the full complement of OpenHands' own contributor/CI/release tooling. No MARA-specific code exists yet anywhere in the tree. `docs/architecture/` is the one genuinely new addition, created this session, holding the 16-phase master plan and its independent review board critique.

## 2. Problems Found

Full detail: [02-problems-found.md](02-problems-found.md). One Critical (`enterprise/` carried forward as unnecessary attack surface with zero MARA function), three High (docs-domain/CNAME ambiguity, a README/community-docs set that misrepresents what this repository now is, a naming collision between the master plan's proposed `documentation/` and the already-populated `docs/`), six Medium (duplicate-purpose directories that resolve automatically once `enterprise/` is removed, a three-way "agent/skill" naming collision the new MARA `agents/` will make four-way, dual Python lockfiles with no stated authoritative tool), two Low (no environment-config separation yet, a license/citation question that belongs to legal, not engineering).

The encouraging finding underneath all of this: because no MARA code exists yet, every structural fix in Step 3 can be applied cleanly. This is a documentation-and-hygiene audit on top of a genuinely clean slate, not a rescue operation.

## 3. Target Architecture Structure

Full detail: [03-target-structure.md](03-target-structure.md). Existing OpenHands-rooted directories (`openhands/`, `frontend/`, `containers/`, `kind/`, `tests/`, `scripts/`, root compose/build files) stay exactly where they are — deliberately not nested under a `core/` or `apps/` reorganization, because doing so would break every existing path reference and turn future upstream merges into permanent manual conflict resolution, which is precisely what Step 6's protection rules exist to prevent. New MARA structure (`agents/`, `tools/`, `services/`, `workflows/`, `shared/`, `apps/officer-workspace/`, `packages/`, `infrastructure/`, `configs/`) is added alongside. The one directory actually moved is `openhands-ui/` → `packages/openhands-ui/`, because it's self-contained enough that the move is low-risk and it's genuinely reusable as the officer workspace's design-system base — a reuse opportunity the original master plan hadn't inventoried yet. `docs/` (not `documentation/`) is confirmed as canonical, correcting the master plan's Phase 3 on this one point.

## 4. Migration Plan

Full detail: [04-migration-plan.md](04-migration-plan.md). Five phases, ordered by risk: documentation cleanup (zero risk, do first) → folder restructuring (low-medium risk, structure only, no logic) → import/path updates (medium risk — this is where real implementation starts, per the existing roadmap's Milestone 0/1) → CI/CD updates → validation testing, which closes the loop by explicitly proving the OpenHands functionality-preservation mandate held, including a trial upstream-merge dry run as a concrete test rather than a documentation promise.

## 5. Development Guidelines

Full detail: [05-development-guidelines.md](05-development-guidelines.md) and [06-openhands-protection-rules.md](06-openhands-protection-rules.md). Naming conventions that directly defend against the agent/skill naming collision found in Step 2; a branch/commit convention that path-filters by top-level area; code ownership mapped per directory, with approval-gate workflow changes specifically requiring a Compliance sign-off comment, not just a code reviewer; and an explicit, path-by-path protection table for OpenHands' own code — must-not-modify, should-extend, should-wrap, and an upgrade cadence with a concrete compatibility test ("can we still `git merge upstream/main` right now").

## 6. Recommended Next Implementation Step

**Do Phase 1 (documentation cleanup) and the `enterprise/` removal half of Phase 2 first, together, as a single small PR, before any other work — including before Milestone 1 of the original roadmap.**

Reasoning: both are low-risk, high-clarity fixes that cost little and pay off immediately — every contributor (human or AI) who opens this repository from this point forward gets an accurate README, a resolved `docs/` vs `documentation/` question, and a codebase that no longer carries a commercial SaaS product's billing/multi-tenant-auth surface for a government platform to have to explain away in a future security review. Doing this *before* Milestone 1 (which the architecture roadmap already scopes as "prove the core loop" with a Document Agent, per [../architecture/14-roadmap.md](../architecture/14-roadmap.md)) means Milestone 1's engineering work starts against the clean, correctly-named target structure from Step 3, rather than being built against `documentation/`-that-should-have-been-`docs/` or alongside an `enterprise/` directory someone eventually has to remember to remove out from under already-written code.

The remaining Phase 2 items (creating placeholder MARA directories, moving `openhands-ui/`) and all of Phases 3–5 should then proceed in the order given, interleaved with — not blocking — the roadmap's Milestone 0 (Foundation) work from the master plan, since they're substantially the same activity (standing up the skeleton the first real agent gets built into).
