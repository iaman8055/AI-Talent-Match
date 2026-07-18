from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    env: str = "local"

    database_url: str = "postgresql+psycopg://talent_match:talent_match@localhost:5432/talent_match"
    redis_url: str = "redis://localhost:6379/0"
    qdrant_url: str = "http://localhost:6333"

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

    # Ollama Cloud (LLM structured extraction + embeddings). Blank api key until configured;
    # calls fail with a clear error rather than silently no-op'ing (unlike email/OAuth, there's
    # no safe no-op for "parse this resume").
    ollama_api_key: str | None = None
    ollama_base_url: str = "https://ollama.com"
    ollama_llm_model: str = "qwen3:cloud"
    ollama_embedding_model: str = "bge-m3"

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
