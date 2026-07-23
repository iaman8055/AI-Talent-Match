from slowapi import Limiter
from slowapi.util import get_remote_address

from src.core.config import get_settings

settings = get_settings()

# Redis-backed (not in-memory) because the deployment target is multiple ECS Fargate replicas
# behind an ALB (docs/02-ARCHITECTURE.md §6) — an in-memory counter per replica would let a
# client simply get a fresh quota by hitting a different replica.
limiter = Limiter(key_func=get_remote_address, storage_uri=settings.redis_url)
