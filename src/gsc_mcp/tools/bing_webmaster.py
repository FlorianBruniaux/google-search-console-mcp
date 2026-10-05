"""Read-only Bing Webmaster crawl, URL, site, feed, and quota tools."""

from __future__ import annotations

import json
from datetime import date, timedelta

from gsc_mcp.meta import with_meta
from gsc_mcp.providers.bing import get_bing_client, parse_bing_date

_MAX_LIMIT = 10_000
_CRAWL_ISSUE_FLAGS = {
    1: "code_301",
    2: "code_302",
    4: "code_4xx",
    8: "code_5xx",
    16: "blocked_by_robots_txt",
    32: "contains_malware",
    64: "important_url_blocked_by_robots_txt",
    128: "dns_errors",
    256: "timeout_errors",
}
_KNOWN_CRAWL_ISSUE_BITS = sum(_CRAWL_ISSUE_FLAGS)
_CRAWL_COUNT_FIELDS = {
    "CrawledPages": "crawled_pages",
    "CrawlErrors": "crawl_errors",
    "InIndex": "in_index",
    "InLinks": "in_links",
    "Code2xx": "code_2xx",
    "Code301": "code_301",
    "Code302": "code_302",
    "Code4xx": "code_4xx",
    "Code5xx": "code_5xx",
    "BlockedByRobotsTxt": "blocked_by_robots_txt",
    "DnsFailures": "dns_failures",
    "ConnectionTimeout": "connection_timeout",
    "ContainsMalware": "contains_malware",
    "AllOtherCodes": "all_other_codes",
}


def _validate_window(days: int) -> None:
    if not isinstance(days, int) or isinstance(days, bool) or days < 1:
        raise ValueError("days must be at least 1")


def _validate_limit(limit: int) -> None:
    if (
        not isinstance(limit, int)
        or isinstance(limit, bool)
        or not 1 <= limit <= _MAX_LIMIT
    ):
        raise ValueError("limit must be between 1 and 10000")


def _integer(value: object) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _list_of_dicts(value: object) -> list[dict]:
    if not isinstance(value, list):
        return []
    return [row for row in value if isinstance(row, dict)]


def _response(
    data: dict,
    *,
    tool: str,
    params: dict,
    metadata: dict[str, object] | None = None,
) -> str:
    payload = with_meta(data, tool=tool, params=params)
    payload["_meta"]["engine"] = "bing"
    if metadata:
        payload["_meta"].update(metadata)
    return json.dumps(payload)


def _requested_window(days: int) -> dict[str, object]:
    end = date.today()
    start = end - timedelta(days=days - 1)
    return {"start": start.isoformat(), "end": end.isoformat(), "days": days}


def _observed_window(rows: list[dict]) -> dict[str, str | None]:
    dates = [row["date"] for row in rows if isinstance(row.get("date"), str)]
    return {
        "start": min(dates) if dates else None,
        "end": max(dates) if dates else None,
    }


def _crawl_row(raw: dict) -> dict:
    return {
        "date": parse_bing_date(raw.get("Date")),
        **{
            output_name: _integer(raw.get(input_name))
            for input_name, output_name in _CRAWL_COUNT_FIELDS.items()
        },
    }


def _feed_row(raw: dict) -> dict:
    return {
        "compressed": bool(raw.get("Compressed", False)),
        "file_size": _integer(raw.get("FileSize")),
        "last_crawled": parse_bing_date(raw.get("LastCrawled")),
        "status": raw.get("Status"),
        "submitted": parse_bing_date(raw.get("Submitted")),
        "type": raw.get("Type"),
        "url": raw.get("Url"),
        "url_count": _integer(raw.get("UrlCount")),
    }


def bing_sites_list() -> str:
    """Return verified-state summaries for sites visible to the Bing account."""
    raw_sites = get_bing_client().read("GetUserSites", {})
    sites = [
        {"url": raw.get("Url"), "verified": bool(raw.get("IsVerified", False))}
        for raw in _list_of_dicts(raw_sites)
    ]
    return _response(
        {"count": len(sites), "sites": sites},
        tool="bing_sites_list",
        params={},
    )


def bing_crawl_stats(site: str, days: int = 30) -> str:
    """Return dated Bing crawl counts inside the requested local window."""
    _validate_window(days)
    requested_window = _requested_window(days)
    raw_rows = get_bing_client().read("GetCrawlStats", {"siteUrl": site})
    rows = [_crawl_row(raw) for raw in _list_of_dicts(raw_rows)]
    rows = [
        row
        for row in rows
        if isinstance(row["date"], str)
        and requested_window["start"] <= row["date"] <= requested_window["end"]
    ]
    rows.sort(key=lambda row: row["date"])
    return _response(
        {"site": site, "count": len(rows), "rows": rows},
        tool="bing_crawl_stats",
        params={"site": site, "days": days},
        metadata={
            "requested_window": requested_window,
            "observed_window": _observed_window(rows),
        },
    )


def bing_crawl_issues(site: str, limit: int = 1000) -> str:
    """Decode Bing crawl issue flags using the synthetic-fixture contract."""
    _validate_limit(limit)
    raw_rows = get_bing_client().read("GetCrawlIssues", {"siteUrl": site})
    issues = []
    for raw in _list_of_dicts(raw_rows)[:limit]:
        issue_bits = _integer(raw.get("Issues"))
        issues.append(
            {
                "url": raw.get("Url"),
                "issue_types": [
                    name
                    for flag, name in _CRAWL_ISSUE_FLAGS.items()
                    if issue_bits & flag
                ],
                "unknown_issue_bits": issue_bits & ~_KNOWN_CRAWL_ISSUE_BITS,
            }
        )
    return _response(
        {"site": site, "count": len(issues), "issues": issues},
        tool="bing_crawl_issues",
        params={"site": site, "limit": limit},
        metadata={"contract_status": "UNVERIFIED_RUNTIME"},
    )


def bing_crawl_settings_get(site: str) -> str:
    """Return only Bing's observed crawl-rate value from the partial contract."""
    raw = get_bing_client().read("GetCrawlSettings", {"siteUrl": site})
    crawl_rate = raw.get("CrawlRate") if isinstance(raw, dict) else None
    return _response(
        {"site": site, "crawl_rate": crawl_rate},
        tool="bing_crawl_settings_get",
        params={"site": site},
        metadata={"contract_status": "PARTIAL"},
    )


def bing_url_info(site: str, url: str) -> str:
    """Return only fields observed from Bing URL info, without indexation claims."""
    raw = get_bing_client().read(
        "GetUrlInfo", {"siteUrl": site, "url": url}
    )
    raw = raw if isinstance(raw, dict) else {}
    return _response(
        {
            "anchor_count": _integer(raw.get("AnchorCount")),
            "discovery_date": parse_bing_date(raw.get("DiscoveryDate")),
            "document_size": _integer(raw.get("DocumentSize")),
            "http_status": _integer(raw.get("HttpStatus")),
            "is_page": bool(raw.get("IsPage", False)),
            "last_crawled_date": parse_bing_date(raw.get("LastCrawledDate")),
            "total_child_url_count": _integer(raw.get("TotalChildUrlCount")),
            "url": raw.get("Url"),
        },
        tool="bing_url_info",
        params={"site": site, "url": url},
        metadata={"last_crawled_semantics": "last_crawl_observed_only"},
    )


def bing_url_traffic(site: str, url: str) -> str:
    """Return observed URL traffic and derived CTR without rank fields."""
    raw = get_bing_client().read(
        "GetUrlTrafficInfo", {"siteUrl": site, "url": url}
    )
    raw = raw if isinstance(raw, dict) else {}
    clicks = _integer(raw.get("Clicks"))
    impressions = _integer(raw.get("Impressions"))
    return _response(
        {
            "clicks": clicks,
            "impressions": impressions,
            "ctr": round(clicks / impressions, 4) if impressions else 0.0,
            "is_page": bool(raw.get("IsPage", False)),
            "url": raw.get("Url"),
        },
        tool="bing_url_traffic",
        params={"site": site, "url": url},
        metadata={
            "metrics": {
                "measured": ["clicks", "impressions"],
                "derived": ["ctr"],
            }
        },
    )


def bing_feeds_list(site: str) -> str:
    """Return Bing feeds with only the observed, non-indexation fields."""
    raw_feeds = get_bing_client().read("GetFeeds", {"siteUrl": site})
    feeds = [_feed_row(raw) for raw in _list_of_dicts(raw_feeds)]
    return _response(
        {"site": site, "count": len(feeds), "feeds": feeds},
        tool="bing_feeds_list",
        params={"site": site},
    )


def bing_feed_details(site: str, feed_url: str) -> str:
    """Return every Bing feed-detail row from the observed list response."""
    raw_feeds = get_bing_client().read(
        "GetFeedDetails", {"siteUrl": site, "feedUrl": feed_url}
    )
    feeds = [_feed_row(raw) for raw in _list_of_dicts(raw_feeds)]
    return _response(
        {"site": site, "count": len(feeds), "feeds": feeds},
        tool="bing_feed_details",
        params={"site": site, "feed_url": feed_url},
    )


def bing_url_submission_quota(site: str) -> str:
    """Return Bing quota integers without claiming total or remaining semantics."""
    raw = get_bing_client().read(
        "GetUrlSubmissionQuota", {"siteUrl": site}
    )
    raw = raw if isinstance(raw, dict) else {}
    return _response(
        {
            "site": site,
            "daily_quota": _integer(raw.get("DailyQuota")),
            "monthly_quota": _integer(raw.get("MonthlyQuota")),
        },
        tool="bing_url_submission_quota",
        params={"site": site},
        metadata={"quota_semantics": "unknown_total_or_remaining"},
    )
