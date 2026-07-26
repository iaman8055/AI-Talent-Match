from typing import Protocol


class CacheClient(Protocol):
    """A small, generic key/value cache with TTL — used for short-lived caching of hot read
    endpoints (e.g. recommended jobs, job detail) whose data is expensive to recompute per
    request but tolerant of a short staleness window. Deliberately no manual invalidation API:
    every cache write here uses a short TTL and lets entries expire naturally rather than trying
    to track every place a write could make a cached read stale — simpler and can't go wrong by
    missing an invalidation site."""

    def get(self, key: str) -> str | None: ...

    def set(self, key: str, value: str, ttl_seconds: int) -> None: ...
