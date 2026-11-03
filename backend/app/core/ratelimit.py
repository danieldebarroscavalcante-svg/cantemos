"""Limite simples de requisições em memória (a API roda em uma única instância)."""

import time
from collections import defaultdict, deque
from threading import Lock

from fastapi import HTTPException, Request, status


class RateLimiter:
    def __init__(self, max_calls: int, per_seconds: int) -> None:
        self.max_calls = max_calls
        self.per_seconds = per_seconds
        self._calls: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def hit(self, key: str) -> None:
        now = time.monotonic()
        with self._lock:
            calls = self._calls[key]
            while calls and now - calls[0] > self.per_seconds:
                calls.popleft()
            if len(calls) >= self.max_calls:
                raise HTTPException(
                    status.HTTP_429_TOO_MANY_REQUESTS,
                    "Muitas tentativas em pouco tempo. Aguarde um minuto e tente de novo.",
                )
            calls.append(now)

    def reset(self) -> None:
        with self._lock:
            self._calls.clear()


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    return forwarded.split(",")[0].strip() or (request.client.host if request.client else "?")
