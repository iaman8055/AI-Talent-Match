"""Celery worker entrypoint.

The worker has no dependencies or virtual environment of its own — it runs inside
apps/api's environment and imports apps/api/src as a package, per
docs/02-ARCHITECTURE.md §2. This keeps task code and its models/config in one place
instead of duplicating them across two Python packages.

Run locally:
    cd services/worker
    uv run --project ../../apps/api celery -A main.celery_app worker --loglevel=info

Run the Apply Agent's scheduler locally (separate process, same entrypoint — see
docs/03-ROADMAP.md Phase 6 / celery_app.py's beat_schedule):
    cd services/worker
    uv run --project ../../apps/api celery -A main.celery_app beat --loglevel=info

Run via Docker: see infra/docker/Dockerfile.worker (worker + beat services in docker-compose.yml)
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
