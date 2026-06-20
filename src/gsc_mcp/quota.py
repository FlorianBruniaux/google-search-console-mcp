class QuotaTracker:
    def __init__(self, limit: int, warn_at: int):
        self._limit = limit
        self._warn_at = warn_at
        self._used = 0

    def remaining(self) -> int:
        return self._limit - self._used

    def consume(self, n: int) -> None:
        self._used += n

    def check(self, n: int) -> None:
        if self._used + n > self._limit:
            raise RuntimeError(
                f"Indexing API quota exceeded: {self._used} used, {n} requested, limit {self._limit}"
            )

    def should_warn(self) -> bool:
        return self._used >= self._warn_at
