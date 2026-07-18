import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.exception_handlers import register_exception_handlers
from src.api.v1.router import router as v1_router
from src.core.config import get_settings
from src.core.logging import configure_logging
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(v1_router)
register_exception_handlers(app)
