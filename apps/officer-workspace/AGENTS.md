# apps/officer-workspace — AI agent brief (read this before every task)

You are working on the **frontend only**. This file is your boundary and your
map. Read it fully before touching anything, every session — don't rely on
memory from a previous session.

## Hard boundary — read this part twice

**You touch files under `apps/officer-workspace/` and nowhere else.** Specifically:

- ❌ **Never** edit anything under `agents/`, `services/`, `tools/`, `workflows/`,
  `shared/`, `infrastructure/`, `openhands/`, `configs/`, `.github/workflows/`.
  These are backend/platform/system — owned by someone else. If a task seems
  to require changing one of these, **stop and flag it** — do not work around
  it by, e.g., inventing a fake local copy of backend logic inside the
  frontend app.
- ⚠️ **Read-only** on `packages/openhands-ui/` — you *consume* its exported
  components (`import { Button } from '@openhands/ui'`, etc.). Do not modify
  files inside that package. If a component you need doesn't exist there,
  flag it (see "When something you need doesn't exist yet" below) rather than
  building a parallel one-off version inside `officer-workspace/`.
- ✅ Your write scope is `apps/officer-workspace/src/**`, plus this app's own
  `package.json`, `tsconfig.json`, `vite.config.ts` when the task genuinely
  requires a dependency or build-config change (not routinely).
- You have **no visibility into and no authority over** what the actual
  backend agents (Document, Compliance, Finance, Risk, Market, Recommendation,
  Planner) do internally. You only know their *output contract* — see below.

## What this app is (read before designing anything)

MARA AI-ETC is an agentic platform for MARA entrepreneurship officers — not a
chatbot. Officers upload documents, AI agents extract/analyze/draft, and
humans approve/correct/reject at defined gates. This app (`apps/officer-workspace/`)
is the officer-facing UI. Full context, in this order:

1. [`docs/governance/architecture-approval-report.md`](../../docs/governance/architecture-approval-report.md)
   Decision 4 — **the constraint that shapes everything you build**: this app
   shares a design system (`@openhands/ui`) and toolchain with OpenHands, but
   it is a **new application**, not a reskin of OpenHands' own coding-agent
   frontend (file tree, terminal, IDE chrome). None of that UX applies here.
   Don't borrow patterns from `frontend/` (that's OpenHands' own dev console,
   kept only as an extraction source — see its own docs, don't copy its UI).
2. [`docs/architecture/02-system-architecture.md`](../../docs/architecture/02-system-architecture.md)
   §2.2 "Workspace (UI)" — the four surfaces this app is made of: Officer
   Workspace (chat + task view), Review & Approval Console, Dashboard,
   Admin Console. Know which one you're building before you start.
3. [`docs/architecture/10-human-in-the-loop.md`](../../docs/architecture/10-human-in-the-loop.md)
   — if your task touches anything approval-related, this is the actual spec,
   not a design guess:
   - §10.4: every approval request UI must show — the agent output(s) under
     review, full provenance/citations, the confidence score and *why* it
     triggered, the specific question being asked, and one-click access to
     the source document. Never show a bare claim without the evidence next
     to it.
   - §10.5: **three actions, not two** — Approve / Reject / **Correct**.
     Correct is not the same as edit-and-approve: it's a distinct, attributed
     action (the correction is stored separately from the agent's original
     output, not merged silently into it). If you build an approval UI with
     only Approve/Reject buttons, it's wrong.
4. This app's own [`README.md`](README.md) — stack, quick start, env vars.
5. Read the existing code before adding new patterns:
   `src/services/auth.ts` (Keycloak OIDC flow via `oidc-client-ts`),
   `src/components/AuthGuard.tsx` (route-guard pattern),
   `src/App.tsx` (routing). Match these conventions — don't introduce a
   second auth pattern, a second state-management approach, etc.

## Current state (update your understanding — this changes over time)

- ✅ Built: login (Keycloak SSO redirect flow), route guard,
  authenticated workspace shell with full AppLayout (sidebar + mobile drawer
  + dark mode toggle).
- ✅ Built: **Officer Workspace** — ChatPanel with message history + file/voice
  afforances, TaskPanel with status chips + agent badges. Data fetched via
  `src/services/data.ts` (mock fallback by default).
- ✅ Built: **Dashboard** — stats grid, active workflow list, pending approvals
  + risk flag summary, agent metrics table. All data via `src/services/data.ts`.
- ✅ Built: **Review & Approval Console** — two-tab (Pending/Resolved) view,
  ApprovalCard with Approve/Reject/Correct actions, FieldPreview with
  confidence/citation/source links, CorrectionForm. 403 handling shows
  gate-role messaging. Decisions submitted via `src/services/api.ts`.
- ✅ Built: **Admin Console** — four-tab panel (Users, Roles, Agents, Settings),
  all backed by mock data via `src/services/data.ts`.
- ✅ Built: **API service layer** — `src/services/api.ts` with typed
  `createAssessment()` and `submitDecision()` calls against the live
  `POST /loans/assessments` and `POST /loans/assessments/{thread_id}/decision`
  endpoints, including 403/503 error handling.
- ✅ Built: **Unified data service** — `src/services/data.ts` wraps all data
  access with mock-first fallback (`setUseMock(true/false)` to toggle).
- ✅ **The Loan Assessment API is live.** All seven agents run behind it, with
  six approval gates.

    | | |
    |---|---|
    | `POST /loans/assessments` | multipart: `file`, `sector`, `region`, optional `compliance_requirements[]`, `product_query`, `precedent_query` |
    | `POST /loans/assessments/{thread_id}/decision` | JSON: `action` (`approve`/`reject`/`correct`), optional `reason`, `corrections[]` |

  Both return the same shape: `status` (`pending_approval` \| `completed`),
  `pending_gate`, `pending_payload`, `stage_log`, and `acted_gate` on a
  decision response.

- ✅ **Vertical-slice API v1 is now exposed (temporary in-memory store for
  wiring):**

    | | |
    |---|---|
    | `POST /api/v1/auth/register` | JSON: `full_name`, `email`, `password` |
    | `POST /api/v1/auth/login` | JSON: `email`, `password` |
    | `POST /api/v1/applications` | JSON: `applicant`, `business`, `financing`, `documents[]` |
    | `GET /api/v1/applications/{application_id}` | Full detail payload including `ai_assessment` and `workflow` |
    | `POST /api/v1/applications/{application_id}/documents` | multipart: `file`, `doc_type` |
    | `GET /api/v1/applications/{application_id}/status` | Status + `stage_log` + `updated_at` |
    | `GET /api/v1/officer/applications` | Officer queue list |
    | `POST /api/v1/officer/applications/{application_id}/decision` | JSON: `action` (`approve`/`reject`/`request_more_info`), optional `reason`, `conditions[]` |

  `ai_assessment.recommendation` now carries
  `has_acknowledged_violation` (boolean) and must be rendered.

  Local test users (dev-only seed in backend):
  `officer@mara.local` / `Officer123!`,
  `admin@mara.local` / `Admin123!Secure`.

- ⚠️ API will 503 until an OCR engine and document classifier are wired
  (`tools/ocr/README.md`). Expected current state, not a bug in your call.

## Frontend execution map (mandatory from now on)

This section is the working instruction for frontend continuation under
Phase 17 vertical-slice execution. Use this sequence exactly unless product
owner explicitly reprioritizes.

### FE-P0 - Contract lock and adapters (done, keep stable)

Build/maintain:

1. Typed API client contracts in `src/services/api.ts`.
2. Mapping layer in `src/services/data.ts` for UI-friendly models.
3. One place only for status mapping (`SUBMITTED`, `PROCESSING`,
  `UNDER_REVIEW`, `NEEDS_INFO`, `APPROVED`, `REJECTED`).

Definition of done:

1. No contract shape duplicated across multiple files.
2. No UI page calls `fetch` directly; page -> services/data -> services/api.

### FE-P1 - Officer queue vertical slice (R4) (in progress)

Build/maintain:

1. Queue list from `GET /api/v1/officer/applications`.
2. Decision actions:
  - `approve`
  - `reject`
  - `request_more_info`
3. Post-action refresh + visible status transition in UI.

Definition of done:

1. Officer can action one case end-to-end from UI only.
2. 401/403/5xx states are rendered as explicit user messages.

### FE-P2 - Applicant portal path (R2) (next priority)

Build in a dedicated applicant surface (not mixed into officer nav):

1. Register/login:
  - `POST /api/v1/auth/register`
  - `POST /api/v1/auth/login`
2. Multi-step application submit:
  - `POST /api/v1/applications`
3. Document upload after submission:
  - `POST /api/v1/applications/{application_id}/documents`
4. Status timeline/tracker:
  - `GET /api/v1/applications/{application_id}/status`

Definition of done:

1. Applicant can complete one full happy path without Postman/manual API.
2. Minimum 3 document uploads supported in one application flow.
3. Status tracker clearly shows transitions over time.

### FE-P3 - Officer case detail and evidence view (R4 continuation)

Build:

1. Case detail using `GET /api/v1/applications/{application_id}`.
2. Render extraction/compliance/finance/risk/recommendation outputs.
3. Render recommendation field `has_acknowledged_violation` explicitly.
4. Preserve human-in-the-loop context beside actions (no blind action-only UI).

Definition of done:

1. Officer can open one case and understand why recommendation is shown.
2. Decision action context is visible on the same screen.

### FE-P4 - Hardening and smoke scripts (R5)

Build:

1. Frontend smoke scripts/checklists for:
  - applicant happy path
  - officer review path
2. Error matrix coverage:
  - auth expiry
  - invalid payload/validation
  - upload failure
  - backend unavailable

Definition of done:

1. Team can re-run the same smoke path after each backend change quickly.
2. Regressions are detectable by checklist, not memory.

## How pieces connect (do not break this chain)

1. Applicant submit creates `application_id`.
2. Uploads attach to `application_id`.
3. Backend workflow updates `applications.status` and `stage_log`.
4. Officer queue consumes the same application record.
5. Officer decision updates status and may resume workflow.
6. Applicant status timeline reflects latest result.

If a UI change breaks this chain, stop and flag immediately.

## Frontend handoff artifacts required per phase

For every PR in FE-P1..FE-P4, include these artifacts in PR description:

1. API contract checklist (endpoint, request, response fields used).
2. Action-to-status transition table touched by the PR.
3. Error-state behavior summary (what user sees for 401/403/422/5xx).
4. Smoke steps (copy-paste runnable).

No artifact, no merge.

## Scope discipline (so architecture/system/agentic team can stay focused)

Frontend team owns delivery under `apps/officer-workspace/**` only.
Architecture/system/agentic team owns backend/workflow/agent internals.

When frontend is blocked by backend:

1. Open a blocker note with exact endpoint + field needed.
2. Do not implement speculative contracts.
3. Continue with mock-adapter only if mock is explicitly labeled temporary.

## Three things about the approval flow that will shape your UI

**1. The workflow tells you which gate is next — don't track it yourself.**
Every response carries `pending_gate`, one of: `confirm_extraction`,
`compliance_acknowledgment`, `financial_sign_off`, `risk_review`,
`recommendation_approval`, `publish_approval`. Route the officer from that.
Keeping your own state machine in the client will drift, and the server's
answer is the one authorization is checked against.

**2. `pending_payload` differs per gate — deliberately.** Extraction fields at
one gate, a risk rating at another. It is not flattened into a common shape
because §10.4 requires the officer see the actual evidence, and a lowest-common
denominator would drop exactly that. Render per gate.

**3. A 403 here is normal, not a bug.** Each gate has its own approver role
(§10.2). A Finance Officer opening a case paused at `risk_review` gets 403, and
the `detail` says which role is required. **Show that as "this stage needs a
Risk Officer", not as an error.** Don't hide gates the officer can't action —
they need to see where the case is waiting and on whom.

**Never send `actor` or a gate name.** The actor comes from the token and the
gate from workflow state. Both are authorization inputs, so neither is
something the client gets to assert.

## Backend contracts that are settled (build against these, not a guess)

These Python modules are the source of truth. Mirror them in
`src/types/` — do not invent a parallel shape.

| What | Contract |
|---|---|
| Document extraction | [`shared/schemas/documents.py`](../../shared/schemas/documents.py) |
| Approval decisions | [`shared/schemas/approval.py`](../../shared/schemas/approval.py) |
| Compliance checklist | [`shared/schemas/compliance.py`](../../shared/schemas/compliance.py) |
| Policy citations & retrieval | [`shared/schemas/knowledge.py`](../../shared/schemas/knowledge.py) |

### There are two different citation shapes — do not merge them

This trips people up, so it is worth being explicit. They are not
interchangeable and a single "Citation" component that handles both will be
wrong for one of them:

- **`Citation`** (`documents.py`) — points into an *applicant's uploaded
  document*: `document_id` + `page` + optional `bounding_box`. The bounding box
  is what makes §10.4's "one-click access to the underlying source document"
  land on the right region of the right page.
- **`PolicyCitation`** (`knowledge.py`) — points into the *policy corpus*:
  `document_id` + `version` + `locator` (clause/section) + `relevance` +
  `superseded_on` + `trust_tier`. There is no bounding box and no page. **The
  version is not decoration** — a compliance finding is decided against a
  specific policy version, and an officer reviewing it needs to see which. Never
  render a policy citation without its version.

### `trust_tier` on a policy citation must be visible

`PolicyCitation.trust_tier` is `approved` or `provisional`, and there is a
convenience method `is_provisional()`.

`provisional` means **no Knowledge Owner has reviewed this source**. It exists
because the Market Agent gathers findings from the open internet, and §9.7
requires that unreviewed material never reaches an officer looking like
approved corpus policy. Rendering a provisional citation the same as an
approved one defeats the whole control at the last step — the officer would be
weighing unreviewed web content believing it had been signed off.

So: **a provisional citation must be visually distinct and labeled.** Not an
error state — it is legitimate, readable evidence — but clearly marked as
unreviewed, in the same way `superseded_on` is flagged without being treated as
wrong. Wording along the lines of "source not yet reviewed by a Knowledge
Owner" is the intent.

In practice you will mostly see `approved` today: nothing in the backend writes
provisional content yet (there is no ingestion path), so the tier is a boundary
built ahead of the writer that will populate it. Build the rendering anyway —
it is far cheaper now than retrofitting it the day market-data caching lands.

### Three compliance states to render, not two

`ComplianceStatus` is `pass` / `fail` / `exception` / **`no_policy_found`**.

`no_policy_found` means the corpus was searched and nothing applicable was
found — it is an honest finding, not an error state and not a silent blank.
Render it as a distinct, visible outcome. An officer must be able to tell "we
checked and no policy applies" from "we failed to check".

Related: a retrieval can come back with `no_confident_match` set — candidates
existed but none passed the relevance threshold, with `withheld_below_threshold`
saying how many were dropped. If you surface retrieval detail anywhere, that is
a different message from "nothing in the corpus".

`RetrievalResult` carries two further counters, and they mean different things
again — do not collapse them into one "some results were hidden" line:

| Field | Meaning | What it tells the officer |
|---|---|---|
| `withheld_below_threshold` | Candidates scored too low | The corpus is weak on this question |
| `withheld_unverified` | Content exists but no Knowledge Owner has approved it | Chase the approval — this is not a gap in the corpus |
| `withheld_expired` | Cached market data aged out (90 days by default) | Nothing is wrong; a fresh search is the correct next step |

`needs_fresh_search()` is true when the result is empty *because* the cache
aged out, which is a different officer-facing message from "we found nothing".

### Stale citations

`PolicyCitation.superseded_on` is set when the cited version has since been
replaced. A finding citing a superseded policy is not necessarily *wrong* — it
may be a historical decision made while that version was in force — so do not
render it as an error. Flag it as "cited policy has since been superseded" and
let the officer judge.

## When something you need doesn't exist yet

You will frequently need something that isn't built on the backend side yet
— most importantly, the actual shape of a Document Agent extraction result
(what fields, what a citation object looks like, what a confidence score
looks like). Do not invent this contract silently and build against your own
guess — a guessed shape becomes real integration work to unwind later.

Instead:
1. Check `shared/schemas/` first — if the contract you need has been defined
   there (even as a stub/type), use it exactly as declared.
2. If it isn't defined yet, build against a **clearly-marked mock** that
   matches the *documented* requirements (10-human-in-the-loop.md §10.4's
   field list above is the minimum shape), and say explicitly in your output
   / PR description / commit message that this is a mock pending the real
   contract — don't let it look like a finished integration.
3. Flag it to the user rather than guessing silently when the shape is
   genuinely ambiguous (e.g., "does confidence come back as 0–1 or 0–100?").

## Conventions already established — follow, don't reinvent

- React 19 + TypeScript 5.9, Vite 7, React Router 7 (declarative `<Routes>`,
  not file-based routing), Tailwind CSS 4, `@openhands/ui` for all visual
  components before reaching for raw HTML/custom CSS.
- Auth: `oidc-client-ts` against Keycloak, via `src/services/auth.ts`. Never
  add a second auth library or hand-roll token handling.
- No state-management library is in place yet (React state/context only so
  far) — if a task genuinely needs one, flag it as a decision rather than
  picking one unilaterally.

## Before you finish any task

- Run `npm run typecheck` and `npm run build` — both must pass clean. If
  `npm install` fails with `ENOSPC`, it's almost certainly because the npm
  cache is pointed at a full drive on this machine, not a real problem with
  your changes — try `npm install --cache <path-on-a-drive-with-space>`
  before concluding something is broken.
- Never touch `pyproject.toml`, `uv.lock`, anything under `tests/unit/mara/`,
  or any `.py` file. If a bug you find seems to be on the backend, describe
  it and stop — do not attempt the fix yourself.
