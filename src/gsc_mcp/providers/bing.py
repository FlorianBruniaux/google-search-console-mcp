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
from gsc_mcp.providers.base import (
    SearchMetricBatch,
    SearchMetricRow,
    UnsupportedProviderFeature,
)

_BING_API_BASE = "https://ssl.bing.com/webmaster/api.svc/json"
_RETRYABLE_STATUSES = {429, 500, 502, 503, 504}
_MAX_RETRIES = 3
_OPERATION_TIMEOUT = 15.0
_BING_DATE = re.compile(r"^/Date\((?P<millis>-?\d+)(?P<offset>[+-]\d{4})?\)/$")
_SAFE_ERROR_CODE = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]{0,63}$")
_PUBLIC_ERROR_CODES = frozenset(
    {"InvalidApiKey", "InternalError", "NotFound", "ThrottleUser", "Unavailable"}
)

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

    def read_with_status(
        self, method: str, params: dict[str, object]
    ) -> tuple[object, int]:
        if method not in READ_METHODS:
            raise ValueError(f"Bing read method is not allowed: {method}")
        return self._request_with_status("GET", method, params=params)

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
        payload, _ = self._request_with_status(
            http_method,
            method,
            params=params,
            body=body,
        )
        return payload

    def _request_with_status(
        self,
        http_method: str,
        method: str,
        *,
        params: dict[str, object] | None = None,
        body: dict[str, object] | None = None,
    ) -> tuple[object, int]:
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
                    return _strip_type(data), response.status_code

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
        return code if code in _PUBLIC_ERROR_CODES else "api_error"


def get_bing_client() -> BingWebmasterClient:
    return BingWebmasterClient(get_bing_api_key())


_METRIC_METHODS = {
    ("query",): "GetQueryStats",
    ("page",): "GetPageStats",
    ("date",): "GetRankAndTrafficStats",
}


def _metric_int(value: object) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _metric_float(value: object) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _weighted_value(total: float, weight: int) -> float | None:
    return round(total / weight, 1) if weight else None


class BingSearchProvider:
    def fetch(
        self,
        site: str,
        start_date: str,
        end_date: str,
        dimensions: tuple[str, ...],
    ) -> SearchMetricBatch:
        method = _METRIC_METHODS.get(dimensions)
        if method is None:
            raise UnsupportedProviderFeature(
                f"Bing does not support dimensions {dimensions!r}"
            )

        raw_rows = get_bing_client().read(method, {"siteUrl": site})
        filtered_rows, observed_dates = self._filter_rows(
            raw_rows, start_date, end_date
        )
        if dimensions == ("date",):
            rows = self._aggregate_dates(filtered_rows)
            position_semantics = "unavailable"
        else:
            dimension = dimensions[0]
            rows = self._aggregate_positions(filtered_rows, dimension)
            position_semantics = "bing_average_impression_position"

        return SearchMetricBatch(
            engine="bing",
            dimensions=dimensions,
            rows=rows,
            requested_start=start_date,
            requested_end=end_date,
            observed_start=min(observed_dates) if observed_dates else None,
            observed_end=max(observed_dates) if observed_dates else None,
            window_exact=False,
            position_semantics=position_semantics,
        )

    @staticmethod
    def _filter_rows(
        raw_rows: object, start_date: str, end_date: str
    ) -> tuple[list[tuple[dict, str]], list[str]]:
        filtered: list[tuple[dict, str]] = []
        observed_dates: list[str] = []
        if not isinstance(raw_rows, list):
            return filtered, observed_dates

        for raw in raw_rows:
            if not isinstance(raw, dict):
                continue
            observed_date = parse_bing_date(raw.get("Date"))
            if observed_date is None or not start_date <= observed_date <= end_date:
                continue
            filtered.append((raw, observed_date))
            observed_dates.append(observed_date)
        return filtered, observed_dates

    @staticmethod
    def _aggregate_dates(
        filtered_rows: list[tuple[dict, str]],
    ) -> tuple[SearchMetricRow, ...]:
        aggregates: dict[str, dict[str, int]] = {}
        for raw, observed_date in filtered_rows:
            aggregate = aggregates.setdefault(
                observed_date, {"clicks": 0, "impressions": 0}
            )
            aggregate["clicks"] += _metric_int(raw.get("Clicks"))
            aggregate["impressions"] += _metric_int(raw.get("Impressions"))

        rows = []
        for observed_date in sorted(aggregates):
            aggregate = aggregates[observed_date]
            clicks = aggregate["clicks"]
            impressions = aggregate["impressions"]
            rows.append(
                SearchMetricRow(
                    engine="bing",
                    date=observed_date,
                    query=None,
                    page=None,
                    clicks=clicks,
                    impressions=impressions,
                    ctr=round(clicks / impressions, 4) if impressions else 0.0,
                    position=None,
                )
            )
        return tuple(rows)

    @staticmethod
    def _aggregate_positions(
        filtered_rows: list[tuple[dict, str]], dimension: str
    ) -> tuple[SearchMetricRow, ...]:
        aggregates: dict[str | None, dict[str, int | float]] = {}
        for raw, _ in filtered_rows:
            raw_key = raw.get("Query")
            key = str(raw_key) if raw_key is not None else None
            aggregate = aggregates.setdefault(
                key,
                {
                    "clicks": 0,
                    "impressions": 0,
                    "click_position_total": 0.0,
                    "click_position_weight": 0,
                    "impression_position_total": 0.0,
                    "impression_position_weight": 0,
                },
            )
            clicks = _metric_int(raw.get("Clicks"))
            impressions = _metric_int(raw.get("Impressions"))
            aggregate["clicks"] += clicks
            aggregate["impressions"] += impressions

            avg_click_position = _metric_float(raw.get("AvgClickPosition"))
            if avg_click_position is not None and clicks:
                aggregate["click_position_total"] += (
                    avg_click_position * clicks
                )
                aggregate["click_position_weight"] += clicks

            avg_impression_position = _metric_float(
                raw.get("AvgImpressionPosition")
            )
            if avg_impression_position is not None and impressions:
                aggregate["impression_position_total"] += (
                    avg_impression_position * impressions
                )
                aggregate["impression_position_weight"] += impressions

        rows = []
        for key, aggregate in aggregates.items():
            clicks = int(aggregate["clicks"])
            impressions = int(aggregate["impressions"])
            avg_click_position = _weighted_value(
                float(aggregate["click_position_total"]),
                int(aggregate["click_position_weight"]),
            )
            avg_impression_position = _weighted_value(
                float(aggregate["impression_position_total"]),
                int(aggregate["impression_position_weight"]),
            )
            rows.append(
                SearchMetricRow(
                    engine="bing",
                    date=None,
                    query=key if dimension == "query" else None,
                    page=key if dimension == "page" else None,
                    clicks=clicks,
                    impressions=impressions,
                    ctr=round(clicks / impressions, 4) if impressions else 0.0,
                    position=avg_impression_position,
                    provider_metrics={
                        "avg_click_position": avg_click_position,
                        "avg_impression_position": avg_impression_position,
                    },
                )
            )
        rows.sort(key=lambda row: row.impressions, reverse=True)
        return tuple(rows)
