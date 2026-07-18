from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from src.api.v1.auth.router import router as auth_router
from src.api.v1.candidates.router import router as candidates_router
from src.api.v1.companies.router import router as companies_router
from src.api.v1.jobs.router import router as jobs_router
from src.infrastructure.db.session import check_db_connection

router = APIRouter()
router.include_router(auth_router)
router.include_router(companies_router)
router.include_router(candidates_router)
router.include_router(jobs_router)


@router.get("/health")
def health() -> dict[str, str]:
    """Liveness probe — no external dependencies checked."""
    return {"status": "ok"}


@router.get("/ready")
def ready() -> JSONResponse:
    """Readiness probe — verifies the database is reachable."""
    if check_db_connection():
        return JSONResponse(status_code=status.HTTP_200_OK, content={"status": "ready"})
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"status": "not ready", "reason": "database unreachable"},
    )
