import logging
import time
from collections.abc import Iterator
from contextlib import contextmanager

logger = logging.getLogger(__name__)


@contextmanager
def log_task_duration(task_name: str, **context: object) -> Iterator[None]:
    """Logs how long a Celery task body actually took, as a structured field (core/logging.py's
    JSONFormatter surfaces `extra`) — the only per-task latency signal this app has today; there
    is no external metrics stack. Always logs, including on failure, since the duration up to a
    raised exception is still real signal (e.g. "this timed out after 90s waiting on the rate
    limiter" vs. "this failed instantly")."""
    start = time.monotonic()
    try:
        yield
    finally:
        logger.info(
            "Task duration",
            extra={
                "task_name": task_name,
                "duration_seconds": round(time.monotonic() - start, 2),
                **context,
            },
        )
