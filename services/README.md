# services/

Independently deployable backend services — see [`docs/architecture/03-repository-structure.md`](../docs/architecture/03-repository-structure.md) §3.2.

Includes both platform infrastructure services (memory, knowledge, approval, notification) and the 5 components reclassified from the original 12-agent draft to deterministic services per [`docs/architecture/05-agent-architecture.md`](../docs/architecture/05-agent-architecture.md) §5.10–5.11: `supervisor_service`, `publishing_service`, `voice_service`, `audit_service`. None of these carry an LLM-reasoning loop by default — see §5.14 for the test that governs whether new work belongs here or in `agents/`.

`api_gateway` is the single entry point for all client traffic (Milestone 0) — authentication, rate limiting, correlation-ID assignment, request/response schema validation. No business logic lives there.

Dependency rule: services may depend on `shared/` and `openhands/`, never on `agents/` or `workflows/` (services are lower-level than orchestration) — see [`docs/architecture/03-repository-structure.md`](../docs/architecture/03-repository-structure.md) §3.3.
