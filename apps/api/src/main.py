import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from src.api.exception_handlers import register_exception_handlers
from src.api.v1.router import router as v1_router
from src.core.config import get_settings
from src.core.logging import configure_logging
from src.core.middleware import RequestIDMiddleware, SecurityHeadersMiddleware
from src.core.rate_limit import limiter
from src.core.sentry import configure_sentry
from src.infrastructure.storage.s3_client import S3StorageClient

settings = get_settings()

configure_logging()
configure_sentry(settings)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    if settings.supabase_s3_access_key_id:
        try:
            S3StorageClient(
                bucket=settings.supabase_storage_bucket,
                endpoint_url=settings.supabase_s3_endpoint_url,
                access_key_id=settings.supabase_s3_access_key_id,
                secret_access_key=settings.supabase_s3_secret_access_key,
                region=settings.supabase_s3_region,
            ).ensure_bucket()
        except Exception:
            logger.warning(
                "Could not verify/create storage bucket %r at startup — it may need to be "
                "created manually (e.g. via the Supabase dashboard)",
                settings.supabase_storage_bucket,
                exc_info=True,
            )
    yield


app = FastAPI(title="AI Talent Match API", version="0.1.0", lifespan=lifespan)

app.state.limiter = limiter
# slowapi's handler is typed narrowly for RateLimitExceeded specifically; Starlette's
# add_exception_handler wants a handler typed for the general Exception base — a typing
# mismatch in the library itself, not a real type error here.
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(SecurityHeadersMiddleware, enable_hsts=not settings.is_local)

app.include_router(v1_router)
register_exception_handlers(app)
