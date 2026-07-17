# AI Talent Match Platform

AI-first recruiting platform (candidates + recruiters) built around semantic resume/job matching,
not keyword search. Full product brief, risk analysis, architecture, and phased roadmap live in
`docs/`:

- [docs/01-ANALYSIS.md](docs/01-ANALYSIS.md) — gaps in the original brief, risks, and the
  architectural calls made to address them (multi-tenancy, auth, PII handling, prompt-injection
  guarding, auto-apply legal scope, etc.)
- [docs/02-ARCHITECTURE.md](docs/02-ARCHITECTURE.md) — system architecture, repo layout, data
  model, AI integration layer, deployment target
- [docs/03-ROADMAP.md](docs/03-ROADMAP.md) — phase-by-phase implementation plan with scope and
  effort per phase

## Stack

Frontend: Next.js (App Router), TypeScript, Tailwind, shadcn/ui, TanStack Query, React Hook Form,
Zod.
Backend: Python, FastAPI, SQLAlchemy, Alembic, Celery.
Data: PostgreSQL (system of record), Qdrant (vectors), Redis (broker/cache), S3 (resume files).
AI: LangChain/LangGraph orchestration; Qwen 3, BGE-M3, BGE Reranker via a managed inference API
in v1 (provider TBD — DeepInfra/Together/Fireworks are the candidates), behind an internal
swappable client interface so a self-hosted vLLM/TEI deployment is a drop-in later.
Deploy: Docker/Docker Compose locally, AWS ECS Fargate + RDS + ElastiCache + Qdrant Cloud in
production, Terraform for infra, GitHub Actions for CI.

## Architecture rules

- **Modular monolith**, not microservices. One FastAPI codebase, hard module boundaries
  (candidate / job / matching / agent / notification / billing), each independently extractable
  later if traffic ever demands it.
- **Clean Architecture layering** inside `apps/api/src`: `domain` (pure, no framework imports) →
  `application` (use cases) → `infrastructure` (SQLAlchemy/Qdrant/S3/LLM adapters implementing
  `domain` interfaces) → `api` (FastAPI routers only, no business logic).
- **AI pipeline is async, always.** Resume/job upload endpoints return immediately; parsing,
  embedding, matching happen in Celery workers with a visible status field. Never call an
  LLM/embedding/reranker from a request-handling code path.
- **Untrusted content never enters a system prompt.** Resume/JD text is always the "data" input
  to a structured-extraction call, never concatenated into instructions.
- **Every agent decision is logged**, including "did not act" decisions, to `agent_decisions` —
  this is both the fault-tolerance/observability requirement and the audit trail.
- **External-ATS auto-apply is prepare-and-redirect, not auto-submit.** True one-click auto-apply
  is scoped to jobs native to our platform only. See 01-ANALYSIS.md §2.8 before changing this.
- No placeholders, no TODOs, no mock implementations in code delivered as "done" for a phase.

## Status

Planning complete (this document + docs/01–03). No application code written yet. Next step is
Phase 0 (infra skeleton) — pending founder go-ahead.
