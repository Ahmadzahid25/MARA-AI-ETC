# Officer Workspace application

**Scaffolded in Milestone 0 (Foundation).** This is the authenticated workspace for MARA officers — a React SPA consuming `@openhands/ui` (the shared design system) and the API Gateway.

## Stack

- **Framework**: React 19 + TypeScript 5.9
- **Bundler**: Vite 7
- **Routing**: React Router 7 (file-route-free, declarative `<Routes>`)
- **Styling**: Tailwind CSS 4
- **Design system**: `@openhands/ui` (`packages/openhands-ui/`)
- **Auth**: Keycloak SSO via `oidc-client-ts` (Authorization Code + PKCE)
- **API Gateway**: `http://localhost:8051` (proxied via Vite in dev)

---

## Quick start — Dev Mode (tanpa Keycloak)

Untuk pembangunan lokal tanpa Docker / Keycloak:

```bash
cd apps/officer-workspace
npm install
npm run dev
```

Buka `http://localhost:4000`. Klik **"Log Masuk Pegawai (Mod Pembangunan / Mock)"** untuk bypass Keycloak dengan sesi palsu.

---

## Quick start — Keycloak SSO penuh

### 1. Start Keycloak via Docker

```bash
# Dari root repo
docker compose -f docker-compose.yml \
               -f infrastructure/compose/docker-compose.mara.yml \
               up keycloak -d
```

### 2. Tunggu Keycloak ready (~30–60 saat)

```bash
# Semak health status
docker logs mara-keycloak --follow

# Atau curl health endpoint
curl -sf http://localhost:8080/health/ready && echo "Keycloak ready!"
```

### 3. Verify realm import

Buka `http://localhost:8080` → Log masuk Admin Console dengan:
- **Username**: `admin`
- **Password**: `admin-dev-only`

Pergi ke **Realm: mara-ai-etc** → Pastikan realm wujud dan users nampak.

### 4. Set environment variables

```bash
cp .env.example .env.local
# Nilai default sudah betul untuk Docker stack lokal
```

### 5. Run frontend

```bash
npm run dev
```

Klik **"Sign in with SSO (Keycloak Server)"** → Login dengan test user di bawah.

---

## Test Users (auto-import dari realm JSON)

| Username | Password | Role |
|---|---|---|
| `pegawai.usahawan` | `Password123!` | `entrepreneurship_officer` |
| `pegawai.pematuhan` | `Password123!` | `compliance_officer` |
| `pegawai.kewangan` | `Password123!` | `finance_officer` |
| `pengurus.cawangan` | `Password123!` | `branch_manager` |
| `juruaudit` | `Password123!` | `auditor` |
| `admin.mara` | `Admin@2026!` | `administrator` + `auditor` |

---

## Dev config (environment variables)

| Variable | Default | Purpose |
|---|---|---|
| `VITE_KEYCLOAK_URL` | `http://localhost:8080` | Keycloak server base URL |
| `VITE_KEYCLOAK_REALM` | `mara-ai-etc` | Keycloak realm name |
| `VITE_KEYCLOAK_CLIENT_ID` | `mara-officer-workspace` | OIDC client ID (match realm JSON) |

Salin `.env.example` ke `.env.local` dan ubah jika perlu.

---

## OIDC Flow

```
1. Officer klik "Sign in with SSO"
2. Browser redirect → Keycloak login page (localhost:8080)
3. Officer masukkan credentials
4. Keycloak redirect → http://localhost:4000/callback?code=…&state=…
5. CallbackPage.tsx exchange code → JWT tokens
6. Navigate ke "/" (WorkspacePage)
7. AuthGuard semak token untuk setiap protected route
8. oidc-client-ts auto-renew token (silent refresh)
```

---

## Fail-fail utama

| Fail | Tujuan |
|---|---|
| `src/main.tsx` | App entry point dengan BrowserRouter |
| `src/App.tsx` | Route definitions (login, callback, protected pages) |
| `src/pages/LoginPage.tsx` | SSO login screen |
| `src/pages/CallbackPage.tsx` | OIDC redirect callback handler |
| `src/pages/WorkspacePage.tsx` | Workspace dashboard (authenticated) |
| `src/components/AuthGuard.tsx` | Route guard — semak Keycloak session |
| `src/services/auth.ts` | OIDC wrapper: login, logout, getUser, getAccessToken, getUserProfile |
| `src/services/dev-auth.ts` | Dev mode mock session (dev build sahaja) |

---

## Apa yang belum ada (blockers)

- **`packages/event-stream-client/`** — belum wujud. Perlu extraction dari `frontend/src` WebSocket/event-stream code per `docs/repo-audit/04-migration-plan.md` Phase 3.
- **Corporate IDP Federation** — Keycloak belum disambung ke MARA corporate Active Directory/SAML. Diperlukan untuk production.
- **Production Keycloak** — Compose sekarang guna `KC_DB: dev-file`. Production perlu Postgres tersendiri untuk Keycloak.

---

## Architecture decisions

Per `docs/governance/architecture-approval-report.md` Decision 4: **same framework/toolchain and same design system (`openhands-ui/`), new application (`apps/officer-workspace/`)** — one design language, two apps, not one framework forked into two incompatible UIs.

See `docs/architecture/02-system-architecture.md` §2.2 for the full layer specification.



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
