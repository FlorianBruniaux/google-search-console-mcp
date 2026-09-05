"""Secure JSON client for the Bing Webmaster API."""

from __future__ import annotations

import logging
import re
import time
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any

import httpx

from gsc_mcp.auth import get_bing_api_key

_BING_API_BASE = "https://ssl.bing.com/webmaster/api.svc/json"
_RETRYABLE_STATUSES = {429, 500, 502, 503, 504}
_MAX_RETRIES = 3
_OPERATION_TIMEOUT = 15.0
_BING_DATE = re.compile(r"^/Date\((?P<millis>-?\d+)(?P<offset>[+-]\d{4})?\)/$")
_SAFE_ERROR_CODE = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]{0,63}$")

READ_METHODS = frozenset(
    {
        "GetUserSites",
        "GetQueryStats",
        "GetPageStats",
        "GetPageQueryStats",
        "GetRankAndTrafficStats",
        "GetCrawlStats",
        "GetCrawlIssues",
        "GetCrawlSettings",
        "GetUrlInfo",
        "GetUrlTrafficInfo",
        "GetFeeds",
        "GetFeedDetails",
        "GetKeywordStats",
        "GetRelatedKeywords",
        "GetLinkCounts",
        "GetUrlLinks",
        "GetUrlSubmissionQuota",
    }
)
WRITE_METHODS = frozenset({"SubmitUrl", "SubmitUrlBatch", "SubmitFeed", "RemoveFeed"})


class _BlockAllLogs(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return False


@contextmanager
def _suppress_httpx_logs() -> Iterator[None]:
    logger = logging.getLogger("httpx")
    log_filter = _BlockAllLogs()
    logger.addFilter(log_filter)
    try:
        yield
    finally:
        logger.removeFilter(log_filter)


class BingApiError(RuntimeError):
    """An expurgated Bing API failure that never includes request data."""

    def __init__(
        self, status_code: int | None, method: str, code: str | None
    ) -> None:
        self.status_code = status_code
        self.method = method
        self.code = code
        super().__init__(
            f"Bing API request failed: status={status_code}, method={method}, code={code}"
        )


def parse_bing_date(value: object) -> str | None:
    """Normalize Bing's .NET or ISO date representation to YYYY-MM-DD."""
    if not isinstance(value, str):
        return None

    match = _BING_DATE.fullmatch(value)
    try:
        if match:
            timestamp = int(match.group("millis")) / 1000
            return datetime.fromtimestamp(timestamp, tz=timezone.utc).date().isoformat()

        normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
        return datetime.fromisoformat(normalized).date().isoformat()
    except (OverflowError, ValueError):
        return None


def _strip_type(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _strip_type(child)
            for key, child in value.items()
            if key != "__type"
        }
    if isinstance(value, list):
        return [_strip_type(child) for child in value]
    return value


class BingWebmasterClient:
    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    def read(self, method: str, params: dict[str, object]) -> object:
        if method not in READ_METHODS:
            raise ValueError(f"Bing read method is not allowed: {method}")
        return self._request("GET", method, params=params)

    def write(self, method: str, body: dict[str, object]) -> object:
        if method not in WRITE_METHODS:
            raise ValueError(f"Bing write method is not allowed: {method}")
        return self._request("POST", method, body=body)

    def _request(
        self,
        http_method: str,
        method: str,
        *,
        params: dict[str, object] | None = None,
        body: dict[str, object] | None = None,
    ) -> object:
        url = f"{_BING_API_BASE}/{method}"
        request_params = dict(params or {})
        request_params["apikey"] = self._api_key
        deadline = time.monotonic() + _OPERATION_TIMEOUT

        with httpx.Client(timeout=15, follow_redirects=False) as client:
            for attempt in range(_MAX_RETRIES + 1):
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise BingApiError(None, method, "Timeout")

                transport_error = None
                try:
                    with _suppress_httpx_logs():
                        if http_method == "GET":
                            response = client.get(
                                url, params=request_params, timeout=remaining
                            )
                        else:
                            response = client.post(
                                url,
                                params=request_params,
                                json=body,
                                timeout=remaining,
                            )
                except httpx.TimeoutException:
                    transport_error = "Timeout"
                except httpx.RequestError:
                    transport_error = "TransportError"

                if transport_error is not None:
                    raise BingApiError(None, method, transport_error)

                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise BingApiError(None, method, "Timeout")

                if (
                    response.status_code in _RETRYABLE_STATUSES
                    and attempt < _MAX_RETRIES
                ):
                    time.sleep(min(2**attempt, remaining))
                    continue

                payload = self._parse_response(response, method)
                if 200 <= response.status_code < 300:
                    data = payload.get("d") if isinstance(payload, dict) else None
                    return _strip_type(data)

                code = self._error_code(payload)
                raise BingApiError(response.status_code, method, code)

        raise AssertionError("unreachable")

    def _parse_response(self, response: httpx.Response, method: str) -> object:
        invalid_json = False
        try:
            payload = response.json()
        except (TypeError, ValueError):
            invalid_json = True

        if invalid_json:
            raise BingApiError(response.status_code, method, "InvalidJson")
        return payload

    def _error_code(self, payload: object) -> str | None:
        if not isinstance(payload, dict):
            return None
        error = payload.get("error")
        if not isinstance(error, dict):
            return None
        code = error.get("code")
        if not isinstance(code, str):
            return None
        if not _SAFE_ERROR_CODE.fullmatch(code):
            return None
        if self._api_key and self._api_key in code:
            return None
        return code


def get_bing_client() -> BingWebmasterClient:
    return BingWebmasterClient(get_bing_api_key())
