# Phased Implementation Roadmap

Effort estimates are relative-complexity engineer-weeks for a small human team (2-3 engineers).
Building with Claude Code compresses the typing/scaffolding time substantially, but does **not**
compress the review, eval-harness, and security-hardening time proportionally — those stay
roughly fixed because they're bounded by human judgment and real-world testing, not typing speed.
Treat the estimates as sequencing/complexity signal, not a calendar commitment.

Each phase, before code, gets: objective, architecture notes specific to that phase, DB changes,
API list, AI components, risks/edge cases — per the brief's own methodology. This document is the
index; the detailed per-phase spec is produced immediately before that phase starts (requirements
tend to shift slightly by the time earlier phases are done, so writing phase 6's detailed spec
now would go stale).

## Phase 0 — Foundations & Infra Skeleton (~1 week)
Monorepo scaffold, Docker Compose (Postgres, Redis, Qdrant, api, worker, web), CI skeleton
(lint + typecheck + test on every PR), base FastAPI app with health/readiness endpoints, base
Next.js app, Alembic wired to an empty schema, structured logging + `pydantic-settings` config,
Sentry wired (no-op in local dev), pre-commit hooks (ruff, black, mypy, eslint, prettier).
**Exit criteria:** `docker compose up` gives a working empty stack; CI is green on an empty repo.

## Phase 1 — Auth & Core Identity (~1–1.5 weeks)
`users`, `companies`, `company_members` tables. JWT access/refresh auth, Argon2 hashing, email
verification via Celery + transactional email provider, password reset, RBAC middleware
(candidate/recruiter/admin), Google OAuth for candidate signup. Company CRUD + recruiter invite
flow.
**APIs:** `/auth/register`, `/auth/login`, `/auth/refresh`, `/auth/verify-email`,
`/auth/oauth/google`, `/companies`, `/companies/{id}/members`.
**Risk:** getting refresh-token rotation and RBAC right early avoids retrofitting auth checks
into every later endpoint.

## Phase 2 — Candidate Profile & Resume Ingestion (~2 weeks)
Resume upload → S3 (private, SSE), file-type/magic-byte validation, text extraction
(pdfplumber/python-docx), LLM structured parsing behind a strict Pydantic schema, `candidates` +
`resumes` tables (versioned, content-hash deduped), candidate profile edit UI (AI-extracted
fields are editable, not read-only), BGE-M3 embedding generation → Qdrant `candidates` collection.
Golden-set eval harness for parsing accuracy starts here (small, grows over time).
**APIs:** `/candidates/me`, `/candidates/me/resume` (upload/list/versions),
`/candidates/me/profile` (edit).
**AI:** LLM structured extraction, embedding generation.
**Risk:** prompt-injection guarding (untrusted resume text must never reach a system prompt) —
addressed at the client-interface level, not per-call.

## Phase 3 — Recruiter Job Posting & Job Parsing (~1.5 weeks)
`jobs` table, full CRUD + publish/close/reopen lifecycle, JD structured parsing (same LLM
interface as Phase 2), embeddings → Qdrant `jobs` collection.
**APIs:** `/jobs` (CRUD), `/jobs/{id}/publish`, `/jobs/{id}/close`, `/jobs/{id}/reopen`.
**AI:** LLM structured extraction, embedding generation (same shared pipeline as resumes).

## Phase 4 — Matching Engine Core (~2.5 weeks, highest technical risk)
Semantic search (Qdrant top-100 per job), hybrid search (payload pre-filter on
location/salary/work-mode/experience + sparse/keyword signal), BGE reranking, explainable score
composition (weighted sub-scores: semantic similarity, skill overlap, experience fit, salary fit,
location fit), `match_scores` table (immutable, versioned), per-company configurable threshold
(default 70%). Eval harness extended to score/ranking quality, not just extraction accuracy.
**APIs:** `/jobs/{id}/candidates` (ranked, above threshold), `/candidates/me/recommended-jobs`.
**AI:** semantic search, hybrid search, reranking, score composition.
**Risk:** this is the product's core value prop — budget real iteration time here, not a single
pass. Do not proceed to Phase 6 (autonomous apply) until eval numbers are trustworthy.
Score/explanation caching (keyed by matcher version + content hash, per
[02-ARCHITECTURE.md §7.3](02-ARCHITECTURE.md)) is part of this phase's deliverable, not an
optimization pass — Phase 6 depends on it to stay within cost bounds.

## Phase 5 — Recruiter Review & Application Tracking (~1 week)
Recruiter-facing candidate detail view (resume, skills, match explanation, matched/missing
skills), invite-candidate flow, `applications` table with pipeline states (sourced → invited →
applied → screening → interview → offer → rejected), candidate-facing application status view.
**APIs:** `/jobs/{id}/candidates/{candidate_id}` (detail), `/jobs/{id}/invite`, `/applications`.

## Phase 6 — AI Job Apply Agent (LangGraph) (~2.5–3 weeks)
`agent_configs` (candidate preferences: roles, tech, locations, work mode, min salary, min match
%, auto-apply toggle), LangGraph graph with Postgres checkpointer, Celery Beat 24h-window job
scan, constraint validation nodes, decision + action node
(internal-apply / prepare-external-redirect / skip), `agent_decisions` immutable log, daily
auto-apply cap.
**APIs:** `/candidates/me/agent-config`, `/candidates/me/agent-decisions` (history),
`/applications` (internal apply path reused from Phase 5).
**AI:** full matching pipeline reused (Phases 2–4) + LangGraph orchestration + decision reasoning
generation.
**Risk:** external-ATS handling is prepare-and-redirect only in v1, not auto-submit — see
[01-ANALYSIS.md §2.8](01-ANALYSIS.md). This is a scope boundary, not a deferred feature.
**Cost control is built in this phase, not retrofitted** — decision-log short-circuiting (skip
already-evaluated pairs), rerank funnel, lazy explanation generation, and per-candidate daily
caps are part of the Phase 6 exit criteria. See [02-ARCHITECTURE.md §7](02-ARCHITECTURE.md).

## Phase 7 — AI Recruiter Agent (LangGraph) (~1.5–2 weeks)
Graph triggered on candidate registration/resume update: finds high-match open jobs, updates
cached rankings, generates AI candidate summaries, drafts (never auto-sends) outreach messages
for recruiter approval.
**APIs:** `/jobs/{id}/candidates` gains "new high match" surfacing, `/outreach-drafts`
(recruiter approves/edits/sends).

## Phase 8 — Notifications & Observability (~1 week)
Notification service (in-app feed + transactional email), Langfuse tracing wired through every
LLM/agent call, correlation IDs through logs, CloudWatch/Grafana dashboards, Sentry alert routing.

## Phase 9 — Hardening, Security Review, Load Testing, Deployment (~1.5–2 weeks)
Security review (auth, injection, file upload, prompt injection, rate limiting, IDOR checks on
company-scoped data), load testing on the matching pipeline (Locust/k6), Terraform for AWS infra,
staging environment, backup/DR runbook for Postgres and Qdrant, production rollout.

---

**Total v1 scope:** ~16–18 engineer-weeks of complexity, sequenced as above. Billing/monetization
is intentionally Phase 10+, after the core recruiter/candidate loop is validated — see
[01-ANALYSIS.md §2.2](01-ANALYSIS.md) for why the schema is still designed to absorb it without a
rewrite.

**Immediate next step (pending your go-ahead):** Phase 0 — infra skeleton. No product code, no AI
calls, just a working scaffold everything else builds on.
