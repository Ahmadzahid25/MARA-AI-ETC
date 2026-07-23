« [Index](00-INDEX.md) | Phase 11 of 16 »

# Phase 11 — Security Architecture

> **v1.0 note:** §11.7 now specifies mandatory query sanitization for the Market Agent's search tool (ACCB Mandatory Change 1); §11.4 and §11.7 reference the Audit Service and `docs/policy/` per the reclassification and taxonomy corrections in [05-agent-architecture.md](05-agent-architecture.md) and the [repository audit](../repo-audit/00-index.md).

## 11.1 Threat model summary

The system's primary assets are applicant personal/financial data and MARA's own decision-making integrity. The primary threats considered: (1) unauthorized access to applicant data (insider or external), (2) prompt injection causing an agent to exceed its intended tool/data scope, (3) data leakage to external LLM/search providers beyond what's authorized, (4) an agent taking an unapproved irreversible action, (5) tampering with the audit trail itself. Every control below maps to one of these.

## 11.2 Authentication & authorization

- **Authentication**: Keycloak ([04-technology-stack.md](04-technology-stack.md)), federated with MARA's corporate identity provider via OIDC/SAML where available; MFA required for all officer accounts, non-negotiable for any role with approval authority.
- **RBAC**: coarse-grained roles (Entrepreneurship Officer, Compliance Officer, Finance Officer, Risk Officer, Branch Manager, Committee Secretary, Auditor, Administrator) gate which UI surfaces, workflows, and approval types a user can access at all — enforced at the API Gateway.
- **ABAC**: fine-grained, attribute-based checks layered on top of RBAC for decisions RBAC alone can't express — e.g., "this officer may only approve applications in their assigned branch/state," or "this document's sensitivity classification restricts it to officers with an active security clearance level." Enforced at the Memory Service and Tool Runtime, not just the Gateway, so a valid role alone is insufficient to reach data outside an officer's attribute-scoped assignment.
- **Defense in depth**: permission checks happen at the Gateway (coarse, fast reject), the Supervisor (workflow-scope check — Phase 5), and the Tool Runtime (per-tool grant check — Phase 6) independently. This redundancy is deliberate: a prompt-injected agent that somehow gets past its own system-prompt instructions still hits a hard permission check at the Tool Runtime that has no dependency on the LLM having "decided" correctly.

## 11.3 Encryption

- **At rest**: Postgres (transparent data encryption or disk-level encryption depending on deployment target), object storage server-side encryption, Vault-managed keys.
- **In transit**: TLS everywhere internally (service-to-service) and externally; no plaintext internal traffic even within the cluster network, since insider/lateral-movement risk is explicitly in scope.
- **Secrets**: never in code, config files, or logs — sourced from Vault/K8s Secrets at runtime via `openhands/app_server/secrets` ([04-technology-stack.md](04-technology-stack.md)), with automatic rotation for API keys where the provider supports it.

## 11.4 PDPA compliance

- **Data minimization**: agents and tools are scoped to the specific document set/workflow they're assigned ([05-agent-architecture.md](05-agent-architecture.md), [06-tool-architecture.md](06-tool-architecture.md)) — no agent has standing broad access to the full applicant database.
- **Purpose limitation**: applicant data ingested for one workflow (e.g., Loan Assessment) is not repurposed into Knowledge Memory without explicit redaction and approval (Phase 9's precedent-ingestion path).
- **Accountability**: Audit Memory ([08-memory-architecture.md](08-memory-architecture.md)) plus the Audit Service directly serve PDPA accountability/subject-access requests — "what data do you hold on this individual and what was it used for" is answerable by query, not by manual reconstruction.
- **Right to correction/erasure**: handled through the same amendment/correction mechanism as [10-human-in-the-loop.md](10-human-in-the-loop.md) for operational data; Long-term Memory's per-officer personal-preference data supports a genuine erasure path where PDPA requires it, distinct from Audit Memory's immutability (accountability records about *processing having occurred* are retained even when the personal data referenced within them is redacted, consistent with standard PDPA/GDPR-pattern practice of anonymizing rather than deleting audit trails).
- **Data residency**: self-hosted-by-default posture for OCR/TTS/STT/embeddings on sensitive documents ([04-technology-stack.md](04-technology-stack.md)) exists specifically to keep raw applicant data off third-party infrastructure unless explicitly classified as non-sensitive.

## 11.5 Document classification

Every ingested document and every workflow instance carries a sensitivity classification (e.g., Public / Internal / Sensitive-Personal / Sensitive-Financial), assigned at ingestion ([09-knowledge-architecture.md](09-knowledge-architecture.md)) and inherited by every downstream artifact derived from it. Classification is the single input that drives: which OCR/LLM/TTS execution path is used (self-hosted vs. cloud-eligible), which roles can access the document, and what retention policy applies. This is enforced as metadata checked by the Tool Runtime before dispatch, not a convention agents are trusted to respect.

## 11.6 Prompt injection protection

- **Tool-grant enforcement independent of the LLM** (11.2 above) is the primary defense — even a successfully injected agent cannot call a tool outside its role's allow-list, because the check doesn't trust the agent's own stated intent.
- **Untrusted-content isolation**: document content, OCR output, and search results are treated as untrusted data in the prompt, structurally delimited from system/instruction content, with agents explicitly instructed (and evaluated in `tests/agent_evals/`) to treat instructions found inside document content as data, never as commands.
- **No agent can grant itself new tools or escalate another agent's permissions** — permission grants are static configuration ([03-repository-structure.md](03-repository-structure.md) `agents/*`), not something any agent or workflow can mutate at runtime.
- **Output filtering**: agent outputs destined for a human are scanned for indicators of injection success (e.g., an agent unexpectedly attempting to reference tools/data outside its declared scope) before display, logged as a security event if triggered.

## 11.7 Data leakage prevention

- **Egress control**: the Market Agent's web-search tool is the only tool with outbound internet access ([06-tool-architecture.md](06-tool-architecture.md)); all other agents/tools operate against internal services only, closing off the most obvious exfiltration path (an agent "searching" applicant data to an external endpoint). As of v1.0, this restriction is enforced at two independent layers, not one: the Tool Runtime permission grant (application layer) **and** a Kubernetes network policy restricting non-cluster-internal traffic to the Market Agent's tool pod specifically (infrastructure layer, [13-deployment-architecture.md](13-deployment-architecture.md)) — so a future tool addition cannot quietly acquire a second egress path merely by being granted the permission in application code.
- **Query sanitization** *(added in v1.0 — ACCB Mandatory Change 1)*: restricting *which* tool can reach the internet says nothing about *what data that tool sends externally*. The web/external search tool itself enforces PII sanitization — applicant names, IC numbers, business registration numbers, and exact addresses are detected and generalized to sector/industry/region terms, or the call is rejected, before any outbound request is constructed. This closes Review Board Finding B3 ([review/02-agent-and-tool-review.md](review/02-agent-and-tool-review.md) §5.3): egress-restriction-to-one-tool and query-content-sanitization are different controls, and the original draft only specified the first. Full detail in [06-tool-architecture.md](06-tool-architecture.md) §6.6. This is a precondition for the Market Agent shipping, not a follow-on hardening task.
- **LLM provider data-handling agreements**: any cloud LLM/API provider used for non-self-hosted paths is contractually bound (zero-retention/no-training-on-input terms) as a prerequisite for being an approved provider at all — this is a procurement/legal gate as much as a technical one, tracked in `docs/policy/` (ACCB Condition C-1 taxonomy) — recorded there as a named, trackable gate, not a background assumption (ACCB Condition C-4 tracks the parallel legal sign-off on OpenHands' own upstream licensing).
- **Egress logging**: every external call (search, cloud LLM, cloud OCR/TTS opt-in) is logged with the data sent, in Audit Memory, so a leakage incident is investigable rather than undetectable after the fact.

## 11.8 Model isolation

- Each agent's LLM calls are scoped to that agent's own conversation/task context — one agent's Shared Memory access is read-through-the-service (Phase 8), never a raw shared prompt/context window across agents, which prevents context bleed where one agent's sensitive data accidentally appears in another agent's prompt via careless context concatenation.
- Self-hosted model path (vLLM, [04-technology-stack.md](04-technology-stack.md)) is available specifically so maximum-sensitivity workloads never leave MARA-controlled infrastructure, independent of any cloud provider's stated data-handling policy.

## 11.9 Network security

- Kubernetes network policies restrict service-to-service traffic to declared dependencies (e.g., `tools/ocr` can reach the sandbox and object storage, not the Approval Service database directly) — least-privilege at the network layer mirrors least-privilege at the permission layer.
- The Tool Runtime's sandbox ([04-technology-stack.md](04-technology-stack.md)) is network-isolated by default per execution, with the Market Agent's search tool as the sole, explicitly allow-listed egress path.
- Production ingress is behind a WAF; the Gateway is the only externally reachable service.

## 11.10 API security

- Every API Gateway request requires authentication; no anonymous or service-to-service call bypasses authorization checks, including internal calls between `services/*` (mutual TLS + service identity, not network-location-based trust).
- Rate limiting and per-user/per-workflow tool-call budgets ([06-tool-architecture.md](06-tool-architecture.md)) double as both a cost control and an abuse/anomaly-detection signal.
- Input validation (typed schemas throughout, per [06-tool-architecture.md](06-tool-architecture.md)) closes the injection paths (SQL, command) that a raw-string interface would otherwise expose to LLM-generated input.

## 11.11 Security review cadence

Given the sensitivity of the data involved, this architecture is designed to pass a formal government security review before production launch — the constraints in [01-vision.md](01-vision.md) (self-hostability, data residency, PDPA-first design) exist specifically so that review is a validation of an already-sound design, not a late-stage redesign trigger. A dedicated third-party security assessment (including prompt-injection red-teaming specific to the agent architecture) is a gate in [14-roadmap.md](14-roadmap.md) before any Loan Assessment workflow processes real applicant data.
