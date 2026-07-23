« [Index](00-index.md) | Step 3 of 7 »

# Step 3 — Target Repository Structure

## 3.1 Where this diverges from the original architecture plan, and from the example in this prompt, and why

Two prior documents already proposed a structure and both need correcting against what Step 1's actual inventory found:

- The original master plan's [../architecture/03-repository-structure.md](../architecture/03-repository-structure.md) used a top-level `documentation/` — reconciled here to `docs/`, which already exists and is already populated (Problem P-10). No functional difference intended; this is the audit overriding the earlier document on a naming collision it didn't know about at the time it was written.
- This prompt's example structure (`apps/`, `core/openhands/`, `packages/`, etc.) nests the entire OpenHands codebase under `core/openhands/`. **This board does not adopt that nesting**, and the reason is Step 6's own mandate: moving `openhands/`, `frontend/`, `containers/`, `kind/`, `tests/`, or `scripts/` from their current root locations breaks every existing path reference in the Makefile, CI workflows, Dockerfiles, and `pyproject.toml`, and — far more importantly — turns every future upstream OpenHands merge into a manual path-remapping exercise instead of a normal `git merge`. Relocating code you intend to keep merging from upstream is the single most common way forks silently become unmaintainable. The only relocation this plan makes is `openhands-ui/` → `packages/openhands-ui/`, and only because it is already a self-contained, independently-tooled package (Step 1) where the blast radius of a path change is limited to its own internal config and whatever explicitly imports it — nothing does yet.

## 3.2 Target tree

```
MARA-AI-ETC/                        (repository root — currently "MARA AI-ETC/")

├── openhands/                      # [UNCHANGED LOCATION — protected, see Step 6]
│   ├── app_server/                   # integration target (OpenHands "V1") — extended via new mara_* submodules
│   │                                  # registered into it, never edited in place
│   ├── server/                       # legacy "V0" — read-only reference; do not build new MARA code against it
│   ├── db/
│   └── analytics/
│
├── frontend/                       # [UNCHANGED LOCATION — protected] OpenHands' own dev-console UI.
│                                    # Kept as-is; it is the source packages/event-stream-client is extracted
│                                    # from, and remains useful for internal/dev debugging of the runtime.
│                                    # NOT reskinned into the officer product — see apps/officer-workspace/.
│
├── containers/                     # [UNCHANGED LOCATION — protected] OpenHands' own app/dev container images.
├── kind/                           # [UNCHANGED LOCATION — protected] OpenHands' own local-Kubernetes config.
├── docker-compose.yml              # [UNCHANGED LOCATION — protected] OpenHands' own base local-dev compose file.
├── tests/                          # [UNCHANGED LOCATION] extended in place — see 3.4.
├── scripts/                        # [UNCHANGED LOCATION] extended in place — see 3.4.
│
├── apps/                           # [NEW]
│   └── officer-workspace/            # purpose-built MARA officer frontend (architecture plan §2, Workspace
│                                      # layer). Consumes packages/event-stream-client and packages/openhands-ui.
│                                      # This is genuinely new code, not a fork of frontend/'s existing routes.
│
├── packages/                       # [NEW] shared, independently-versionable libraries
│   ├── openhands-ui/                  # ← MOVED from root (Step 4) — design-system/component base, unchanged
│   │                                    internally. Reused rather than rebuilt (Problem P-02 from Step 2).
│   └── event-stream-client/           # extracted from frontend/src's event-stream/WebSocket client logic —
│                                        the one part of the existing frontend genuinely worth reusing per the
│                                        architecture review (../architecture/review/01-*.md §2.1–2.5). Consumed
│                                        by both apps/officer-workspace/ and, optionally, frontend/ itself.
│
├── agents/                         # [NEW] MARA domain agent definitions — see naming note, §3.3
│   ├── planner/
│   ├── document_agent/
│   ├── compliance_agent/
│   ├── finance_agent/
│   ├── risk_agent/
│   ├── market_agent/
│   ├── recommendation_agent/
│   └── shared/                       # base agent class, prompt templates, confidence-scoring helpers
│   # NOTE: per the review board (../architecture/review/02-*.md §4), Supervisor, Report, Presentation, Voice,
│   # and (mostly) Audit are NOT full agents — they belong under services/, not here. Do not create
│   # agents/supervisor/, agents/report_agent/, etc.
│
├── tools/                          # [NEW] per architecture plan Phase 6 — OCR, documents, search, rag,
│   │                                  database, calculations, mcp_servers/
│   └── ...
│
├── services/                       # [NEW] per architecture plan Phase 3/7, INCLUDING the reclassified
│   ├── planner_service/               components from the review board:
│   ├── supervisor_service/            # workflow-engine control logic (NOT an LLM agent — review board Part 2)
│   ├── publishing_service/            # merged Report + Presentation rendering (review board §4.1) — templating,
│   │                                    not agentic reasoning
│   ├── voice_service/                 # TTS/STT tool wrappers (NOT an agent — review board Part 2)
│   ├── audit_service/                 # structured audit query API; narrative summarization is a thin add-on
│   │                                    layer on top of this, not a separate full agent
│   ├── memory_service/
│   ├── knowledge_service/             # Dify-backed, own database instance (review board Finding C2 — see
│   │                                    Step 6 for the explicit note that this is NOT the same Postgres
│   │                                    instance as the platform's primary one)
│   ├── approval_service/
│   └── notification_service/
│
├── workflows/                      # [NEW] LangGraph graph definitions, per architecture plan Phase 7 —
│   └── ...                            constrained to bounded template selection per the review board (Part 1,
│                                       Finding A1) — the Planner parameterizes these, it does not generate them
│
├── shared/                         # [NEW] cross-cutting contracts/infra — schemas, auth, telemetry, llm, config
│
├── infrastructure/                 # [NEW] MARA-specific deployment definitions — additive alongside, not a
│   ├── docker/                        replacement for, containers/ and kind/ above
│   ├── k8s/
│   ├── terraform/
│   └── compose/                      # MARA overlay compose files, composed with root docker-compose.yml via
│                                        `-f docker-compose.yml -f infrastructure/compose/mara.yml`
│
├── docs/                           # [KEPT, now canonical — resolves P-10]
│   ├── architecture/                  # already exists — master plan + review board report
│   ├── repo-audit/                    # this document set
│   ├── governance/                    # [NEW] ACCB approval reports and future gate decisions
│   ├── security/                      # [NEW] threat models, red-team records, third-party assessment reports
│   ├── deployment/                    # [NEW] deployment guides and operational runbooks (supersedes the
│   │                                    originally-proposed "runbooks/" name — merged per ACCB Decision 3,
│   │                                    see [../governance/architecture-approval-report.md](../governance/architecture-approval-report.md))
│   ├── api/                           # [NEW] target for pydoc-markdown output — see Step 4 for the CNAME fix
│   └── policy/                        # [NEW] PDPA / compliance documentation
│
├── configs/                        # [NEW] resolves P-12
│   ├── dev/
│   ├── staging/
│   └── production/
│
├── (removed) enterprise/           # P-01 — see Step 4 for the removal procedure
├── (removed) .release-please-manifest.cloud.json, release-please-config.cloud.json   # part of P-01
│
└── [all other root files — Makefile, pyproject.toml, uv.lock/poetry.lock (see Step 4 re: P-08),
     config.template.toml, .github/, etc. — UNCHANGED LOCATION, see Step 1/6]
```

## 3.3 Naming disambiguation (resolves P-07, P-11)

Four things now share the word "agent" or "skill" in this repository. This table is the canonical disambiguation, and should be pasted into `AGENTS.md` or `docs/repo-audit/` verbatim so it's discoverable:

| Path | What it actually is | Who edits it |
|---|---|---|
| `.openhands/microagents/` | OpenHands *product* feature — runtime microagent behavior for the coding assistant itself | Platform team, rarely |
| `skills/` (root) | OpenHands' own general coding-assistant skill library | Platform team, synced loosely with upstream |
| `.agents/skills/` | This-repo-specific coding-assistant instructions (release process, cross-repo testing) | Whoever owns repo/release tooling |
| `agents/` (new) | **MARA's domain agents** (Document, Compliance, Finance, Risk, Market, Recommendation, Planner) — the actual product | Agents team |

## 3.4 What "extended in place" means for `tests/` and `scripts/`

`tests/unit/` already mirrors `openhands/` and (soon-removed) `enterprise/`'s module layout. New MARA test categories are added as siblings: `tests/unit/agents/`, `tests/integration/`, `tests/e2e/`, `tests/agent_evals/` — matching the existing convention rather than introducing a second one. Same principle for `scripts/`: MARA operational scripts (migrations, seed data, load tests) are added as new files in the existing `scripts/` directory, not a parallel `scripts-mara/`.
