"""Read-only Bing Webmaster search performance tools."""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import date, timedelta

from gsc_mcp.meta import with_meta
from gsc_mcp.providers.bing import (
    BingSearchProvider,
    bing_row_ctr_metrics,
    get_bing_client,
    parse_bing_date,
)

_MAX_LIMIT = 10_000
_POSITION_SEMANTICS = {
    "position": "average_impression_position",
    "avg_click_position": "average_click_position",
    "avg_impression_position": "average_impression_position",
}
_POSITION_METRICS = {
    "measured": [
        "clicks",
        "impressions",
        "position",
        "avg_click_position",
        "avg_impression_position",
    ],
    "derived": ["ctr"],
}
_TRAFFIC_METRICS = {
    "measured": ["clicks", "impressions"],
    "derived": ["ctr"],
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


def _validate_page(page: int) -> None:
    if (
        not isinstance(page, int)
        or isinstance(page, bool)
        or not 0 <= page <= 32_767
    ):
        raise ValueError("page must be between 0 and 32767")


def _integer(value: object) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _nested_rows(raw: object, key: str) -> list[dict]:
    if not isinstance(raw, dict) or not isinstance(raw.get(key), list):
        return []
    return [row for row in raw[key] if isinstance(row, dict)]


def _requested_window(days: int) -> dict[str, object]:
    end = date.today()
    start = end - timedelta(days=days - 1)
    return {"start": start.isoformat(), "end": end.isoformat(), "days": days}


def _query_row(raw: dict, key_name: str) -> dict:
    impressions = int(raw.get("Impressions", 0) or 0)
    clicks = int(raw.get("Clicks", 0) or 0)
    raw_impression_position = raw.get("AvgImpressionPosition")
    raw_click_position = raw.get("AvgClickPosition")
    avg_impression_position = (
        round(float(raw_impression_position), 1)
        if raw_impression_position is not None else None
    )
    avg_click_position = (
        round(float(raw_click_position), 1)
        if raw_click_position is not None else None
    )
    metrics = bing_row_ctr_metrics(raw, clicks, impressions)
    observed_date = parse_bing_date(raw.get("Date"))
    for diagnostic in metrics.get("metric_diagnostics", []):
        diagnostic.update({"date": observed_date, key_name: raw.get("Query")})
    return {
        key_name: raw.get("Query"),
        "date": observed_date,
        "clicks": clicks,
        "impressions": impressions,
        **metrics,
        "position": avg_impression_position,
        "avg_click_position": avg_click_position,
        "avg_impression_position": avg_impression_position,
    }


def _traffic_row(raw: dict) -> dict:
    impressions = int(raw.get("Impressions", 0) or 0)
    clicks = int(raw.get("Clicks", 0) or 0)
    return {
        "date": parse_bing_date(raw.get("Date")),
        "clicks": clicks,
        "impressions": impressions,
        **bing_row_ctr_metrics(raw, clicks, impressions),
    }


def _rows_in_window(
    raw_rows: object,
    requested_window: dict[str, object],
    parser: Callable[[dict], dict],
) -> list[dict]:
    if not isinstance(raw_rows, list):
        return []

    start = str(requested_window["start"])
    end = str(requested_window["end"])
    rows = [parser(raw) for raw in raw_rows if isinstance(raw, dict)]
    return [
        row
        for row in rows
        if isinstance(row.get("date"), str) and start <= row["date"] <= end
    ]


def _observed_window(rows: list[dict]) -> dict[str, str | None]:
    dates = [row["date"] for row in rows if isinstance(row.get("date"), str)]
    return {
        "start": min(dates) if dates else None,
        "end": max(dates) if dates else None,
    }


def _response(
    *,
    data: dict,
    tool: str,
    params: dict,
    requested_window: dict[str, object],
    observed_rows: list[dict],
    position_semantics: dict[str, str] | str,
    metrics: dict[str, list[str]],
    extra_meta: dict | None = None,
) -> str:
    payload = with_meta(data, tool=tool, params=params)
    payload["_meta"].update(
        {
            "engine": "bing",
            "requested_window": requested_window,
            "observed_window": _observed_window(observed_rows),
            "position_semantics": position_semantics,
            "metrics": metrics,
            **(extra_meta or {}),
        }
    )
    return json.dumps(payload)


def _position_stats(
    *,
    method: str,
    site: str,
    days: int,
    limit: int,
    key_name: str,
    tool: str,
    extra_params: dict[str, object] | None = None,
    data: dict[str, object] | None = None,
    daily: bool = True,
) -> str:
    _validate_window(days)
    _validate_limit(limit)
    requested_window = _requested_window(days)
    api_params: dict[str, object] = {"siteUrl": site, **(extra_params or {})}
    raw_rows = get_bing_client().read(method, api_params)
    rows = _rows_in_window(
        raw_rows,
        requested_window,
        lambda raw: _query_row(raw, key_name),
    )
    observed_rows = rows
    query_data = {}
    if tool == "bing_query_stats":
        start, end = str(requested_window["start"]), str(requested_window["end"])
        source_rows = (
            [raw for raw in raw_rows if isinstance(raw, dict)]
            if isinstance(raw_rows, list) else []
        )
        dated_rows = [
            (raw, parse_bing_date(raw.get("Date"))) for raw in source_rows
        ]
        in_window = [
            (raw, observed) for raw, observed in dated_rows
            if observed is not None and start <= observed <= end
        ]
        diagnostics = [
            diagnostic for row in observed_rows
            for diagnostic in row.get("metric_diagnostics", [])
        ]
        if not daily:
            rows = [
                {
                    "query": row.query,
                    "date": None,
                    "clicks": row.clicks,
                    "impressions": row.impressions,
                    "ctr": row.ctr,
                    "position": row.position,
                    **row.to_dict()["provider_metrics"],
                }
                for row in BingSearchProvider._aggregate_positions(
                    in_window, "query"
                )
            ]
        query_data = {
            "aggregation_scope": "daily" if daily else "query",
            "source_row_count": len(in_window),
            "row_count": len(rows),
            "local_truncated": len(rows) > limit,
            "date_filtering": {
                "invalid_date_row_count": sum(
                    observed is None for _, observed in dated_rows
                ),
                "out_of_window_row_count": sum(
                    observed is not None and not start <= observed <= end
                    for _, observed in dated_rows
                ),
            },
            "metric_diagnostics": diagnostics,
        }
    rows.sort(key=lambda row: row["impressions"], reverse=True)
    visible_rows = rows[:limit]
    response_data = {
        "site": site,
        **(data or {}),
        **query_data,
        "count": len(visible_rows),
        "rows": visible_rows,
    }
    public_params = {"site": site, "days": days, "limit": limit}
    if data:
        public_params.update(data)
    extra_meta = {}
    if tool == "bing_query_stats":
        public_params["daily"] = daily
        extra_meta = {
            "window_exact": False,
            "provider_completeness": "UNKNOWN",
            "aggregation_semantics": {
                "scope": "daily" if daily else "query",
                "counts": (
                    "source_row" if daily
                    else "sum_of_dated_rows_in_requested_window"
                ),
                "ctr": (
                    "source_row_ratio_unavailable_on_anomaly" if daily
                    else "ratio_of_summed_counts_unavailable_on_source_anomaly"
                ),
                "avg_click_position": (
                    "source_average" if daily
                    else "click_weighted_over_rows_with_available_position"
                ),
                "avg_impression_position": (
                    "source_average" if daily
                    else "impression_weighted_over_rows_with_available_position"
                ),
            },
        }
    return _response(
        data=response_data,
        tool=tool,
        params=public_params,
        requested_window=requested_window,
        observed_rows=observed_rows,
        position_semantics=_POSITION_SEMANTICS,
        metrics=(
            {"measured": [], "derived": [
                *_POSITION_METRICS["measured"], *_POSITION_METRICS["derived"]
            ]}
            if tool == "bing_query_stats" and not daily
            else _POSITION_METRICS
        ),
        extra_meta=extra_meta,
    )


def bing_query_stats(
    site: str, days: int = 30, limit: int = 1000, daily: bool = False
) -> str:
    """Aggregate dated Bing rows by query within the requested local window.

    Limit applies after aggregation. CTR uses summed counts; positions use click
    or impression weights over rows with available positions. An anomalous
    source CTR makes the aggregate CTR unavailable. Use daily=True for the
    former individual dated rows. Provider completeness remains unknown.
    """
    if not isinstance(daily, bool):
        raise ValueError("daily must be a boolean")
    return _position_stats(
        method="GetQueryStats",
        site=site,
        days=days,
        limit=limit,
        key_name="query",
        tool="bing_query_stats",
        daily=daily,
    )


def bing_page_stats(site: str, days: int = 30, limit: int = 1000) -> str:
    """Return Bing page performance, normalizing Bing's Query field to page."""
    return _position_stats(
        method="GetPageStats",
        site=site,
        days=days,
        limit=limit,
        key_name="page",
        tool="bing_page_stats",
    )


def bing_page_query_stats(
    site: str,
    page: str,
    days: int = 30,
    limit: int = 1000,
) -> str:
    """Return Bing query performance for one requested page."""
    return _position_stats(
        method="GetPageQueryStats",
        site=site,
        days=days,
        limit=limit,
        key_name="query",
        tool="bing_page_query_stats",
        extra_params={"page": page},
        data={"page": page},
    )


def bing_rank_traffic_stats(site: str, days: int = 30) -> str:
    """Return Bing daily clicks and impressions without inventing rank fields."""
    _validate_window(days)
    requested_window = _requested_window(days)
    raw_rows = get_bing_client().read(
        "GetRankAndTrafficStats", {"siteUrl": site}
    )
    rows = _rows_in_window(raw_rows, requested_window, _traffic_row)
    rows.sort(key=lambda row: row["date"])
    return _response(
        data={"site": site, "count": len(rows), "rows": rows},
        tool="bing_rank_traffic_stats",
        params={"site": site, "days": days},
        requested_window=requested_window,
        observed_rows=rows,
        position_semantics="unavailable",
        metrics=_TRAFFIC_METRICS,
    )


def bing_link_counts(site: str, page: int = 0) -> str:
    """Return one Bing page of backlink counts from a synthetic shape."""
    _validate_page(page)
    raw = get_bing_client().read(
        "GetLinkCounts", {"siteUrl": site, "page": page}
    )
    raw_dict = raw if isinstance(raw, dict) else {}
    links = [
        {"url": row.get("Url"), "count": _integer(row.get("Count"))}
        for row in _nested_rows(raw_dict, "Links")
    ]
    payload = with_meta(
        {
            "site": site,
            "page": page,
            "links": links,
            "total_pages": _integer(raw_dict.get("TotalPages")),
        },
        tool="bing_link_counts",
        params={"site": site, "page": page},
    )
    payload["_meta"].update(
        {"engine": "bing", "contract_status": "UNVERIFIED_RUNTIME"}
    )
    return json.dumps(payload)


def bing_url_links(site: str, url: str, page: int = 0) -> str:
    """Return one Bing page of backlinks for the requested target URL."""
    _validate_page(page)
    raw = get_bing_client().read(
        "GetUrlLinks", {"siteUrl": site, "link": url, "page": page}
    )
    raw_dict = raw if isinstance(raw, dict) else {}
    details = [
        {"url": row.get("Url"), "anchor_text": row.get("AnchorText")}
        for row in _nested_rows(raw_dict, "Details")
    ]
    payload = with_meta(
        {
            "site": site,
            "url": url,
            "page": page,
            "details": details,
            "total_pages": _integer(raw_dict.get("TotalPages")),
        },
        tool="bing_url_links",
        params={"site": site, "url": url, "page": page},
    )
    payload["_meta"].update(
        {"engine": "bing", "contract_status": "UNVERIFIED_RUNTIME"}
    )
    return json.dumps(payload)
