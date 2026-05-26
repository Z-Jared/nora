from __future__ import annotations

import time


class TokenBucketRateLimiter:
    def __init__(self, rate: float = 10.0, burst: int = 20):
        self.rate = max(0.1, rate)
        self.burst = max(1, burst)
        self._tokens = float(burst)
        self._last_refill = time.monotonic()

    def allow(self, key: str = "default") -> bool:
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(self.burst, self._tokens + elapsed * self.rate)
        self._last_refill = now

        if self._tokens >= 1.0:
            self._tokens -= 1.0
            return True
        return False
