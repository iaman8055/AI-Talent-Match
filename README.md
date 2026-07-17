# AI Talent Match

AI-first recruiting platform. See [CLAUDE.md](CLAUDE.md) and [docs/](docs/) for the product brief,
architecture, and phased roadmap. This repo is currently at **Phase 0 — Foundations & Infra
Skeleton**: a working empty scaffold, no product code, no AI calls.

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (with Compose v2)
- [uv](https://docs.astral.sh/uv/) — Python dependency/venv management
- Node.js 22+ and npm — only needed for running `apps/web` outside Docker

## Quick start (Docker)

```bash
cp .env.example .env
docker compose up --build
```

- API: http://localhost:8000 (`/health`, `/ready`)
- Web: http://localhost:3000
- Postgres: localhost:5432, Redis: localhost:6379, Qdrant: localhost:6333

## Running services individually (without Docker)

**API**

```bash
cd apps/api
uv sync
uv run alembic upgrade head   # no-op until the first migration lands
uv run uvicorn src.main:app --reload
```

**Worker** (needs Redis running — e.g. `docker compose up redis`)

```bash
cd services/worker
uv run --project ../../apps/api celery -A main.celery_app worker --loglevel=info
```

**Web**

```bash
cd apps/web
npm install
npm run dev
```

## Checks

```bash
# API
cd apps/api
uv run ruff check .
uv run black --check .
uv run mypy src
uv run pytest

# Web
cd apps/web
npm run lint
npm run format:check
npx tsc --noEmit
npm run build

# All of the above, via pre-commit
uvx pre-commit run --all-files
```

## Repo layout

```
apps/api/       FastAPI backend (Clean Architecture: domain → application → infrastructure → api)
apps/web/       Next.js frontend
services/worker/ Celery worker entrypoint (shares apps/api's environment and code)
infra/docker/   Dockerfiles
docs/           Product analysis, architecture, roadmap
```
