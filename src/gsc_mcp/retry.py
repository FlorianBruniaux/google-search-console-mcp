import time
import functools
from typing import Callable

from googleapiclient.errors import HttpError

_RETRYABLE_STATUSES = {429, 500, 502, 503, 504}


def with_retry(max_retries: int = 3, base_delay: float = 1.0) -> Callable:
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except HttpError as exc:
                    status = int(exc.resp.status)
                    if status not in _RETRYABLE_STATUSES:
                        raise
                    last_exc = exc
                    if attempt < max_retries:
                        time.sleep(base_delay * (2 ** attempt))
            raise last_exc
        return wrapper
    return decorator
