from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    env: str = "local"

    database_url: str = "postgresql+psycopg://talent_match:talent_match@localhost:5432/talent_match"
    redis_url: str = "redis://localhost:6379/0"
    qdrant_url: str = "http://localhost:6333"
    # Blank for local docker-compose Qdrant (no auth). Required for Qdrant Cloud — set alongside
    # qdrant_url pointing at the cluster's endpoint.
    qdrant_api_key: str | None = None

    sentry_dsn: str | None = None

    # JWT / auth. jwt_secret_key's default is dev-only and intentionally obvious —
    # production deployments must override it via the real environment.
    jwt_secret_key: str = "insecure-dev-only-secret-change-me"
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 30

    # Google OAuth (candidate login). Blank until real credentials are configured;
    # the /auth/oauth/google endpoint reports 503 while unset.
    google_client_id: str | None = None
    google_client_secret: str | None = None
    google_oauth_redirect_uri: str | None = None

    frontend_url: str = "http://localhost:3000"

    # Local/Cloud Ollama (LLM structured extraction + embeddings) — not currently wired up (see
    # nvidia_* below), kept configured in case of a future switch back.
    ollama_api_key: str | None = None
    ollama_base_url: str = "http://localhost:11434"
    ollama_llm_model: str = "qwen3:8b"
    ollama_embedding_model: str = "bge-m3"

    # NVIDIA hosted inference API (https://integrate.api.nvidia.com/v1, OpenAI-compatible) — the
    # active LLM/embedding provider (infrastructure/ai/nvidia_client.py). Always requires an API
    # key (no local/no-auth mode, unlike Ollama).
    nvidia_api_key: str | None = None
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"
    nvidia_llm_model: str = "nvidia/nemotron-3-ultra-550b-a55b"
    nvidia_embedding_model: str = "nvidia/nv-embedqa-e5-v5"

    # Supabase Storage, accessed via its S3-compatible API.
    supabase_s3_endpoint_url: str | None = None
    supabase_s3_access_key_id: str | None = None
    supabase_s3_secret_access_key: str | None = None
    supabase_s3_region: str = "us-east-1"
    supabase_storage_bucket: str = "resumes"

    @property
    def is_local(self) -> bool:
        return self.env == "local"


@lru_cache
def get_settings() -> Settings:
    return Settings()
