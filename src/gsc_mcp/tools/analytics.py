import json
import statistics
import math
from datetime import date, timedelta
from googleapiclient.errors import HttpError
from gsc_mcp.auth import get_searchconsole_service
from gsc_mcp.meta import with_meta
from gsc_mcp.retry import with_retry

_ANALYTICS_LAG_DAYS = 3
_DEFAULT_ROW_LIMIT = 1000
_MAX_ROWS_PER_PAGE = 25000
_MAX_PAGES = 40


def _date_range(days: int, lag: int = _ANALYTICS_LAG_DAYS) -> tuple[str, str]:
    end = date.today() - timedelta(days=lag)
    start = end - timedelta(days=days - 1)
    return start.isoformat(), end.isoformat()


def _parse_row(row: dict, dimensions: list[str]) -> dict:
    keys = row.get("keys", [])
    parsed = {dim: keys[i] if i < len(keys) else None for i, dim in enumerate(dimensions)}
    # An absent aggregate count is unknown, not evidence of zero traffic.
    parsed["clicks"] = row.get("clicks", None if not dimensions else 0)
    parsed["impressions"] = row.get("impressions", 0)
    parsed["ctr"] = round(row.get("ctr", 0.0), 4)
    parsed["position"] = round(row.get("position", 0.0), 1)
    return parsed


@with_retry()
def _fetch_rows(svc, site: str, body: dict, parser=None) -> list[dict]:
    rows: list[dict] = []
    start_row = 0
    pages_fetched = 0
    dimensions = body.get("dimensions", [])

    while pages_fetched < _MAX_PAGES:
        page_body = {**body, "startRow": start_row, "rowLimit": _MAX_ROWS_PER_PAGE}
        response = svc.searchanalytics().query(siteUrl=site, body=page_body).execute()
        if parser is not None and not isinstance(response, dict):
            raise _InvalidAppearanceResponse('invalid_response_container')
        page_rows = response.get("rows", [])
        if parser is not None and not isinstance(page_rows, list):
            raise _InvalidAppearanceResponse('invalid_rows_container')
        rows.extend([parser(r, dimensions) if parser is not None else _parse_row(r, dimensions) for r in page_rows])
        pages_fetched += 1
        if len(page_rows) < _MAX_ROWS_PER_PAGE:
            break
        start_row += len(page_rows)

    return rows


def get_search_analytics(
    site: str,
    days: int = 28,
    dimensions: list[str] | None = None,
    row_limit: int = _DEFAULT_ROW_LIMIT,
) -> str:
    """Fetch GSC search analytics (clicks, impressions, CTR, position) for a site.

    Groups results by the requested dimensions (query, page, device, country). Data has
    a 3-day reporting lag; the window covers the `days` days ending 3 days ago.
    """
    if dimensions is None:
        dimensions = ["query"]
    start, end = _date_range(days)
    svc = get_searchconsole_service()
    body = {
        "startDate": start,
        "endDate": end,
        "dimensions": dimensions,
        "rowLimit": row_limit,
    }
    rows = _fetch_rows(svc, site, body)
    return json.dumps(with_meta(
        {"site": site, "date_range": {"start": start, "end": end}, "rows": rows},
        tool="get_search_analytics",
        params={"site": site, "days": days, "dimensions": dimensions},
    ))


def get_performance_overview(site: str, days: int = 28) -> str:
    """Summarise total clicks, impressions, average CTR and average position for a site.

    Returns aggregate totals plus the top 10 queries by clicks over the rolling window.
    """
    start, end = _date_range(days)
    svc = get_searchconsole_service()
    totals_rows = _fetch_rows(svc, site, {"startDate": start, "endDate": end})
    query_rows = _fetch_rows(svc, site, {
        "startDate": start, "endDate": end, "dimensions": ["query"],
    })

    total_clicks = sum(r["clicks"] for r in totals_rows)
    total_impressions = sum(r["impressions"] for r in totals_rows)
    avg_ctr = round(total_clicks / total_impressions, 4) if total_impressions else 0.0
    avg_position = (
        round(sum(r["position"] * r["impressions"] for r in totals_rows) / total_impressions, 1)
        if total_impressions > 0 else 0.0
    )

    return json.dumps(with_meta(
        {
            "site": site,
            "date_range": {"start": start, "end": end},
            "totals": {
                "clicks": total_clicks,
                "impressions": total_impressions,
                "ctr": avg_ctr,
                "avg_position": avg_position,
            },
            "top_queries": query_rows[:10],
            "top_queries_scope": "Visible query rows can omit anonymized queries; totals use an ungrouped query.",
        },
        tool="get_performance_overview",
        params={"site": site, "days": days},
    ))


def compare_search_periods(site: str, days: int = 28) -> str:
    """Compare two consecutive equal-length windows and report delta in clicks and impressions.

    Period B is the most recent `days` days (with a 3-day lag). Period A is the
    `days` days immediately before that. Useful for week-over-week or month-over-month trends.
    """
    svc = get_searchconsole_service()

    end_b = date.today() - timedelta(days=_ANALYTICS_LAG_DAYS)
    start_b = end_b - timedelta(days=days - 1)
    end_a = start_b - timedelta(days=1)
    start_a = end_a - timedelta(days=days - 1)

    def fetch(start: date, end: date) -> list[dict]:
        body = {
            "startDate": start.isoformat(),
            "endDate": end.isoformat(),
        }
        return _fetch_rows(svc, site, body)

    rows_a = fetch(start_a, end_a)
    rows_b = fetch(start_b, end_b)

    totals_a = {"clicks": sum(r["clicks"] for r in rows_a), "impressions": sum(r["impressions"] for r in rows_a)}
    totals_b = {"clicks": sum(r["clicks"] for r in rows_b), "impressions": sum(r["impressions"] for r in rows_b)}

    return json.dumps(with_meta(
        {
            "site": site,
            "period_a": {"start": start_a.isoformat(), "end": end_a.isoformat(), **totals_a},
            "period_b": {"start": start_b.isoformat(), "end": end_b.isoformat(), **totals_b},
            "delta": {
                "clicks": totals_b["clicks"] - totals_a["clicks"],
                "impressions": totals_b["impressions"] - totals_a["impressions"],
            },
        },
        tool="compare_search_periods",
        params={"site": site, "days": days},
    ))


def get_search_by_page_query(site: str, days: int = 28, row_limit: int = _DEFAULT_ROW_LIMIT) -> str:
    """Fetch GSC data grouped by both page and query simultaneously.

    Useful for identifying which query drives which page and diagnosing on-page relevance issues.
    """
    start, end = _date_range(days)
    svc = get_searchconsole_service()
    body = {
        "startDate": start,
        "endDate": end,
        "dimensions": ["page", "query"],
        "rowLimit": row_limit,
    }
    raw_rows = _fetch_rows(svc, site, body)
    rows = [
        {
            "page": r.get("page"),
            "query": r.get("query"),
            "clicks": r["clicks"],
            "impressions": r["impressions"],
            "ctr": r["ctr"],
            "position": r["position"],
        }
        for r in raw_rows
    ]
    return json.dumps(with_meta(
        {"site": site, "date_range": {"start": start, "end": end}, "rows": rows},
        tool="get_search_by_page_query",
        params={"site": site, "days": days},
    ))


def analytics_anomalies(site: str, days: int = 90, threshold: float = 2.5) -> str:
    """Detect days with statistically abnormal click volumes using z-score analysis.

    A day is flagged as a spike or drop when abs(z_score) > threshold (default 2.5).
    Returns mean_daily_clicks, std_daily_clicks, and the list of anomalous days with their z-score.
    Use `days=90` or more for meaningful baseline statistics.
    """
    start, end = _date_range(days)
    svc = get_searchconsole_service()
    body = {
        "startDate": start,
        "endDate": end,
        "dimensions": ["date"],
        "rowLimit": _MAX_ROWS_PER_PAGE,
    }
    rows = _fetch_rows(svc, site, body)

    daily_clicks = [r["clicks"] for r in rows]

    if not daily_clicks:
        mean = 0.0
        std = 0.0
        anomalies: list[dict] = []
    else:
        mean = statistics.fmean(daily_clicks)
        std = statistics.pstdev(daily_clicks)
        anomalies = []
        if std > 0:
            for r in rows:
                clicks = r["clicks"]
                z = (clicks - mean) / std
                if abs(z) > threshold:
                    anomalies.append({
                        "date": r.get("date"),
                        "clicks": clicks,
                        "z_score": round(z, 2),
                        "type": "spike" if z > 0 else "drop",
                    })

    return json.dumps(with_meta(
        {
            "site": site,
            "date_range": {"start": start, "end": end},
            "mean_daily_clicks": round(mean, 1),
            "std_daily_clicks": round(std, 1),
            "threshold": threshold,
            "anomalies": anomalies,
        },
        tool="analytics_anomalies",
        params={"site": site, "days": days, "threshold": threshold},
    ))


def discover_performance(site: str, days: int = 28, limit: int = 50) -> str:
    """Get Discover performance: top pages by impressions (Discover does not support query dimension)."""
    start, end = _date_range(days)
    svc = get_searchconsole_service()
    body = {"startDate": start, "endDate": end, "dimensions": ["page"], "type": "discover"}
    rows = _fetch_rows(svc, site, body)
    rows.sort(key=lambda r: r["impressions"], reverse=True)
    return json.dumps(with_meta(
        {"site": site, "days": days, "count": len(rows[:limit]), "rows": rows[:limit]},
        tool="discover_performance",
        params={"site": site, "days": days, "limit": limit},
    ))


def news_performance(site: str, days: int = 28, limit: int = 50) -> str:
    """Get Google News performance: top pages by impressions (News does not support query dimension)."""
    start, end = _date_range(days)
    svc = get_searchconsole_service()
    body = {"startDate": start, "endDate": end, "dimensions": ["page"], "type": "googleNews"}
    rows = _fetch_rows(svc, site, body)
    rows.sort(key=lambda r: r["impressions"], reverse=True)
    return json.dumps(with_meta(
        {"site": site, "days": days, "count": len(rows[:limit]), "rows": rows[:limit]},
        tool="news_performance",
        params={"site": site, "days": days, "limit": limit},
    ))


def search_type_breakdown(site: str, url: str | None = None, days: int = 28) -> str:
    """Aggregate clicks and impressions broken down by search type for a site or specific URL.

    Makes one GSC call per search type (web, discover, googleNews, image, video) and returns
    total clicks and impressions for each. If `url` is provided, results are scoped to that page.
    """
    start, end = _date_range(days)
    svc = get_searchconsole_service()
    search_types = ["web", "discover", "googleNews", "image", "video"]
    breakdown = {}
    for stype in search_types:
        body = {"startDate": start, "endDate": end, "dimensions": ["page"], "type": stype}
        if url:
            body["dimensionFilterGroups"] = [{"filters": [{"dimension": "page", "expression": url}]}]
        rows = _fetch_rows(svc, site, body)
        breakdown[stype] = {
            "clicks": sum(r["clicks"] for r in rows),
            "impressions": sum(r["impressions"] for r in rows),
        }
    return json.dumps(with_meta(
        {"site": site, "days": days, "url": url, "breakdown": breakdown},
        tool="search_type_breakdown",
        params={"site": site, "url": url, "days": days},
    ))


class _InvalidAppearanceResponse(ValueError):
    pass


def _parse_appearance_row(row: dict, dimensions: list[str]) -> dict:
    """Preserve explicit zeros and distinguish absent, null and invalid values."""
    if not isinstance(row, dict):
        row = {}
    keys = row.get('keys')
    label = keys[0] if isinstance(keys, list) and len(keys) == 1 and isinstance(keys[0], str) and keys[0] else None
    parsed = {'searchAppearance': label}
    unavailable = {}
    for metric in ('clicks', 'impressions', 'ctr', 'position'):
        value = row.get(metric)
        if value is None:
            unavailable[metric] = 'null_provider_value' if metric in row else 'missing_provider_value'
        elif (type(value) not in (int, float) or not math.isfinite(value) or value < 0
              or (metric == 'ctr' and value > 1)):
            unavailable[metric] = 'invalid_provider_value'
            value = None
        elif metric in ('ctr', 'position'):
            value = round(value, 4 if metric == 'ctr' else 1)
        parsed[metric] = value
    if unavailable:
        parsed['unavailable_metrics'] = unavailable
    if label is None:
        parsed['dimension_status'] = 'missing_or_invalid'
    return parsed


def ai_overviews_impact(site: str, days: int = 28, limit: int = 100) -> str:
    """Discover generic Web search appearances; AI exposure remains unverified.

    The legacy name does not identify AI Overview queries or causal impact. Fetches
    searchAppearance alone, preserves returned metrics, and sorts by impressions.
    The window covers `days` days ending 3 days ago; dataState=all may be incomplete.
    HTTP 400 means invalid/unsupported request; 403 means access denied. Neither
    establishes whether this property appears in AI Overviews.
    """
    if type(days) is not int or not 1 <= days <= 366:
        raise ValueError('days must be an integer from 1 to 366')
    if type(limit) is not int or not 1 <= limit <= 25000:
        raise ValueError('limit must be an integer from 1 to 25000')
    start, end = _date_range(days)
    svc = get_searchconsole_service()
    body = {"startDate": start, "endDate": end, "dimensions": ["searchAppearance"],
            "type": "web", "dataState": "all"}
    data = {
        "site": site, "days": days, "date_range": {"start": start, "end": end},
        "source_scope": "web_search_appearance",
        "metric_origin": "explicit_provider_fields",
        "coverage": {"observed_window": None, "all_source_rows_guaranteed": False,
                     "data_state": "all", "provider_timezone": "America/Los_Angeles",
                     "request_date_clock": "server_local_date"},
        "ai_exposure": {"status": "unavailable", "verification": "unverified"},
        "evidence_limits": [
            "Returned rows describe generic Web search appearances, not AI exposure by query.",
            "No returned appearance label has a verified AI Overview mapping in this tool.",
            "Neither generic rows nor an empty result establish AI presence, absence or causal impact.",
            "No AI-attributed lost-click estimate or causal effect is identified.",
            "Search Console returns bounded top rows; dataState=all may include incomplete data.",
        ],
    }
    try:
        rows = _fetch_rows(svc, site, body, parser=_parse_appearance_row)
    except _InvalidAppearanceResponse:
        data.update({"error": "INVALID_SEARCH_APPEARANCE_RESPONSE", "source_status": "malformed_response"})
    except HttpError as e:
        if e.resp.status not in (400, 403):
            raise
        status = "invalid_or_unsupported_request" if e.resp.status == 400 else "access_denied"
        data.update({"error": "AI_OVERVIEWS_NOT_AVAILABLE", "reason": str(e),
                     "http_status": e.resp.status, "source_status": status, "error_meaning": status})
    else:
        rows.sort(key=lambda row: row.get("impressions") if row.get("impressions") is not None else -1, reverse=True)
        partial = sum(bool(row.get('unavailable_metrics') or row.get('dimension_status')) for row in rows)
        data['coverage'].update({'retrieved_rows': len(rows), 'partial_rows': partial,
                                 'display_truncated': len(rows) > limit})
        data.update({"site": site, "days": days, "count": len(rows[:limit]), "rows": rows[:limit],
                     "source_status": "partial" if partial else "observed" if rows else "empty"})
    return json.dumps(with_meta(data, tool="ai_overviews_impact",
                               params={"site": site, "days": days, "limit": limit},
                               sources={'google': {'site': site}}), allow_nan=False)


def get_advanced_search_analytics(
    site: str,
    dimensions: list[str] | None = None,
    date_range_days: int = 28,
    row_limit: int = _DEFAULT_ROW_LIMIT,
    search_type: str = "web",
    data_state: str | None = None,
) -> str:
    """Fetch GSC search analytics with full control over search_type, data_state, dimensions, and row limit.

    search_type: 'web' (default), 'image', 'video', or 'news'.
    data_state: 'final' (default, omit to use API default) or 'all' (includes fresh unverified data).
    dimensions: list of 'query', 'page', 'device', 'country', 'searchAppearance'.
    Use when get_search_analytics defaults are not sufficient.
    """
    if dimensions is None:
        dimensions = ["query"]
    start, end = _date_range(date_range_days)
    svc = get_searchconsole_service()

    body: dict = {
        "startDate": start,
        "endDate": end,
        "dimensions": dimensions,
        "type": search_type,
        "rowLimit": min(row_limit, _MAX_ROWS_PER_PAGE),
    }
    if data_state:
        body["dataState"] = data_state

    rows = _fetch_rows(svc, site, body)
    return json.dumps(with_meta(
        {
            "site": site,
            "date_range": {"start": start, "end": end},
            "search_type": search_type,
            "dimensions": dimensions,
            "rows": rows,
        },
        tool="get_advanced_search_analytics",
        params={"site": site, "dimensions": dimensions, "days": date_range_days},
    ))
