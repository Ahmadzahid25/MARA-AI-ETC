« [Index](00-index.md) | Step 6 of 7 »

# Step 6 — OpenHands Protection Rules

## 6.1 Must not be modified directly

| Path | Rule | Reason |
|---|---|---|
| `openhands/app_server/**` | No direct edits to existing files. Extend only via new sub-packages registered into it (e.g., a new `openhands/app_server/mara_tools/` module registered through the existing MCP host, not a modified `mcp/` internals file) | This is the actively-developed upstream V1 surface (Step 1) — direct edits here are exactly what turns every future `git pull upstream main` into a manual conflict-resolution exercise, precisely the failure mode the architecture review warned against (review board Part 1 §2.4) |
| `openhands/server/**` (legacy V0) | Read-only. Do not extend, do not fix bugs in it for MARA's benefit | It is legacy even from upstream's own perspective; investing MARA engineering time into it is effort spent on a component upstream itself is likely to remove |
| `frontend/src/**` (existing routes/components) | No direct edits to existing screens | Not the product surface (Step 3) — new UI work happens in `apps/officer-workspace/`; the only sanctioned interaction with `frontend/src` is *reading* it to perform the one-time extraction into `packages/event-stream-client/` (Step 4, Phase 3) |
| `containers/**`, `kind/**`, root `docker-compose.yml` | No direct edits | These are OpenHands' own deployment definitions; MARA's equivalents live in `infrastructure/` and compose *with* these files, they don't replace or alter them |
| `pyproject.toml` (root), `Makefile`, `build.sh` | Additive edits only (new optional dependency groups, new Makefile targets) — never remove or restructure existing targets/dependencies that upstream OpenHands relies on | These are the build contract upstream's own CI and contributors expect; breaking them breaks the ability to verify "did we actually not break OpenHands functionality" (the Step 4, Phase 5 validation gate depends on this contract staying intact) |

## 6.2 Should be extended (not replaced)

| Path | Extension pattern |
|---|---|
| `openhands/app_server/mcp/` | New MARA tools register as new MCP servers under `tools/mcp_servers/`, discovered through this existing host — do not build a second, parallel tool-registration mechanism |
| `openhands/app_server/secrets/` | MARA's Vault/Secrets Manager integration ([../architecture/11-security-architecture.md](../architecture/11-security-architecture.md) §11.3) plugs into this existing secrets API surface, rather than agents/services reading secrets through a second, independent path |
| `openhands/app_server/user_auth/` | Keycloak federation ([../architecture/04-technology-stack.md](../architecture/04-technology-stack.md) §4.4) extends this module's existing auth flow; RBAC/ABAC policy evaluation ([../architecture/11-security-architecture.md](../architecture/11-security-architecture.md) §11.2) is new code in `shared/auth/` that this module calls into, not a fork of it |
| `openhands/app_server/event/`, `event_callback/` | The Agent Runtime ([../architecture/02-system-architecture.md](../architecture/02-system-architecture.md) Layer 4) is a consumer/configuration of this event stream, not a reimplementation of it |
| `config.template.toml` | New MARA config keys are added to this template (with sensible defaults), not moved into a separate, parallel config file that a deployer now has to remember also exists |

## 6.3 Should be wrapped, not touched at all

| Path | Wrapping pattern |
|---|---|
| `openhands/app_server/sandbox/` | Treated as an opaque execution primitive. MARA's Tool Runtime permission model ([../architecture/06-tool-architecture.md](../architecture/06-tool-architecture.md)) is enforced in a layer *in front of* sandbox dispatch (deciding whether a call reaches the sandbox at all), never by modifying what the sandbox itself is capable of executing — this is also the direct implementation of the review board's Part 1 §2.3 finding that MARA's security posture should be addition-based, layered on top, not subtraction-based edits to a general-purpose execution primitive |
| `openhands/analytics/` | Left fully alone. MARA's own cost/usage tracking ([../architecture/12-observability.md](../architecture/12-observability.md) §12.7–12.8) is new code in `services/` and `shared/telemetry/`, entirely separate from OpenHands' own product-usage analytics, which serves a different purpose (OpenHands' own telemetry, not MARA's operational cost tracking) and should not be repurposed or conflated |

## 6.4 Should remain upstream-compatible

The test for "is this compatible": **can `git fetch upstream && git merge upstream/main` be attempted at any time without first reverting MARA-specific work?** If the honest answer for a given file is no, that file has drifted from a protected/extend/wrap path into a fork-with-local-modifications path, and that drift should be a deliberate, documented, reviewed decision — never an accretion nobody decided on purpose.

- `openhands/`, `frontend/` (existing files), `containers/`, `kind/`, root `docker-compose.yml`, `tests/unit/{app_server,server,storage,mcp,integrations}/` (existing files): must remain mergeable against upstream at all times.
- New MARA-only paths (`agents/`, `tools/`, `services/`, `workflows/`, `apps/officer-workspace/`, `docs/`, `configs/`, `infrastructure/`) have no upstream equivalent and carry no merge-compatibility obligation — they are pure MARA additions.
- `packages/event-stream-client/` is the one deliberately-accepted exception: it is an extraction *from* upstream code, meaning it will *not* automatically pick up future upstream changes to `frontend/src`'s event-stream logic. This is a known, accepted tradeoff (Step 4, Phase 3) — resolve it operationally by periodically diffing `frontend/src`'s relevant modules against the extracted package during scheduled upstream-sync branches (§5.2), not by pretending the extraction stays automatically in sync.

## 6.5 Upgrade strategy

1. **Cadence:** upstream OpenHands sync is a scheduled, deliberate activity (e.g., monthly, or triggered by a security advisory) — not continuous auto-merge. A `sync/upstream-<date>` branch (§5.2) is created, `git merge upstream/main` attempted, conflicts (expected to be rare, confined to the protected paths in §6.1 if this plan is followed) resolved by a Platform reviewer, and the full validation suite (Step 4, Phase 5) run before merging to `main`.
2. **Security patches specifically** are fast-tracked outside the normal cadence — a security advisory affecting `openhands/app_server/sandbox/` or `user_auth/` triggers an immediate sync attempt, reviewed same-day, given the sandbox's role as the highest-exposure surface in the system (per the architecture plan's own risk register, [../architecture/15-risk-assessment.md](../architecture/15-risk-assessment.md) R-S1/R-S3 territory).
3. **Breaking upstream changes** (e.g., `app_server`'s API shape changes materially) are handled by pinning the last-known-good upstream commit, opening a tracked issue, and scheduling the adaptation work explicitly — never by silently staying stuck on an old commit indefinitely with no record of why.
4. **`packages/openhands-ui/`**, since it's the one moved directory, gets its upstream-diff check folded into the same sync cadence: confirm the moved package still matches upstream's version of the same component library closely enough to be worth periodically re-syncing, or make an explicit, recorded decision to diverge if MARA's design-system needs pull it away from upstream's.
