import sentry_sdk

from src.core.config import Settings


def configure_sentry(settings: Settings) -> None:
    """No-op when SENTRY_DSN is unset, which is the expected state in local dev."""
    if not settings.sentry_dsn:
        return

    sentry_sdk.init(dsn=settings.sentry_dsn, environment=settings.env, traces_sample_rate=0.1)
