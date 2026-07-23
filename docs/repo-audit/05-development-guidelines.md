« [Index](00-index.md) | Step 5 of 7 »

# Step 5 — Development Rules

## 5.1 Naming conventions

- **Directories:** `snake_case` for Python packages (matches existing `openhands/` convention), `kebab-case` for JS/TS packages and apps (matches existing `openhands-ui/` convention). New MARA directories follow whichever convention the sibling existing directory in that layer already uses — don't introduce a third style.
- **The four "agent" locations** (Step 3, §3.3) must always be referred to by full path, never by the bare word "agents," in commit messages, PR descriptions, and docs — e.g., "updated `agents/finance_agent/`," not "updated the agent." This is a direct mitigation for P-07/P-11, not a style preference.
- **Agent module names** match the canonical names in [../architecture/05-agent-architecture.md](../architecture/05-agent-architecture.md) exactly (`document_agent`, `compliance_agent`, etc.) — no abbreviations, no synonyms, so a search for one name reliably finds the code, the architecture doc, and the eval suite together.
- **Service module names** end in `_service` (`knowledge_service`, `approval_service`) to keep the agents-vs-services distinction (review board Part 2) visible at the filesystem level, not just in a document someone has to remember to check.

## 5.2 Branch strategy

- `main` — always deployable to staging; protected, no direct pushes.
- `feature/<area>-<short-description>` (e.g., `feature/agents-document-extraction-confidence`) — the `<area>` prefix matches a top-level directory (`agents`, `tools`, `services`, `workflows`, `infra`, `docs`) so CI can path-filter and reviewers can route by ownership (§5.4).
- `fix/<area>-<short-description>` for bug fixes.
- No long-lived per-developer or per-milestone branches — the roadmap's milestone staging ([../architecture/14-roadmap.md](../architecture/14-roadmap.md)) is a delivery sequence, not a branching model; each milestone's work still lands as many small, independently-reviewed PRs against `main`.
- Upstream OpenHands sync happens on its own `sync/upstream-<date>` branch, reviewed like any other PR, never merged directly by automation without a human diff review — this is the practical enforcement mechanism for Step 6's protection rules.

## 5.3 Commit conventions

Conventional Commits (`type(scope): description`), where `scope` matches the top-level directory touched — e.g., `feat(agents): add compliance agent hard-violation escalation`, `fix(tools): correct OCR timeout default`, `docs(architecture): resolve documentation/ vs docs/ naming`. Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `security` (a distinct type, not folded into `fix`, so security-relevant commits are `git log --grep`-discoverable on their own — directly useful for the audit-trail culture this whole platform is built around).

## 5.4 Code ownership

| Path | Owning team | Review requirement |
|---|---|---|
| `openhands/`, `frontend/` (existing routes), `containers/`, `kind/` | Platform team | Any change requires a Platform reviewer, specifically because these are the upstream-protected paths (Step 6) |
| `agents/` | Agents team | Agents reviewer + at least one eval-suite (`tests/agent_evals/`) result attached to the PR |
| `tools/` | Tools team | Tools reviewer + explicit sign-off that the tool catalogue entry in [../architecture/06-tool-architecture.md](../architecture/06-tool-architecture.md) is updated in the same PR |
| `services/`, `workflows/` | Platform/Workflows team | Platform reviewer; any change to an approval-gate workflow additionally requires a Compliance Officer sign-off comment on the PR, mirroring [../architecture/10-human-in-the-loop.md](../architecture/10-human-in-the-loop.md)'s human-approval principle applied to the code that implements it |
| `apps/officer-workspace/`, `packages/*` | Frontend team | Frontend reviewer |
| `infrastructure/`, `configs/` | DevOps team | DevOps reviewer; production `configs/production/` changes require a second approver, no exceptions |
| `docs/` | Whoever owns the content area (architecture docs → whoever proposed the change; runbooks → DevOps; policy → Compliance) | At least one reviewer, same bar as code — stale docs are a defect, not a lesser artifact |

## 5.5 Documentation rules

- Every new `agents/*`, `tools/*`, `services/*`, `workflows/*` module ships with a `README.md` stating its purpose and linking to the exact architecture-plan section it implements (e.g., `agents/finance_agent/README.md` links to [../architecture/05-agent-architecture.md#56-finance-agent](../architecture/05-agent-architecture.md)). Code without a documented tie-back to the architecture plan is how documentation and implementation drift apart — this rule exists specifically to prevent that.
- Any deviation from the architecture plan or the review board's required changes discovered during implementation gets logged as an update to the relevant `docs/architecture/*` file in the *same PR* as the code change, not as a follow-up ticket that may or may not happen.
- `docs/repo-audit/` (this document set) is a point-in-time audit, not a living document — if the repository structure changes again materially, write a new dated audit rather than editing this one in place, so the history of "what did we decide and when" stays intact (this mirrors the immutability principle the architecture plan itself applies to Audit Memory, [../architecture/08-memory-architecture.md](../architecture/08-memory-architecture.md), applied here to engineering decisions).

## 5.6 Where new things live

- **New agent** → `agents/<name>_agent/`, only if it passes the review board's test (Part 2 of the review): does it make a genuinely ambiguous judgment call, or does it transform already-decided input deterministically? The latter goes in `services/`.
- **New tool** → `tools/<category>/`, or `tools/mcp_servers/<name>/` if it's better isolated as a standalone MCP server (preferred for anything with its own runtime dependencies, per [../architecture/06-tool-architecture.md](../architecture/06-tool-architecture.md) §6.5).
- **New workflow** → `workflows/<name>/`, defined as a bounded LangGraph template per the review board's Finding A1 — never as free-form runtime-constructed graph topology.
- **New shared library code** (used by 2+ of agents/tools/services/workflows) → `shared/`, following the dependency rule already established in [../architecture/03-repository-structure.md](../architecture/03-repository-structure.md) §3.3 (shared depends on nothing else in the repo).
- **New frontend-shared code** (used by both `apps/officer-workspace/` and, if still relevant, `frontend/`) → `packages/`.
