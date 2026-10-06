"""Request budgets for abuse-prone endpoints (password guessing, sign-up floods, AI cost).

A sliding-window counter kept in process memory. That is enough for one API process; with
several workers or hosts each keeps its own count, so a shared store (Redis) or the edge proxy
should enforce limits in a scaled deployment.

Clients are told when they may retry through a 429 response with a Retry-After header.
"""

import math
import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status

from fastapi_app.core.config import settings


class RateLimiter:
    """At most `limit` events per key within any `window` seconds."""

    def __init__(self, name: str, limit: int, window: float) -> None:
        self.name = name
        self.limit = limit
        self.window = window
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def _prune(self, key: str, now: float) -> deque[float]:
        events = self._events[key]
        while events and events[0] <= now - self.window:
            events.popleft()
        return events

    def retry_after(self, key: str) -> int:
        """Seconds until another event is allowed for key (0 if allowed now)."""
        with self._lock:
            now = time.monotonic()
            events = self._prune(key, now)
            if len(events) < self.limit:
                return 0
            return max(1, math.ceil(events[0] + self.window - now))

    def record(self, key: str) -> None:
        with self._lock:
            now = time.monotonic()
            self._prune(key, now).append(now)

    def check(self, key: str) -> None:
        """Raises 429 when key is over budget."""
        if not settings.RATE_LIMIT_ENABLED:
            return
        wait = self.retry_after(key)
        if wait:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many attempts. Please wait and try again.",
                headers={"Retry-After": str(wait)},
            )

    def hit(self, key: str) -> None:
        """Checks the budget, then counts this request against it."""
        self.check(key)
        if settings.RATE_LIMIT_ENABLED:
            self.record(key)

    def reset(self) -> None:
        with self._lock:
            self._events.clear()


def client_ip(request: Request) -> str:
    """The connecting address. X-Forwarded-For is deliberately ignored: any client can set it,
    so trusting it would let an attacker pick a fresh key per request. Behind a proxy, have the
    proxy enforce limits or configure uvicorn's --forwarded-allow-ips."""
    return request.client.host if request.client else "unknown"


# Requests of any outcome, per client address
LOGIN_PER_IP = RateLimiter("login-ip", limit=20, window=60)
REGISTER_PER_IP = RateLimiter("register-ip", limit=10, window=3600)
REFRESH_PER_IP = RateLimiter("refresh-ip", limit=30, window=60)
# Reset requests per address: stops flooding inboxes or probing many emails
RESET_PER_IP = RateLimiter("reset-ip", limit=5, window=3600)
# Failed password checks, per account: slows guessing one user's password from many addresses
LOGIN_FAILURES_PER_EMAIL = RateLimiter("login-failures-email", limit=5, window=900)
# Questions per user: bounds the cost a paid AI provider could run up
AI_MESSAGES_PER_USER = RateLimiter("ai-messages-user", limit=30, window=60)

ALL_LIMITERS = [
    LOGIN_PER_IP,
    REGISTER_PER_IP,
    REFRESH_PER_IP,
    RESET_PER_IP,
    LOGIN_FAILURES_PER_EMAIL,
    AI_MESSAGES_PER_USER,
]


def limit_login(request: Request) -> None:
    LOGIN_PER_IP.hit(client_ip(request))


def limit_register(request: Request) -> None:
    REGISTER_PER_IP.hit(client_ip(request))


def limit_reset(request: Request) -> None:
    RESET_PER_IP.hit(client_ip(request))


def limit_refresh(request: Request) -> None:
    REFRESH_PER_IP.hit(client_ip(request))
