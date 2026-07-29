# MARA AI-ETC — Overall Development Plan

> **Directive mode active (2026-07-29):** execution priority is temporarily governed by `docs/architecture/17-vertical-slice-execution-directive.md` until its vertical-slice done definition is passed. Where this file conflicts with that directive, the directive wins for sequencing.

> **This file is the coordination contract for the three development tracks.**
> It answers one question at any moment: *what is each track supposed to be
> doing right now, and what unblocks whom.* It does not replace the
> architecture baseline (`docs/architecture/`) — where they disagree, the
> baseline wins and this file has a bug.

---

## 1. How this plan works (read this first)

**The rule: every time the project moves forward, three files move with it.**
When a track completes something that changes what another track should do,
the lead-dev track updates, in the same PR as the change or immediately after
merge:

1. **This file** — the Status Log (§7) gets a dated entry, and the current
   phase's task tables get their ✅/⏳/❌ flipped.
2. **`apps/officer-workspace/AGENTS.md`** — if the change affects what the
   frontend dev builds against (new endpoint, new field, new contract).
3. **`infrastructure/AGENTS.md`** — if the change affects what the infra dev
   deploys, verifies, or provisions.

The two AGENTS.md files are the *detailed briefs* per track; this file is the
*map* across tracks. A dev starting a work session reads: this file's §4
(current phase) → their own AGENTS.md → then works.

**Report verified, not assumed.** This project has been burned by "done"
claims that were never run. Every status flip in this file states *how it was
verified* (test run, CI link, manual check) or it doesn't flip.

---

## 2. The three tracks

| Track | Who | Owns (write scope) | Brief |
|---|---|---|---|
| **Architecture & Agentic** (lead) | Lead dev + AI pair | `agents/`, `tools/`, `services/`, `workflows/`, `shared/`, `tests/unit/mara/`, `docs/architecture/`, `.github/workflows/mara-ci.yml`, this file | `docs/architecture/00-INDEX.md` |
| **Frontend** | Dev 2 | `apps/officer-workspace/src/**` + that app's own build config. Read-only on `packages/openhands-ui/` | `apps/officer-workspace/AGENTS.md` |
| **Infrastructure & Deployment** | Dev 3 | `infrastructure/**`, `containers/**`, `kind/**`, deployment GitHub Actions | `infrastructure/AGENTS.md` |

**Boundary rule (non-negotiable):** no track edits another track's scope. If
your task seems to need it, stop and flag it in your PR/issue — the fix is a
handoff, not a workaround. The AGENTS.md files repeat this per track; it has
already prevented real drift, keep it strict.

**Shared-by-consumption, owned-by-one:** `shared/schemas/` is the contract
surface. Lead owns the Python; frontend mirrors it in `src/types/` (never
invents shapes); infra treats it as read-only. A contract change is *always*
announced via both AGENTS.md files.

---

## 3. Where we actually are (verified as of 2026-07-27)

Milestones per `docs/architecture/14-roadmap.md`. "Done" below means the
roadmap's own Implementation Status notes agree, not just that code exists.

| Milestone | State | The honest caveat |
|---|---|---|
| **M0 Foundation** | ✅ mostly closed | Docker stack verified by infra (PR #25); observability up; C-1/C-3/C-5 closed |
| **M1 First agent + approval** | ✅ | Gateway 503s until an OCR engine is wired — expected, tracked in M4 below |
| **M2 Knowledge + Compliance** | ✅ code-complete | Dify deployed but no live corpus ingested yet; acceptance criteria (real Compliance Officer verification) blocked on that |
| **M3 Finance/Risk/Market** | ✅ code-complete | §9.7 low-trust tier now implemented and mutation-tested (read side). Still open: real search provider, free-text PII detection, security review |
| **M4 Full Loan Assessment** | ⏳ **← current phase** | Workflow graph built + unit-tested; three integration gaps below |
| **M5 Voice + Audit completeness** | ⏳ half done | Audit Service pulled forward to M1 and already real; Voice Service is an empty stub |
| **M6 Production hardening** | ❌ not started | Blocked on M4/M5 by design |

---

## 4. Current phase: Milestone 4 — Full Loan Assessment, end to end

Parallel execution start (to avoid duplicate work): use four lanes immediately — Backend core, Workflow integration, Applicant web path, and Officer review path — with contract-first handoffs per `docs/architecture/17-vertical-slice-execution-directive.md` §§17.8-17.10.

**Objective (roadmap §14.6):** an officer runs a real application end-to-end —
intake → parallel analysis → risk → recommendation → approval → committee
report — with a multi-day approval pause surviving a service restart.

**Definition of done:** the two acceptance criteria in roadmap §14.6 —
(a) end-to-end run on a pilot batch of realistic de-identified applications,
(b) workflow resumes correctly after a deliberate mid-approval restart drill
against the **real Postgres checkpointer**, not `InMemorySaver`.

### 4.1 Lead track (architecture & agentic)

| # | Task | Status | Unblocks |
|---|---|---|---|
| L1 | Wire Planner → `supervisor_service` dispatch (Planner selects template, supervisor actually dispatches it) | ⏳ next up | L3, pilot batch |
| L2 | Call `supervisor_service` retry/circuit-breaker policy from workflow node boundaries | ❌ | restart drill realism |
| L3 | Run `workflows/` tests against real `postgres-primary` checkpointer; fix what breaks | ❌ — needs I1 | restart drill (DoD b) |
| L4 | Restart drill: pause at a gate, kill the service, resume, verify state | ❌ — needs L3 | DoD (b) |
| L5 | Market-data ingestion path (the §9.7 *write* side: `KnowledgeBackend` gains a write method or a separate ingestion contract; Market Agent's `cache_writer` bound to it; provisional content finally exists) | ❌ | M5 knowledge-approval track, full C3 closure |

### 4.2 Infrastructure track

| # | Task | Status | Unblocks |
|---|---|---|---|
| I1 | Confirm `postgres-primary` checkpointer connection path works from `shared/workflow_engine/checkpointer.py` config (stack is up per PR #25 — this is the wiring + credentials handoff to lead) | ⏳ next up | L3, L4 |
| I2 | Wire an OCR engine + document classifier (`tools/ocr/README.md`, `tools/documents/README.md` list the vendor options; pick, deploy, hand config to lead) | ❌ | the Gateway 503 — blocks *everything* end-to-end, highest infra priority after I1 |
| I3 | Ingest a first real (or realistic) policy corpus into Dify with the `mara_*` metadata fields — `services/knowledge_service/dify_adapter.py` documents the exact field names incl. `mara_trust_tier` | ❌ | M2 acceptance criteria, Compliance verification |
| I4 | Pick + deploy a search provider for `tools/search/`; coordinate the domain allow-list with lead (currently caller-supplied — flag if it should become shared config) | ❌ | M3 leftover, Market Agent live |
| I5 | Apply `infrastructure/k8s/market-agent-egress-networkpolicy.yaml` in a real cluster context when k8s manifests become real (compose-only for now — no action until then, just don't lose it) | ❌ | M6 security assessment |

### 4.3 Frontend track

| # | Task | Status | Unblocks |
|---|---|---|---|
| F1 | **Review & Approval Console** against the live Loan Assessment API (`POST /loans/assessments`, `.../decision`) — per-gate `pending_payload` rendering, the six gates, Approve/Reject/**Correct** three-action rule (§10.5) | ⏳ next up | pilot batch usability |
| F2 | Render `PolicyCitation.trust_tier` — provisional citations visually distinct and labeled ("source not yet reviewed by a Knowledge Owner"). Backend sends only `approved` today; build it now, it's in the contract | ❌ | §9.7 last-step integrity |
| F3 | Render the three withheld counters distinctly (`withheld_below_threshold` / `withheld_unverified` / `withheld_expired`) wherever retrieval detail is surfaced — see AGENTS.md table for the officer-facing meaning of each | ❌ | honest officer messaging |
| F4 | Officer Workspace chat/task view (upload → watch stages via `stage_log`) | ❌ | pilot batch |

### 4.4 Handoffs this phase (who waits on whom)

```
I1 (checkpointer config) ──► L3 ──► L4 (restart drill)
I2 (OCR engine)          ──► first real end-to-end run ──► pilot batch (all three tracks)
I3 (Dify corpus)         ──► M2 acceptance sign-off (lead + Compliance Officer)
L1+L2 (planner/supervisor) ─► pilot batch
F1 (approval console)    ──► pilot batch is *usable*, not just runnable
```

The pilot batch is the phase's convergence point: it needs all three tracks
and is scheduled only when I2, L1, and F1 are all ✅.

---

## 5. Next phases (planned, not active — don't start these without a Status Log entry saying the phase opened)

### Milestone 5 — Voice + audit completeness

| Track | Work |
|---|---|
| Lead | `services/voice_service` (TTS briefing + STT dictation as tool-wrapping, §5.11.2 — *not* an agent); audit narrative-summarization layer (smallest model tier, clearly labeled as generated); sync→async bridge for tool-call audit writes (documented gap in `services/audit_service/README.md`); PDPA subject-access-request query path |
| Infra | TTS/STT engine selection + deployment (Malay/English code-switching is the stated risk R-A3 — vendor choice matters); audit read-path credentials (separate read-only credential per §11) |
| Frontend | Audio briefing playback + dictation capture UI; Auditor console (cross-workflow queries, auditor role only, gaps rendered as findings — "a gap is itself a finding, never smoothed over") |

**DoD:** roadmap §14.7 — audit reconstruction matches ground truth on a test
workflow with deliberately seeded gaps, and the gaps are *reported*, not
smoothed over.

### Milestone 6 — Production hardening & launch gate

| Track | Work |
|---|---|
| Lead | Rework from security-assessment findings (budgeted as R-S2, expected not exceptional); prompt-injection red-team support |
| Infra | HA/DR implementation (two databases = two backup/restore schedules — §9.1.1); DR drill to RTO/RPO targets (§13); load testing; runbooks (§12) |
| Frontend | Accessibility pass; production error/empty states; performance |

**DoD:** roadmap §14.8 — security assessment passed with no unresolved
critical/high findings; DR drill meets targets.

---

## 6. Working agreement (all tracks)

- **Branches/PRs:** feature branches off `main`, PR per coherent change, the
  repo owner merges. No direct pushes to `main`.
- **CI must be green before merge.** `mara-ci.yml` (ruff pinned at 0.12.5 +
  pytest, 3.12/3.13 + compose-config) gates lead-track paths; OpenHands' own
  Lint/FE workflows gate the rest. A PR that needs CI itself fixed says so
  in its description instead of merging red.
- **Commits say why, not just what.** The commit history is doing real work
  as the project's decision record — keep it that way.
- **Dependabot:** weekly, grouped, majors split from minors (see
  `.github/dependabot.yml`'s header comment for the full rationale). Never
  merge a major-group PR without running its build locally first — CI on a
  stale base has lied to us before (#23).
- **Contract changes announce themselves.** Any change to `shared/schemas/`
  or a Gateway endpoint updates both AGENTS.md files in the same PR.
- **Fail closed, and loudly.** Established pattern across the codebase: an
  unconfigured backend raises rather than returning empty; an unknown trust
  tier maps to provisional; a permission miss is an error, not a silent
  narrowing. New code follows it.
- **AI agents:** every track works with an AI pair. The AGENTS.md files are
  written for them — keep them current, because an agent with a stale brief
  confidently does last month's work.

---

## 7. Status Log (newest first — one entry per forward move)

> Format: `date — track — what moved — how it was verified — who needs to react`

- **2026-07-29 — lead** — Persistent restart handoff captured in
  `docs/handoffs/2026-07-29-vertical-slice-recovery.md` with remote commit,
  startup commands, verified tests, known machine-specific issues, and next
  frontend/backend priorities. Use this file as the first recovery anchor
  after any machine reset or environment rebuild.

- **2026-07-29 — frontend** — Officer workspace now consumes vertical-slice
  queue contracts in the UI lane: added typed `/api/v1/*` client methods in
  `apps/officer-workspace/src/services/api.ts` (queue, detail, status,
  officer decision, document upload), wired dashboard data service to real
  officer queue-derived stats/workflows/pending/risk summaries in
  `apps/officer-workspace/src/services/data.ts`, and added a live
  "Vertical Slice Officer Queue" panel with Approve/Reject/Request Info
  actions in `apps/officer-workspace/src/pages/ReviewConsolePage.tsx` while
  keeping legacy assessment view as fallback. *Verified:* editor diagnostics
  clean for touched files; `npm run build` in `apps/officer-workspace` passes.
  *React:* **QA** — run manual officer-flow smoke through review queue actions.

- **2026-07-29 — lead** — Runtime verification for Lane A/B unblocked and
  stabilized: fixed API dependency initialization for tests by setting
  `app.state.vertical_slice_store` at app construction, and normalized in-memory
  application shape so top-level `workflow` is always present/synced with
  `ai_assessment.workflow`. Also fixed router behavior so initial workflow run
  marks `completed` when no interrupt, officer decision returns post-resume
  final status, and document upload can retrigger workflow for
  `queued_waiting_pdf/failed/resume_failed/NEEDS_INFO` cases.
  *Verified:* `uv run --directory . python -m pytest`
  `tests/unit/mara/test_vertical_slice_router.py`
  `tests/unit/mara/test_recommendation_agent.py`
  `tests/unit/mara/test_loan_assessment_workflow.py` => **24 passed**.
  *React:* **Frontend** — proceed wiring against stable `/api/v1` contracts,
  including upload + evolving status transitions. **Infra** — optional:
  configure OTel collector on `localhost:4317` to remove trace-export warnings
  during local test runs.

- **2026-07-29 — lead** — Lane A moved from temporary module globals to a
  repository abstraction with in-memory + AsyncPG implementations
  (`services/api_gateway/vertical_slice_store.py`) and app-lifespan injection;
  `/api/v1` router now uses store dependencies; deterministic workflow->status
  mapping added (`queued/running/paused/completed/failed` to
  `SUBMITTED/PROCESSING/UNDER_REVIEW/APPROVED/NEEDS_INFO`); applicant document
  upload endpoint added (`POST /api/v1/applications/{application_id}/documents`)
  with persisted file path and audit event; contract and frontend brief updated
  (`docs/architecture/17-vertical-slice-execution-directive.md`,
  `apps/officer-workspace/AGENTS.md`). *Verified:* editor diagnostics clean for
  changed files and endpoint contract tests added
  (`tests/unit/mara/test_vertical_slice_router.py`); runtime pytest execution
  still blocked by host Python/uv environment mismatch (`SRE module mismatch`).
  *React:* **Frontend** — wire upload flow + status tracker to new endpoint and
  `UNDER_REVIEW` transitions. **Infra** — ensure upload directory mount policy
  and DB schema bootstrap are aligned in compose.

- **2026-07-29 — lead** — Phase 17 execution directive activated and
  operationalized: parallel lane matrix + anti-rework protocol + contract
  freeze/smoke checklist added (`docs/architecture/17-vertical-slice-execution-directive.md`);
  Loan Assessment acknowledged-hard-violation policy resolved to explicit
  flagged exception path (`has_acknowledged_violation=true`) across schema,
  agent, workflow, and unit tests; API Gateway now exposes vertical-slice v1
  endpoints (`/api/v1/auth/*`, `/api/v1/applications*`,
  `/api/v1/officer/applications*`) with async best-effort loan-workflow trigger
  and resume wiring; Postgres init gained v1 relational skeleton tables
  (`mara_users`, `applicants`, `businesses`, `applications`,
  `application_documents`). *Verified:* editor diagnostics clean for modified
  files; runtime test execution still blocked by local Python/uv environment
  mismatch (`SRE module mismatch`). *React:* **Frontend** — wire applicant and
  officer flows to `/api/v1/*` contracts and render
  `recommendation.has_acknowledged_violation`. **Infra** — execute SQL init
  changes in dev stack and validate DB migration path.

- **2026-07-27 — lead** — §9.7 low-trust tier + market-data freshness
  implemented and enforced in `tools/rag/rag_tool.py`; `TrustTier` required on
  `RetrievedChunk`/`PolicyCitation`. *Verified:* 366 tests green + 5-way
  mutation testing (each enforcement point disabled → specific tests fail).
  *React:* **Frontend** — F2/F3 are now real contract fields (AGENTS.md
  updated). **Infra** — Dify ingestion must write `mara_trust_tier` +
  `mara_cached_at` metadata (adapter documents the names).
- **2026-07-27 — lead** — Dependabot reconfigured (weekly, grouped,
  majors/minors split) after a 12-PR day; eslint-group bump reverted after it
  broke `main`'s frontend CI at `npm ci`. *Verified:* local `npm ci` + lint +
  tsc green on the revert; broken state reproduced first. *React:* nobody —
  but don't re-bump eslint majors, the ignore-list comment explains why.
- **2026-07-27 — lead** — Loan Assessment exposed via Gateway with per-gate
  approval authorization (`shared/auth/approval_gates.py`, PR #28).
  *Verified:* 9 gateway tests incl. per-gate 403s. *React:* **Frontend** —
  build F1 against it (AGENTS.md has the endpoint table).
- **2026-07-27 — infra** — Docker stack verified against a real daemon;
  DB writes verified; Market Agent NetworkPolicy manifest added (PR #25).
  *Verified:* by infra dev, review comments resolved. *React:* **Lead** — I1
  handoff is now possible.
- **2026-07-26 — lead** — Citation verification wired per-task into both
  workflows (PR #27); gate-to-role policy declared (PR #28). *Verified:*
  workflow tests assert a fabricated citation actually fails the run.
  *React:* nobody outstanding.

*(Older history: PR #20–#22 series — agent profiles registry, milestone 3/4
agent implementations, CI repairs. See git log.)*
