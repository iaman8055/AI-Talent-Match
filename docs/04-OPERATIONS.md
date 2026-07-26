# Operations Runbook

Backup/DR procedures and the security-hardening decisions from Phase 9
(`docs/03-ROADMAP.md`). Companion to `docs/02-ARCHITECTURE.md` (system design) and
`infra/terraform/` (infra-as-code, written but not applied — see that directory's `versions.tf`
header for why).

## 1. Data stores and what's actually irreplaceable

This matters for backup priority: not everything here needs the same rigor.

- **Postgres (Supabase-hosted in dev, RDS in `infra/terraform/rds.tf`)** — the system of record.
  Users, candidates, jobs, applications, match_scores, agent_configs/decisions, outreach_drafts,
  notifications. **If this is lost, it's genuinely gone** — nothing else in the system can
  reconstruct it.
- **Qdrant (candidates/jobs vector collections)** — a derived cache, not source data. Every
  vector in it is deterministically re-derivable from Postgres: `candidates.skills` +
  `headline`/`summary`/etc. → re-embed → re-upsert (same for jobs). **A lost Qdrant collection is
  fully recoverable** by re-dispatching `embed_resume`/`embed_job` for every candidate/job whose
  Postgres row still exists and is `ready`. This is a real, load-bearing property of this
  architecture, not an assumption — worth knowing before treating a Qdrant incident as data loss.
- **S3 / Supabase Storage (resume files)** — source data (the original uploaded PDF/DOCX).
  Losing this doesn't break matching (the extracted fields are already in Postgres), but the
  candidate would need to re-upload if they wanted the file itself preserved.

## 2. Postgres backup/restore

**Dev today (Supabase-hosted):** Supabase provides automatic daily backups + point-in-time
recovery on paid tiers — confirm the project's plan actually has PITR enabled; the free tier
does not. Restore is done from the Supabase dashboard (Database → Backups).

**Once on RDS (`infra/terraform/rds.tf`):** `backup_retention_period = 7` is already set, giving
7 days of automated snapshots + PITR. To restore:
```
aws rds restore-db-instance-to-point-in-time \
  --source-db-instance-identifier ai-talent-match-<env> \
  --target-db-instance-identifier ai-talent-match-<env>-restored \
  --restore-time <ISO8601 timestamp>
```
This creates a **new** instance — cut the app over to it (update the `DATABASE_URL` secret in
Secrets Manager, per `infra/terraform/secrets.tf`), verify, then decommission the old one.

**Manual/ad-hoc backup** (before a risky migration, for example):
```
pg_dump --format=custom --file=backup.dump "$DATABASE_URL"
```
Restore: `pg_restore --clean --if-exists --dbname="$DATABASE_URL" backup.dump`

## 3. Qdrant backup/restore

Qdrant Cloud supports collection snapshots via its API:
```
POST /collections/{collection_name}/snapshots
```
returns a downloadable snapshot file; restore via:
```
PUT /collections/{collection_name}/snapshots/upload
```
**In practice, for this app, taking snapshots is optional** — per §1, both collections are fully
reconstructable from Postgres. The cheaper, always-correct recovery path if a collection is lost
or corrupted:
1. Delete the collection (or let `ensure_collection` recreate it — it only creates when absent).
2. For every `resumes` row with `status = 'ready'`, re-enqueue `embed_resume_task.delay(resume_id)`.
3. For every `jobs` row with `processing_status = 'ready'`, re-enqueue `embed_job_task.delay(job_id)`.
4. Matching recomputes itself as each embed completes (`MatchingDispatcher` calls already wired
   into both parsing services).

## 4. Rate limiting (Phase 9 addition)

`core/rate_limit.py` — Redis-backed (`slowapi`), keyed by client IP. Chosen over in-memory
specifically because the deployment target is multiple ECS Fargate replicas behind an ALB
(§6 of the architecture doc) — an in-memory counter per replica would let a client simply get a
fresh quota by hitting a different replica.

Thresholds (`api/v1/auth/router.py`), and why:
- `POST /auth/login` — **5/minute**. The tightest limit: this is the direct brute-force/
  credential-stuffing target.
- `POST /auth/request-password-reset` — **5/minute**. Same class of risk — also an email-
  enumeration vector (does this address have an account?) if left unthrottled.
- `POST /auth/register`, `/auth/reset-password`, `/auth/accept-invite`, `/auth/oauth/google` —
  **10/minute**. Real abuse surface (signup spam, token-guessing) but not the primary target.
- `POST /auth/refresh` — **30/minute**. Deliberately generous — refresh tokens are high-entropy
  (not guessable), and a legitimate active user can plausibly refresh fairly often.
- `POST /auth/verify-email` — unthrottled. A random one-time token isn't a meaningfully
  brute-forceable target at any rate limit that wouldn't also block legitimate retries.

If a threshold turns out to be wrong in practice (real users hitting 429s, or evidence of abuse
slipping through), it's a one-line change in `api/v1/auth/router.py` — not a redesign.

## 5. Security headers & CORS

`core/middleware.py`'s `SecurityHeadersMiddleware` adds `X-Content-Type-Options: nosniff`,
`X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin` always, and
`Strict-Transport-Security` only when `ENV != local` (HSTS actively breaks local `http://`
dev). CORS origin is `settings.frontend_url` — set this to the real deployed web app URL in
production; it defaults to `http://localhost:3000` for local dev.

## 6. Scaling the Celery pipeline

**Two queues, not one** (`infrastructure/tasks/celery_app.py`'s `task_routes`): `heavy` (parse,
embed, rerank, recruiter-agent draft generation — anything that can block on the shared
NVIDIA/Hugging Face rate limiter) and `light` (email, the Apply Agent, the LinkedIn scraper's own
HTTP work — none of these call an LLM/embedder). A worker only consumes the queue(s) passed to
`-Q`; see `services/worker/main.py`'s docstring for the exact commands, both the single-worker
local-dev form (`-Q heavy,light`) and the two-process scaled form (`-Q heavy` / `-Q light`
separately). The reason this split exists: without it, a single worker blocked waiting on an AI
rate-limit slot couldn't send a notification email meanwhile either — cheap, latency-sensitive
work was getting stuck behind expensive, rate-limited work.

**Horizontal worker scaling is safe** — the rate limiter in `infrastructure/ai/nvidia_client.py`
is Redis-backed (shared across every process hitting it), not a per-worker in-memory counter, so
running multiple `heavy` worker processes/replicas stays correctly bounded by the account's real
rate limit rather than each replica getting its own separate budget. Beat does not get this
treatment — run exactly one Beat process regardless of how many workers exist (see
`services/worker/main.py`'s docstring on why running more than one double/triple-schedules every
periodic task).

**Hot-read caching** (`infrastructure/caching/redis_cache_client.py`): `GET
/candidates/me/recommended-jobs` and `GET /candidates/me/jobs/{job_id}` are cached for 60s,
keyed per candidate, against the same Redis instance already used as the broker. No manual
invalidation — the TTL is short enough that a stale read is a non-issue, and this avoids the much
larger risk of a missed invalidation site leaving a read stale forever. Verified directly during
development: an uncached read against the (network-latency-bound, pooled Supabase) DB took ~14s;
the cached read immediately after took ~290ms.

## 7. Observability

What exists today, without any external metrics/tracing stack:

- **Structured JSON logs** (`core/logging.py`'s `JSONFormatter`) carry `request_id` on every API
  request, and any `extra={...}` fields a caller passes are flattened into the JSON payload
  directly (not silently dropped — this had to be fixed to actually work).
- **Rate-limit wait time** is logged whenever a call actually had to wait for an NVIDIA slot
  (`infrastructure/ai/nvidia_client.py`'s `_acquire_slot`) — `rate_limit_wait_seconds` in the
  structured log. Silent when there's no wait; this is "is the rate limit actually the
  bottleneck right now" signal, not routine noise.
- **Per-task duration** (`core/timing.py`'s `log_task_duration`) wraps every task on the `heavy`
  queue (parse/embed for both jobs and resumes, match computation) — `task_name` and
  `duration_seconds` in the structured log, logged even on failure since "timed out after 90s
  waiting on the rate limiter" and "failed instantly" are different signals worth telling apart.
- **Queue depth and worker status**: [Flower](https://flower.readthedocs.io/) (`dev` dependency
  group, `apps/api/pyproject.toml`) — a real-time web dashboard over the same Redis broker, zero
  code required. Run it locally against a running worker:
  ```
  cd apps/api
  uv run celery -A src.infrastructure.tasks.celery_app flower
  ```
  then open `http://localhost:5555` — per-queue length, worker online/offline status, task
  history and timing, retry counts. It also exposes a Prometheus-format `/metrics` endpoint for
  free (pulled in as a transitive dependency) if a Prometheus/Grafana stack is ever stood up.
  Not wired into `docker-compose.yml`/Terraform — add it there (with real auth in front of it;
  Flower's dashboard has no auth of its own by default) when actually deploying, rather than
  speculatively now.
- **Not built**: Langfuse LLM tracing, CloudWatch/Grafana dashboards, Sentry alert routing — all
  explicitly deferred in Phase 8 for lack of real infra to point them at. The structured logging
  above is what those would consume once they exist; nothing here needs to change to add them
  later.

## 8. What Phase 9 deliberately does not cover

- **Load testing was written, not run** (`infra/load-test/locustfile.py`) — running it fires
  real, metered requests at NVIDIA's API and real load at Supabase/Qdrant Cloud's free-tier
  limits. Run it yourself against an environment you control once you're ready to spend that
  budget.
- **Terraform was written, not applied** — no AWS account is wired into this session. Add a
  remote state backend (S3 + DynamoDB lock table) before the first real `apply`, since
  `infra/terraform/versions.tf` doesn't configure one yet.
- **Staging environment and production rollout** are execution steps requiring a real AWS
  account, domain, and DNS — genuinely nothing to build here beyond the Terraform above; they're
  next steps for whoever has that access, not something a coding session can complete.
