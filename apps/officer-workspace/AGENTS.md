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

- ✅ Built: login (Keycloak SSO redirect flow), route guard, empty
  authenticated workspace shell.
- ❌ Not built yet: Officer Workspace chat/task view, Review & Approval
  Console, Dashboard, Admin Console.
- ⚠️ Backend agents exist but are **not yet exposed over an API you can call**.
  Document Agent and Compliance Agent are implemented; the Gateway routes for
  them are not complete. Keep building against the mocks — but build against
  the *real* contracts below, which are now settled, not against a guess.

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
  `superseded_on`. There is no bounding box and no page. **The version is not
  decoration** — a compliance finding is decided against a specific policy
  version, and an officer reviewing it needs to see which. Never render a policy
  citation without its version.

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
