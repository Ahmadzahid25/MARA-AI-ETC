# MARA AI-ETC — Repository Audit & Restructuring Plan

**Role:** Senior Software Architect / Repository Maintainer / DevOps Engineer / Open Source Project Maintainer
**Mandate:** analyze the actual repository as it exists and produce a restructuring plan. No files were moved, renamed, or modified as part of producing this plan — it is a plan to be executed deliberately (Step 4), not a record of changes already made.

This audit is grounded in a direct inventory of the working tree (every top-level file and folder was opened and read, not assumed) — see [01-inventory.md](01-inventory.md) for the evidence behind every claim in the rest of this set.

## Contents

| Step | Document |
|---|---|
| 1 | [Repository Inventory](01-inventory.md) |
| 2 | [Problems Found](02-problems-found.md) |
| 3 | [Target Repository Structure](03-target-structure.md) |
| 4 | [Migration Plan](04-migration-plan.md) |
| 5 | [Development Rules](05-development-guidelines.md) |
| 6 | [OpenHands Protection Rules](06-openhands-protection-rules.md) |
| 7 | [Final Output Summary + Recommended Next Step](07-final-output-summary.md) |

## Relationship to the other document sets in this repo

- [../architecture/00-INDEX.md](../architecture/00-INDEX.md) — the 16-phase master architecture plan this audit's target structure implements.
- [../architecture/review/00-review-index.md](../architecture/review/00-review-index.md) — the independent Architecture Review Board critique of that plan. This audit's target structure (Step 3) already incorporates the review board's key findings (e.g., agents reclassified to services, Dify on its own database instance) directly into the folder layout, so implementation doesn't have to reconcile the plan and the review separately later.

## One-paragraph summary

The repository is a full OpenHands checkout with no MARA-specific code written yet — a genuinely clean slate, not a rescue job. The one Critical finding is `enterprise/`, OpenHands' own commercial SaaS surface, carried forward with zero MARA function and real attack-surface cost for a government platform. The target structure keeps every existing OpenHands directory exactly where it is (to stay upstream-mergeable) and adds MARA's new structure alongside it, correcting one naming collision the master plan didn't know about (`docs/`, not `documentation/`) and reclassifying five of the original plan's twelve agents into `services/` per the review board's findings. Recommended first move: a single small PR doing documentation cleanup and the `enterprise/` removal, before Milestone 1 of the architecture roadmap begins.
