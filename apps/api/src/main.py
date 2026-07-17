from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.v1.router import router as v1_router
from src.core.config import get_settings
from src.core.logging import configure_logging
from src.core.sentry import configure_sentry

settings = get_settings()

configure_logging()
configure_sentry(settings)

app = FastAPI(title="AI Talent Match API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(v1_router)
