import asyncio
import time


class RateLimiter:
    def __init__(self, requests_per_minute: int = 60):
        self.interval = 60.0 / max(1, requests_per_minute)
        self._last = 0.0

    async def wait(self) -> None:
        now = time.time()
        elapsed = now - self._last
        if elapsed < self.interval:
            await asyncio.sleep(self.interval - elapsed)
        self._last = time.time()
