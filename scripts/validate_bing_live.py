#!/usr/bin/env python3
"""Run a read-only Bing Webmaster canary and emit redacted response shapes."""

from __future__ import annotations

import json
import os
import sys
from collections.abc import Mapping
from datetime import date, timedelta
from importlib.metadata import version
from pathlib import Path
from typing import Any

_SOURCE_ROOT = Path(__file__).resolve().parents[1] / "src"
if str(_SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(_SOURCE_ROOT))

from gsc_mcp.providers.bing import (  # noqa: E402
    BingApiError,
    BingWebmasterClient,
    READ_METHODS,
    parse_bing_date,
)

REQUIRED_ENVIRONMENT = (
    "BING_WEBMASTER_API_KEY",
    "BING_TEST_SITE",
    "BING_TEST_PAGE",
    "BING_TEST_FEED",
    "BING_TEST_QUERY",
)
_BING_SCHEMA_FIELDS = frozenset(
    {
        "AllOtherCodes",
        "AnchorCount",
        "AnchorText",
        "AuthenticationCode",
        "AvgClickPosition",
        "AvgImpressionPosition",
        "BlockedByRobotsTxt",
        "BroadImpressions",
        "Clicks",
        "Code2xx",
        "Code301",
        "Code302",
        "Code4xx",
        "Code5xx",
        "Compressed",
        "ConnectionTimeout",
        "ContainsMalware",
        "Count",
        "CrawlErrors",
        "CrawledPages",
        "CrawlRate",
        "DailyQuota",
        "Date",
        "Details",
        "DiscoveryDate",
        "DnsFailures",
        "DnsVerificationCode",
        "DocumentSize",
        "FileSize",
        "HttpStatus",
        "Impressions",
        "InIndex",
        "InLinks",
        "IsPage",
        "IsVerified",
        "Issues",
        "LastCrawled",
        "LastCrawledDate",
        "Links",
        "MonthlyQuota",
        "Query",
        "Status",
        "Submitted",
        "TotalChildUrlCount",
        "TotalPages",
        "Type",
        "Url",
        "UrlCount",
    }
)
_ERROR_CATEGORIES = {
    "InvalidJson": "invalid_json",
    "Timeout": "timeout",
    "TransportError": "transport_error",
}


class MissingConfigurationError(RuntimeError):
    """Report missing names without retaining configuration values."""

    def __init__(self, missing: tuple[str, ...]) -> None:
        self.missing = missing
        message = f"Missing required environment variables: {', '.join(missing)}"
        super().__init__(message)


def load_config(environment: Mapping[str, str] | None = None) -> dict[str, str]:
    source = os.environ if environment is None else environment
    missing = tuple(
        name
        for name in REQUIRED_ENVIRONMENT
        if not source.get(name, "").strip()
    )
    if missing:
        raise MissingConfigurationError(missing)
    return {name: source[name].strip() for name in REQUIRED_ENVIRONMENT}


def build_read_calls(
    config: Mapping[str, str], *, today: date
) -> tuple[tuple[str, dict[str, object]], ...]:
    site = config["BING_TEST_SITE"]
    page = config["BING_TEST_PAGE"]
    feed = config["BING_TEST_FEED"]
    query = config["BING_TEST_QUERY"]
    start_date = (today - timedelta(days=30)).isoformat()
    end_date = today.isoformat()
    return (
        ("GetUserSites", {}),
        ("GetQueryStats", {"siteUrl": site}),
        ("GetPageStats", {"siteUrl": site}),
        ("GetPageQueryStats", {"siteUrl": site, "page": page}),
        ("GetRankAndTrafficStats", {"siteUrl": site}),
        ("GetCrawlStats", {"siteUrl": site}),
        ("GetCrawlIssues", {"siteUrl": site}),
        ("GetCrawlSettings", {"siteUrl": site}),
        ("GetUrlInfo", {"siteUrl": site, "url": page}),
        ("GetUrlTrafficInfo", {"siteUrl": site, "url": page}),
        ("GetFeeds", {"siteUrl": site}),
        ("GetFeedDetails", {"siteUrl": site, "feedUrl": feed}),
        (
            "GetKeywordStats",
            {"q": query, "country": "US", "language": "en"},
        ),
        (
            "GetRelatedKeywords",
            {
                "q": query,
                "country": "US",
                "language": "en",
                "startDate": start_date,
                "endDate": end_date,
            },
        ),
        ("GetLinkCounts", {"siteUrl": site, "page": 0}),
        ("GetUrlLinks", {"siteUrl": site, "link": page, "page": 0}),
        ("GetUrlSubmissionQuota", {"siteUrl": site}),
    )


def _observed_dates(payload: object) -> list[str]:
    dates = []
    if isinstance(payload, list):
        for item in payload:
            dates.extend(_observed_dates(item))
    elif isinstance(payload, dict):
        for key, value in payload.items():
            if isinstance(key, str) and key.lower().endswith("date"):
                parsed = parse_bing_date(value)
                if parsed is not None:
                    dates.append(parsed)
            dates.extend(_observed_dates(value))
    return dates


def run_canary(
    client: Any, config: Mapping[str, str], *, today: date
) -> dict[str, object]:
    calls = build_read_calls(config, today=today)
    methods = tuple(method for method, _ in calls)
    if len(methods) != len(READ_METHODS) or set(methods) != READ_METHODS:
        raise RuntimeError("Live validator read-method contract is incomplete")

    records = []
    verified_site_present = False
    for method, params in calls:
        try:
            payload, http_status = client.read_with_status(
                method,
                params,
            )
        except BingApiError as error:
            records.append(
                {
                    "method": method,
                    "ok": False,
                    "http_status": error.status_code,
                    "error_category": _ERROR_CATEGORIES.get(
                        error.code,
                        "api_error",
                    ),
                }
            )
            continue
        except Exception:
            records.append(
                {
                    "method": method,
                    "ok": False,
                    "error": "unexpected_error",
                }
            )
            continue
        record: dict[str, object] = {
            "method": method,
            "ok": True,
            "http_status": http_status,
            "shape": describe_shape(payload),
        }
        dates = _observed_dates(payload)
        if dates:
            record["observed_min_date"] = min(dates)
            record["observed_max_date"] = max(dates)
        records.append(record)

        if method == "GetUserSites" and isinstance(payload, list):
            verified_site_present = any(
                isinstance(item, dict) and item.get("IsVerified") is True
                for item in payload
            )

    return {
        "verified_site_present": verified_site_present,
        "methods": records,
    }


def main() -> int:
    try:
        config = load_config()
    except MissingConfigurationError as error:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": "missing_configuration",
                    "missing": list(error.missing),
                },
                sort_keys=True,
            )
        )
        return 2

    today = date.today()
    report = run_canary(
        BingWebmasterClient(config["BING_WEBMASTER_API_KEY"]),
        config,
        today=today,
    )
    report = {
        "canary_date": today.isoformat(),
        "package_version": version("gsc-mcp-tools"),
        **report,
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    all_reads_ok = all(record["ok"] for record in report["methods"])
    return 0 if report["verified_site_present"] and all_reads_ok else 1


def _type_name(value: object) -> str:
    if value is None:
        return "NoneType"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        return "str"
    if isinstance(value, list):
        return "list"
    if isinstance(value, dict):
        return "dict"
    return "unsupported"


def _field_name(value: object) -> str:
    if isinstance(value, str) and value in _BING_SCHEMA_FIELDS:
        return value
    return "<redacted-key>"


def describe_shape(payload: object) -> dict[str, Any]:
    """Describe JSON structure without copying any response value."""
    if isinstance(payload, list):
        types_by_key: dict[str, set[str]] = {}
        for item in payload:
            if not isinstance(item, dict):
                continue
            for key, value in item.items():
                field_name = _field_name(key)
                types_by_key.setdefault(field_name, set()).add(_type_name(value))
        item_keys = sorted(types_by_key)
        item_types = {
            key: sorted(types_by_key[key])
            for key in item_keys
        }
        return {
            "type": "list",
            "count": len(payload),
            "item_keys": item_keys,
            "item_types": item_types,
        }

    if isinstance(payload, dict):
        types_by_key = {}
        for key, value in payload.items():
            field_name = _field_name(key)
            types_by_key.setdefault(field_name, set()).add(_type_name(value))
        keys = sorted(types_by_key)
        return {
            "type": "dict",
            "keys": keys,
            "value_types": {key: sorted(types_by_key[key]) for key in keys},
        }

    return {"type": _type_name(payload)}


if __name__ == "__main__":
    raise SystemExit(main())
