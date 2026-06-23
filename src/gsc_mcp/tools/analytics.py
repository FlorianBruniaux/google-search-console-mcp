import json
import statistics
from datetime import date, timedelta
from gsc_mcp.auth import get_searchconsole_service
from gsc_mcp.meta import with_meta
from gsc_mcp.retry import with_retry

_ANALYTICS_LAG_DAYS = 3
_DEFAULT_ROW_LIMIT = 1000
_MAX_ROWS_PER_PAGE = 25000


def _date_range(days: int, lag: int = _ANALYTICS_LAG_DAYS) -> tuple[str, str]:
    end = date.today() - timedelta(days=lag)
    start = end - timedelta(days=days - 1)
    return start.isoformat(), end.isoformat()


def _parse_row(row: dict, dimensions: list[str]) -> dict:
    keys = row.get("keys", [])
    parsed = {dim: keys[i] if i < len(keys) else None for i, dim in enumerate(dimensions)}
    parsed["clicks"] = row.get("clicks", 0)
    parsed["impressions"] = row.get("impressions", 0)
    parsed["ctr"] = round(row.get("ctr", 0.0), 4)
    parsed["position"] = round(row.get("position", 0.0), 1)
    return parsed


@with_retry()
def _fetch_rows(svc, site: str, body: dict) -> list[dict]:
    rows: list[dict] = []
    start_row = 0
    dimensions = body.get("dimensions", ["query"])

    while True:
        page_body = {**body, "startRow": start_row, "rowLimit": _MAX_ROWS_PER_PAGE}
        response = svc.searchanalytics().query(siteUrl=site, body=page_body).execute()
        page_rows = response.get("rows", [])
        rows.extend([_parse_row(r, dimensions) for r in page_rows])
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
    body = {"startDate": start, "endDate": end, "dimensions": ["query"], "rowLimit": _MAX_ROWS_PER_PAGE}
    rows = _fetch_rows(svc, site, body)

    total_clicks = sum(r["clicks"] for r in rows)
    total_impressions = sum(r["impressions"] for r in rows)
    avg_ctr = round(total_clicks / total_impressions, 4) if total_impressions else 0.0
    avg_position = round(sum(r["position"] for r in rows) / len(rows), 1) if rows else 0.0

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
            "top_queries": rows[:10],
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
            "dimensions": ["query"],
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
