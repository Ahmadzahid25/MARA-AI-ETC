## [2026-07-23] Initial Assessment

Project: MARA AI-ETC (OpenHands checkout evolved into Agentic AI platform)
Git state: 5 commits, last commit ebcd19d (README Status section)
Current milestone: Milestone 0 (Foundation)
Key docs: docs/architecture/00-INDEX.md, docs/architecture/14-roadmap.md, docs/governance/architecture-approval-report.md
Existing test patterns: tests/unit/mara/ follows simple pytest patterns with fixtures
Frontend stack: React 19, Vite, React Router 7, Tailwind CSS 4, TypeScript
Design system: @openhands/ui (packages/openhands-ui/)
Services: FastAPI with Keycloak JWT auth, OTel tracing
Infra: Two Postgres instances (primary + dify per ACCB C-5)
CI: mara-ci.yml runs ruff lint + pytest tests/unit/mara/ via uv on ubuntu-24.04
