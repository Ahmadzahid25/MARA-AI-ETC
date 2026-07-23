# Officer Workspace application

**Scaffolded in Milestone 0 (Foundation).** This is the empty-shell authenticated workspace for MARA officers — a React SPA consuming `@openhands/ui` (the shared design system) and the API Gateway.

## Stack

- **Framework**: React 19 + TypeScript 5.9
- **Bundler**: Vite 7
- **Routing**: React Router 7 (file-route-free, declarative `<Routes>`)
- **Styling**: Tailwind CSS 4
- **Design system**: `@openhands/ui` (`packages/openhands-ui/`)
- **Auth**: Keycloak SSO via `oidc-client-ts`
- **API Gateway**: `http://localhost:8000` (proxied via Vite in dev)

## Quick start

```bash
# From repo root
cd apps/officer-workspace
npm install
npm run dev
```

Opens at `http://localhost:4000`. Routes unauthenticated users to `/login`, which redirects to Keycloak SSO.

## Dev config (environment variables)

| Variable | Default | Purpose |
|---|---|---|
| `VITE_KEYCLOAK_URL` | `http://localhost:8080` | Keycloak server base URL |
| `VITE_KEYCLOAK_REALM` | `mara-ai-etc` | Keycloak realm name |
| `VITE_KEYCLOAK_CLIENT_ID` | `mara-officer-workspace` | OIDC client ID (match compose init) |
| `VITE_API_GATEWAY_URL` | `http://localhost:8000` | Gateway base URL |

## What's here (Milestone 0 scope)

| File | Purpose |
|---|---|
| `src/main.tsx` | App entry point with BrowserRouter |
| `src/App.tsx` | Route definitions (login + authenticated workspace) |
| `src/index.css` | Tailwind CSS v4 entry |
| `src/pages/LoginPage.tsx` | SSO login screen with Keycloak redirect |
| `src/pages/WorkspacePage.tsx` | Empty authenticated workspace dashboard |
| `src/components/AuthGuard.tsx` | Route guard checking Keycloak session |
| `src/services/auth.ts` | OIDC client wrapper (login, logout, getUser, getAccessToken) |

## What's NOT here (blockers)

- **`packages/event-stream-client/`** — does not exist yet. Needs extraction from `frontend/src` WebSocket/event-stream handling code per `docs/repo-audit/04-migration-plan.md` Phase 3. The workspace currently has no event-stream integration; this is expected for Milestone 0.

## Architecture decisions

Per `docs/governance/architecture-approval-report.md` Decision 4: **same framework/toolchain and same design system (`openhands-ui/`), new application (`apps/officer-workspace/`)** — one design language, two apps, not one framework forked into two incompatible UIs.

See `docs/architecture/02-system-architecture.md` §2.2 for the full layer specification.
