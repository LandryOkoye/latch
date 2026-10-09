import threading
import time
from collections import deque

from fastapi import HTTPException


class RateLimit:
    """A global sliding-window cap. The public demo can send real email and spend
    Bedrock tokens, so agent-triggering endpoints are capped per hour."""

    def __init__(self, per_hour: int, what: str):
        self.per_hour = per_hour
        self.what = what
        self._calls: deque[float] = deque()
        self._lock = threading.Lock()

    def check(self) -> None:
        now = time.monotonic()
        with self._lock:
            while self._calls and now - self._calls[0] > 3600:
                self._calls.popleft()
            if len(self._calls) >= self.per_hour:
                raise HTTPException(status_code=429, detail=f"The demo's hourly limit for {self.what} is used up. Try again later.")
            self._calls.append(now)


pursue_limit = RateLimit(30, "running the Pursuer")
ingest_limit = RateLimit(30, "extracting meetings")
