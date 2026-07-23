« [Index](00-INDEX.md) | Phase 6 of 16 »

# Phase 6 — Tool Architecture

> **v1.0 note:** this phase now specifies two controls added per ACCB Mandatory Changes 1–2 and Review Board Findings A2/B3 ([review/03-data-and-security-review.md](review/03-data-and-security-review.md)): deterministic citation verification (§6.1) and mandatory query sanitization on the web/external search tool (§6.2, §6.6). Tool permission references to "Report Agent"/"Presentation Agent"/"Voice Agent"/"Audit Agent" are updated to their reclassified service names per [05-agent-architecture.md](05-agent-architecture.md) §5.11.

## 6.1 Common tool contract

Every tool is registered with the Tool Runtime ([02-system-architecture.md](02-system-architecture.md)) through one interface, whether it runs in-process, as a sandboxed subprocess, or as an external MCP server. Every tool declares, and the Tool Runtime enforces:

- **Input schema** — typed, validated (Pydantic) before execution; malformed input is rejected before it reaches the tool implementation.
- **Output schema** — typed, including a mandatory `confidence` field where applicable and a `source` provenance field.
- **Permissions** — which agent roles may invoke it (see the allow-lists in [05-agent-architecture.md](05-agent-architecture.md)); enforced at the Tool Runtime, not just at the agent's prompt level, so a prompt-injected agent still cannot call a tool it isn't granted.
- **Error handling** — a typed error taxonomy (`InputError`, `TimeoutError`, `ExternalServiceError`, `PermissionError`) rather than raw exceptions leaking to the agent; agents reason over typed errors, not stack traces.
- **Timeout** — a per-tool default, overridable per workflow, enforced by the Tool Runtime regardless of whether the tool implementation respects it internally.
- **Retries** — idempotent tools get automatic retry with backoff on `TimeoutError`/`ExternalServiceError`; non-idempotent tools (e.g., email send) are never auto-retried without explicit dedup/idempotency-key handling.
- **Logging** — every invocation logged with agent ID, workflow ID, input hash, output hash, latency, and outcome, written to Audit Memory ([08-memory-architecture.md](08-memory-architecture.md)) before the result is returned to the agent — so a tool call is audit-recorded even if the agent's own subsequent reasoning crashes.
- **Citation verification** *(added in v1.0)* — for any tool whose output an agent may cite as provenance (RAG/knowledge query, structured database query, web/external search), the Tool Runtime records the exact set of returned document/chunk/record IDs for that task. Before an agent's output reaches a human, every citation in its provenance block is checked against that recorded set; a citation referencing an ID that was never actually returned is rejected and flagged, not passed through on the strength of being well-formed. This closes Review Board Finding A2 ([review/01-architecture-and-foundation-review.md](review/01-architecture-and-foundation-review.md) §1.2): schema validation alone confirms a citation-shaped string exists, not that it's real — an LLM fabricating a plausible but wrong citation is a materially more dangerous failure mode than omitting one, because it reads as more trustworthy to a reviewing officer.

## 6.2 Tool catalogue

| Tool | Input | Output | Permissions | Timeout | Retries | Notes |
|---|---|---|---|---|---|---|
| **OCR** | Image/scanned PDF page, language hint | Extracted text + per-region confidence + bounding boxes | Document Agent only | 30s/page | 2, exponential backoff | Self-hosted PaddleOCR/Tesseract default; cloud OCR path requires document sensitivity = "non-sensitive" flag (Phase 11) |
| **PDF parse** | PDF file | Structured text/tables/metadata | Document Agent | 15s | 2 | Native text-layer extraction before falling back to OCR |
| **Word generation** | Structured content + template ref | .docx artifact | `services/publishing_service` | 20s | 1 (non-idempotent output artifact — retried by regenerating, not appending) | python-docx |
| **Excel generation** | Structured tabular data + template ref | .xlsx artifact | Finance Agent (data), `services/publishing_service` (assembly) | 20s | 1 | openpyxl |
| **PowerPoint generation** | Approved report content + template ref | .pptx artifact | `services/publishing_service` only | 30s | 1 | python-pptx |
| **Audio TTS** | Text + voice/language config | Audio artifact + duration | `services/voice_service` only | 60s | 2 | Self-hosted default; cloud opt-in gated by sensitivity flag |
| **Audio STT** | Audio file | Transcript + confidence | `services/voice_service` only | 60s | 1 | Whisper self-hosted |
| **Web/external search** | Sanitized query (PII stripped/generalized before this tool is even called — see §6.6), domain allow-list ref | Ranked results with URL/snippet/retrieved-date | Market Agent only | 15s | 2 | The only tool with outbound internet access; network-policy-enforced at the infrastructure level to the Market Agent's pod specifically; every call logged with full (sanitized) query text |
| **RAG / knowledge query** | Query, corpus/collection ref, top-k | Ranked chunks with source doc ID, page, and similarity score | All 7 agents, plus `services/publishing_service` (report/deck template and formatting standards) | 10s | 2 | Calls `services/knowledge_service` (Dify-backed, on its own database instance — Phase 9). Audit Service queries Audit Memory directly, not this tool. |
| **Structured database query** | Parameterized query (never raw SQL from agent output) | Rows/records | Compliance, Finance, Risk agents | 10s | 2 | Query templates are pre-defined and parameterized server-side to close the SQL-injection-via-prompt-injection path — see [11-security-architecture.md](11-security-architecture.md) |
| **Email/notification send** | Recipient, template, content refs | Delivery status | `services/notification_service` only, invoked via workflow approval gate, never directly by an agent | 10s | 0 (non-idempotent; failure surfaces to `services/supervisor_service` for explicit human-directed retry) | No agent has direct email-send permission — this is deliberate, see 6.3 |
| **Calculation (finance/risk formulas)** | Named formula ID + typed numeric inputs | Numeric result + formula version used | Finance, Risk agents | 2s | 1 | Deterministic, versioned formula library — never LLM-computed arithmetic for a figure that informs a decision |
| **Document classification** | Document file | Document type label + confidence | Document Agent | 10s | 2 | Feeds routing decisions in the Document Assessment workflow |
| **MCP-hosted external tools** | Per-server schema | Per-server schema | Declared per workflow, reviewed before enabling | Per-server default | Per-server policy | Extension point (`app_server/mcp`) for adding new tools without core redeploy — every new MCP server goes through the same permission/audit registration as built-in tools, no bypass |

## 6.3 Why no agent has direct email/external-transmission permission

This is a deliberate architectural choke point, not an oversight: [01-vision.md](01-vision.md)'s success criterion of "zero incidents of an agent taking an irreversible external action without a passed human-approval gate" is only mechanically guaranteed if the *capability* to transmit externally doesn't exist inside any agent's tool grant. The email/notification tool is only invocable by the platform's Notification Service, itself only triggered by a completed Human Approval gate ([10-human-in-the-loop.md](10-human-in-the-loop.md)). An agent cannot "decide" to send an email; it can only produce a draft that a human approval action subsequently causes to be sent.

## 6.4 Tool Runtime enforcement details

- **Sandboxing**: tools that execute code or process untrusted file content (OCR, PDF parsing, document classification) run inside the OpenHands sandbox (`app_server/sandbox`), isolated from the host and from other agents' concurrent tool calls.
- **Rate/budget limiting**: each workflow instance carries a tool-call budget (count and estimated LLM/API cost) set by the Supervisor at plan time; a tool call that would exceed the budget is rejected with a typed `BudgetExceededError`, escalated to a human rather than silently throttled.
- **Idempotency**: tools that produce artifacts (documents, decks, audio) are treated as idempotent-by-regeneration — a retry regenerates the artifact from the same validated input rather than assuming partial output state, which avoids corrupt half-written files being treated as valid.
- **Schema versioning**: tool input/output schemas are versioned; a workflow checkpointed mid-execution against schema v1 that resumes after a tool upgrade to v2 is handled by the Workflow Engine's schema-migration policy (Phase 7), not by the tool silently accepting both shapes.

## 6.5 Adding a new tool

New tools are added as MCP servers registered in `tools/mcp_servers/` (see [03-repository-structure.md](03-repository-structure.md)) wherever practical, rather than as bespoke in-process integrations — this keeps the core Tool Runtime stable and makes new tools independently deployable and independently permissioned. A new tool requires, before it can be granted to any agent: a completed entry in this catalogue (input/output schema, permissions, timeout, retry policy), a security review of its permission scope (Phase 11), and at least one automated eval case in `tests/agent_evals/` exercising an agent that uses it.

## 6.6 Query sanitization on the web/external search tool (added in v1.0 — ACCB Mandatory Change 1)

The Market Agent is the platform's sole external-egress path ([05-agent-architecture.md](05-agent-architecture.md) §5.7), and that restriction defends against every *other* component leaking data externally — it does nothing to constrain what the Market Agent's own queries contain. Per Review Board Finding B3 ([review/02-agent-and-tool-review.md](review/02-agent-and-tool-review.md) §5.3) and ACCB Mandatory Change 1 ([governance/architecture-approval-report.md](../governance/architecture-approval-report.md) §4), the **web/external search tool itself** — not the calling agent's prompt discipline — enforces:

- **Query sanitization**: incoming query text is checked against a PII-pattern/entity-detection pass (applicant names, IC numbers, business registration numbers, exact addresses) before the tool constructs an outbound request; matches are generalized to sector/industry/region terms or the call is rejected with a typed `InputError` if it cannot be safely generalized. This is enforced programmatically at the tool boundary, verified in `tests/agent_evals/`, not left as an instruction in the Market Agent's system prompt.
- **Network-policy-level egress enforcement**: independent of the application-level permission check, a Kubernetes network policy ([13-deployment-architecture.md](13-deployment-architecture.md)) restricts non-cluster-internal network access to the Market Agent's tool pod specifically — so a future tool addition cannot quietly acquire a second egress path merely by being granted the permission in code. This mirrors the platform's general defense-in-depth pattern (permission enforced at more than one layer, [02-system-architecture.md](02-system-architecture.md) §2.4).

Both controls are a precondition for the Market Agent shipping at all in an environment with real applicant data — they gate Milestone 3, not a later hardening pass. See [11-security-architecture.md](11-security-architecture.md) §11.7 for the corresponding security-architecture statement of this control.
