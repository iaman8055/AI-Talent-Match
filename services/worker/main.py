"""Celery worker entrypoint.

The worker has no dependencies or virtual environment of its own — it runs inside
apps/api's environment and imports apps/api/src as a package, per
docs/02-ARCHITECTURE.md §2. This keeps task code and its models/config in one place
instead of duplicating them across two Python packages.

Two queues exist (celery_app.py's task_routes): "heavy" (parse/embed/rerank/draft-generation —
anything that can block on the shared NVIDIA/HF AI rate limiter) and "light" (notifications,
email, the Apply Agent, the LinkedIn scraper's own HTTP work — none of these call an LLM/embedder
directly). A worker only consumes the queue(s) you tell it to with -Q — every command below
needs -Q heavy,light or its tasks silently pile up unconsumed. This is what fixes a real defect:
without split queues, one worker blocked waiting on an AI rate-limit slot couldn't send a
notification email meanwhile either.

Run locally, worker + Beat scheduler in ONE process, listening to both queues (recommended for
local dev — see the "separate processes" note below for when NOT to do this):
    cd services/worker
    uv run --project ../../apps/api celery -A main.celery_app worker -Q heavy,light --loglevel=info -B

-B (--beat) embeds Beat's scheduler as a thread inside the worker process, so the periodic
jobs already defined in celery_app.py's beat_schedule — the Apply Agent scan (every 15 min)
and the LinkedIn job-ingestion scrape (every 6h, infrastructure/tasks/linkedin_scraper_tasks.py)
— fire automatically without a second command/terminal. Nothing about the LinkedIn scraper
needs manual triggering in normal operation; it was already schedule-driven, it just needed
Beat running somewhere to actually fire.

On Windows, add --pool=solo: the default prefork pool relies on fork/multiprocessing
semantics Windows doesn't support properly, and fails with billiard errors like
"WinError 6: The handle is invalid" / "WinError 5: Access is denied" as soon as a task
runs. --pool=solo runs tasks single-threaded in the main process instead, sidestepping
that entirely — it's the standard fix for local Celery dev on Windows:
    uv run --project ../../apps/api celery -A main.celery_app worker -Q heavy,light --loglevel=info --pool=solo -B

Scale to two worker processes once a single one becomes a bottleneck — genuinely just an ops
change now, no code change, since the rate limiter is Redis-backed (shared across processes)
rather than per-worker. Run each in its own terminal, no -B on either (Beat stays separate,
see below) — a light worker for fast, latency-sensitive work that should never wait behind an
AI call, and a heavy worker (or several, if the AI provider's real capacity allows it) for the
rate-limited pipeline:
    uv run --project ../../apps/api celery -A main.celery_app worker -Q light --loglevel=info --pool=solo -n light@%h
    uv run --project ../../apps/api celery -A main.celery_app worker -Q heavy --loglevel=info --pool=solo -n heavy@%h

Run worker and Beat as separate processes instead of -B when scaling to more than one worker
process/replica: -B embeds exactly one scheduler per process it's attached to, so running it
on N worker replicas double/triple/N-schedules every periodic task (each fires N times, not
once) — this is why docker-compose.yml and infra/terraform/ecs.tf both define worker and beat
as distinct single-instance services rather than using -B, and why running multiple -B workers
locally at once is also wrong (same failure mode we hit this session — two Beat schedulers were
found running simultaneously). Locally with a single worker process, -B is exactly correct; once
scaled to the two-process setup above, run Beat as its own third process instead, no --pool
since Beat has no worker pool:
    uv run --project ../../apps/api celery -A main.celery_app beat --loglevel=info

Run via Docker: see infra/docker/Dockerfile.worker (worker + beat services in docker-compose.yml;
update its command to add -Q heavy,light, or split into two services matching the two-process
setup above once that's warranted). The container runs Linux, so the prefork pool there is
unaffected by the Windows issue above.
"""

import sys
from pathlib import Path

_API_SRC_ROOT = Path(__file__).resolve().parents[2] / "apps" / "api"
if str(_API_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_API_SRC_ROOT))

from src.infrastructure.tasks.celery_app import celery_app  # noqa: E402

__all__ = ["celery_app"]

if __name__ == "__main__":
    celery_app.start()
