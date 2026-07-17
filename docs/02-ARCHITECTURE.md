# Architecture

## 1. System shape

Modular monolith (see [01-ANALYSIS.md](01-ANALYSIS.md) §3 for rationale) with an async pipeline
for anything AI-driven. Three runtime processes share one codebase:

```
                         ┌─────────────┐
                         │   Next.js    │  apps/web
                         │  (frontend)  │
                         └──────┬───────┘
                                │ HTTPS / REST (OpenAPI)
                         ┌──────▼───────┐        ┌───────────────┐
                         │   FastAPI    │◄──────►│  PostgreSQL   │
                         │   (api)      │        └───────────────┘
                         │ apps/api     │        ┌───────────────┐
                         └──────┬───────┘◄──────►│    Qdrant     │
                                │ enqueue          └───────────────┘
                         ┌──────▼───────┐        ┌───────────────┐
                         │ Celery worker│◄──────►│     Redis      │
                         │ services/    │        │ (broker+cache) │
                         │  worker      │        └───────────────┘
                         └──────┬───────┘
                    ┌───────────┼────────────┐
              ┌─────▼────┐ ┌────▼─────┐ ┌────▼─────┐
              │  S3       │ │ Managed  │ │  LangGraph │
              │ (resumes) │ │ LLM/Embed│ │  agents    │
              │           │ │ API      │ │ (Apply +   │
              └───────────┘ └──────────┘ │ Recruiter) │
                                          └────────────┘
```

- **apps/web** — Next.js App Router frontend, talks only to the FastAPI REST API.
- **apps/api** — FastAPI app: HTTP layer, request validation, synchronous reads, enqueues
  long-running work.
- **services/worker** — Celery workers (parsing, embedding, matching, agent runs, notifications)
  plus Celery Beat for scheduled jobs (24h new-job scan for the Apply Agent).
- **PostgreSQL** — system of record: users, companies, jobs, candidates, applications, scores,
  agent decisions.
- **Qdrant** — vector store: `candidates` and `jobs` collections, payload-filterable.
- **Redis** — Celery broker/result backend + short-TTL caches (e.g. embedding dedup lookups).
- **S3** — original resume files, private, signed-URL access only.
- **Managed LLM/embedding API** — Qwen 3 (parsing/reasoning), BGE-M3 (embeddings), BGE Reranker,
  all behind one internal client interface (see §4).

## 2. Repository layout (monorepo)

```
ai-talent-match/
├── apps/
│   ├── web/                        # Next.js frontend
│   │   ├── app/
│   │   │   ├── (auth)/
│   │   │   ├── (candidate)/
│   │   │   ├── (recruiter)/
│   │   │   └── layout.tsx
│   │   ├── components/
│   │   │   ├── ui/                 # shadcn/ui primitives
│   │   │   └── features/           # feature-scoped components
│   │   ├── lib/
│   │   │   ├── api-client/         # typed client generated from OpenAPI + TanStack Query hooks
│   │   │   ├── validators/         # zod schemas mirroring backend Pydantic schemas
│   │   │   └── utils/
│   │   ├── hooks/
│   │   └── types/
│   │
│   └── api/                        # FastAPI backend
│       ├── src/
│       │   ├── main.py
│       │   ├── core/                # config (pydantic-settings), security, logging, exceptions, DI
│       │   ├── domain/               # pure business entities + interfaces (ports). No framework imports.
│       │   │   ├── candidate/
│       │   │   ├── recruiter/
│       │   │   ├── company/
│       │   │   ├── job/
│       │   │   ├── matching/
│       │   │   ├── application/
│       │   │   └── agent/
│       │   ├── application/          # use cases: orchestrate domain + infra ports
│       │   │   ├── candidate/
│       │   │   ├── job/
│       │   │   ├── matching/
│       │   │   ├── application_tracking/
│       │   │   └── agent/
│       │   ├── infrastructure/       # adapters implementing the ports
│       │   │   ├── db/               # SQLAlchemy models, repositories, Alembic
│       │   │   ├── vector_store/     # Qdrant client + hybrid search
│       │   │   ├── storage/          # S3 client
│       │   │   ├── ai/               # LLM / embedding / reranker clients (provider-swappable)
│       │   │   ├── notifications/    # email provider adapter
│       │   │   └── tasks/            # Celery task definitions, thin wrappers over use cases
│       │   ├── api/
│       │   │   └── v1/
│       │   │       ├── auth/
│       │   │       ├── candidates/
│       │   │       ├── companies/
│       │   │       ├── jobs/
│       │   │       ├── matching/
│       │   │       └── agents/
│       │   └── agents/               # LangGraph graph definitions
│       │       ├── apply_agent/
│       │       └── recruiter_agent/
│       ├── alembic/
│       ├── tests/
│       │   ├── unit/
│       │   ├── integration/
│       │   └── eval/                 # AI extraction/matching accuracy harness
│       └── pyproject.toml
│
├── services/
│   └── worker/                      # Celery worker entrypoint (imports apps/api/src as a package)
│
├── infra/
│   ├── docker/
│   ├── terraform/                   # AWS: VPC, RDS, ECS Fargate, ALB, S3, ElastiCache
│   └── nginx/
│
├── docs/
│   ├── 01-ANALYSIS.md
│   ├── 02-ARCHITECTURE.md
│   └── 03-ROADMAP.md
│
├── .github/workflows/               # CI: lint, typecheck, test, build
├── docker-compose.yml                # local dev: postgres, redis, qdrant, api, worker, web
└── CLAUDE.md
```

`domain` never imports SQLAlchemy, FastAPI, boto3, or an LLM SDK — it defines interfaces
(`ResumeRepository`, `EmbeddingProvider`, `VectorStore`) that `infrastructure` implements and
`api`/`tasks` wire together via dependency injection. This is what lets the AI provider, the
vector DB, or even Postgres itself be swapped in one layer without touching business rules.

## 3. Core data model (high level — full DDL written in Phase 0/1 migrations)

- `users` (auth identity, role: candidate/recruiter/admin)
- `companies`, `company_members` (recruiter ↔ company, roles within company)
- `candidates` (profile fields editable post-extraction), `resumes` (versioned, S3 pointer,
  `parser_version`, `content_hash`)
- `jobs` (structured fields + raw description), `job_versions` (re-parse history)
- `match_scores` (candidate_id, job_id, overall %, sub-score breakdown JSON, `matcher_version`,
  computed_at) — immutable, append new rows on re-score rather than overwrite
- `applications` (candidate_id, job_id, source: internal/external_redirect, status, timestamps)
- `agent_configs` (per-candidate Apply Agent preferences), `agent_decisions` (immutable decision
  log, one row per agent evaluation of a job, including "did not apply" decisions and why)
- `notifications` (in-app feed), `notification_deliveries` (email send log)

Every recruiter-owned row carries `company_id`; every scoping query filters on it at the
repository layer (defense in depth on top of the API-layer auth check).

## 4. AI integration layer (`infrastructure/ai/`)

Three interfaces, each with one managed-API implementation for v1 and a documented seam for a
future self-hosted implementation:

- `LLMClient` — structured extraction (resume → JSON, JD → JSON) and generation (summaries,
  outreach drafts). Always called with a strict output schema (Pydantic model → JSON schema),
  never with untrusted content in the system prompt (see 01-ANALYSIS.md §2.6).
- `EmbeddingClient` — BGE-M3 embeddings for resumes and jobs, batched, content-hash-deduped.
- `RerankerClient` — BGE Reranker, takes the top-N Qdrant hits + query, returns reordered
  results with relevance scores that feed the explainable score.

All three are called exclusively from Celery tasks (`infrastructure/tasks/`), never from a
request-handling code path, so a slow provider never blocks an HTTP response.

## 5. LangGraph agents

- **Apply Agent** (`agents/apply_agent/`): scheduled by Celery Beat every N minutes to scan jobs
  published in the last 24h; per candidate with auto-apply enabled, runs the graph:
  `load_profile → embed_or_reuse → semantic_search → hybrid_filter → rerank → score →
  validate_constraints (salary/location/work_mode/experience) → decide → act (internal_apply |
  prepare_external_redirect | skip)`. Postgres-backed checkpointer
  (`langgraph-checkpoint-postgres`) makes every run resumable after a crash. Every node's
  input/output is written to `agent_decisions`.
- **Recruiter Agent** (`agents/recruiter_agent/`): triggered on new candidate registration/resume
  update; finds high-match open jobs, updates cached rankings, generates candidate summaries and
  **draft** outreach messages (never auto-sent — see 01-ANALYSIS.md §2.12).

## 6. Deployment target (AWS)

- **Compute:** ECS Fargate (api, worker, web as separate services/tasks) behind an ALB — chosen
  over EKS for a pre-revenue team: no cluster ops overhead, still scales per-service.
- **Database:** RDS PostgreSQL (Multi-AZ once there's paying usage; single-AZ acceptable for
  early beta).
- **Vector store:** Qdrant Cloud (managed) for v1 — avoids running a stateful vector DB ourselves
  before there's a reason to; self-host on EC2/ECS later if cost or data-residency demands it.
- **Cache/broker:** ElastiCache Redis.
- **Storage:** S3 with SSE-KMS, private bucket, CloudFront only if/when public asset serving is
  needed.
- **IaC:** Terraform, not manual console changes, from Phase 9 onward (infra work is deferred
  until the app shape is stable, to avoid re-writing Terraform every phase).
- **Observability:** Sentry (errors), Langfuse (LLM/agent traces — direct fit for the
  "observable" requirement on the agents), CloudWatch (infra metrics/logs).
- **Secrets:** AWS Secrets Manager, injected as ECS task environment — never `.env` in any
  deployed image.
