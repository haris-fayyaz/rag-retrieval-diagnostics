"""
Reusable in-memory rate limiter, applied as a FastAPI dependency.

In-memory only: state lives in this one process, resets on restart,
and isn't shared across instances. Fine for this single-process local
project. A real multi-instance deployment needs a shared backend
(e.g. Redis) so every instance sees the same counts - see README.
"""
import threading
import time
from collections import defaultdict, deque

from fastapi import Depends, HTTPException, Request


class InMemoryRateLimiter:
    """Sliding-window request counter, keyed by caller-supplied string."""

    def __init__(self):
        self._hits: dict[str, deque] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key: str, max_requests: int, window_seconds: int = 60) -> None:
        """
        Raise 429 if `key` has hit `max_requests` within the last
        `window_seconds`, otherwise record this request.
        - Raises before recording: a rejected request doesn't itself
          count against the caller's next attempt.
        - Lock covers read+write together, so two concurrent requests
          for the same key can't both slip past a limit of 1.
        """
        now = time.monotonic()
        with self._lock:
            hits = self._hits[key]
            while hits and now - hits[0] >= window_seconds:
                hits.popleft()
            if len(hits) >= max_requests:
                retry_after = max(1, int(window_seconds - (now - hits[0])))
                raise HTTPException(
                    status_code=429,
                    detail="Too many requests",
                    headers={"Retry-After": str(retry_after)},
                )
            hits.append(now)


rate_limiter = InMemoryRateLimiter()


def rate_limit(max_requests: int, key_dependency=None):
    """
    Dependency factory - Depends(rate_limit(N)) limits by client IP,
    Depends(rate_limit(N, get_current_user)) limits by whatever
    key_dependency resolves to (e.g. the authenticated username).
    Generic on purpose: not tied to one auth mechanism.
    """
    if key_dependency is not None:
        def check_by_key(key: str = Depends(key_dependency)) -> None:
            rate_limiter.check(f"user:{key}", max_requests)
        return check_by_key

    def check_by_ip(request: Request) -> None:
        rate_limiter.check(f"ip:{request.client.host}", max_requests)
    return check_by_ip