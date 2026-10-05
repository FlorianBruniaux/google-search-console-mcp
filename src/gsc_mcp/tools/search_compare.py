"""Descriptive, evidence-bounded comparison of Google and Bing metrics."""

from __future__ import annotations

import json
from urllib.parse import urlsplit, urlunsplit

from gsc_mcp.meta import with_meta
from gsc_mcp.providers import get_search_provider
from gsc_mcp.providers.base import SearchMetricBatch, SearchMetricRow
from gsc_mcp.tools.analytics import _date_range


def _normalize_dimension(value: str, dimension: str) -> str:
    if dimension == "query":
        return value.strip().casefold()

    parsed = urlsplit(value.strip())
    return urlunsplit(
        (
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            parsed.path.rstrip("/"),
            parsed.query,
            parsed.fragment,
        )
    )


def _aggregate_rows(
    batch: SearchMetricBatch, dimension: str
) -> dict[str, dict[str, int | float | None | bool]]:
    aggregates: dict[str, dict[str, int | float]] = {}
    for row in batch.rows:
        raw_value = getattr(row, dimension)
        if raw_value is None:
            continue
        key = _normalize_dimension(raw_value, dimension)
        aggregate = aggregates.setdefault(
            key,
            {
                "clicks": 0,
                "impressions": 0,
                "position_total": 0.0,
                "position_weight": 0,
            },
        )
        aggregate["clicks"] += row.clicks
        aggregate["impressions"] += row.impressions
        if row.position is not None and row.impressions:
            aggregate["position_total"] += row.position * row.impressions
            aggregate["position_weight"] += row.impressions

    results = {}
    for key, aggregate in aggregates.items():
        clicks = int(aggregate["clicks"])
        impressions = int(aggregate["impressions"])
        position_weight = int(aggregate["position_weight"])
        results[key] = {
            "present": True,
            "clicks": clicks,
            "impressions": impressions,
            "ctr": round(clicks / impressions, 4) if impressions else 0.0,
            "position": (
                round(
                    float(aggregate["position_total"]) / position_weight,
                    1,
                )
                if position_weight
                else None
            ),
        }
    return results


def _missing_metrics() -> dict[str, int | float | None | bool]:
    return {
        "present": False,
        "clicks": 0,
        "impressions": 0,
        "ctr": 0.0,
        "position": None,
    }


def _windows_comparable(
    google: SearchMetricBatch, bing: SearchMetricBatch
) -> bool:
    return bool(
        google.window_exact
        and bing.window_exact
        and google.observed_start is not None
        and google.observed_end is not None
        and google.observed_start == bing.observed_start
        and google.observed_end == bing.observed_end
    )


def _comparison_fields(
    google: dict[str, int | float | None | bool],
    bing: dict[str, int | float | None | bool],
    comparable: bool,
) -> dict[str, bool | int | None | str]:
    both_present = bool(
        google.get("present", True) and bing.get("present", True)
    )
    can_calculate_delta = comparable and both_present
    fields: dict[str, bool | int | None | str] = {
        "windows_comparable": comparable,
        "click_delta": (
            int(bing["clicks"]) - int(google["clicks"])
            if can_calculate_delta
            else None
        ),
        "impression_delta": (
            int(bing["impressions"]) - int(google["impressions"])
            if can_calculate_delta
            else None
        ),
    }
    if not comparable:
        fields["reason"] = "observed_windows_differ"
    elif not both_present:
        fields["reason"] = "dimension_not_present_in_both_providers"
    return fields


def _totals(
    metrics: dict[str, dict[str, int | float | None | bool]],
) -> dict[str, int | float]:
    clicks = sum(int(row["clicks"]) for row in metrics.values())
    impressions = sum(int(row["impressions"]) for row in metrics.values())
    return {
        "clicks": clicks,
        "impressions": impressions,
        "ctr": round(clicks / impressions, 4) if impressions else 0.0,
    }


def compare_search_engines(
    google_site: str,
    bing_site: str,
    days: int = 28,
    dimension: str = "query",
    limit: int = 100,
) -> str:
    """Compare Google and Bing query or page metrics without inferring causality.

    Click and impression deltas are returned only when both providers expose the
    same exact observed window. Positions remain side by side because the two
    providers use different position semantics.
    """
    if dimension not in ("query", "page"):
        raise ValueError("dimension must be query or page")
    if days < 1:
        raise ValueError("days must be at least 1")
    if not 1 <= limit <= 1000:
        raise ValueError("limit must be between 1 and 1000")

    start_date, end_date = _date_range(days)
    dimensions = (dimension,)
    google_batch = get_search_provider("google").fetch(
        google_site, start_date, end_date, dimensions
    )
    bing_batch = get_search_provider("bing").fetch(
        bing_site, start_date, end_date, dimensions
    )

    google_metrics = _aggregate_rows(google_batch, dimension)
    bing_metrics = _aggregate_rows(bing_batch, dimension)
    comparable = _windows_comparable(google_batch, bing_batch)

    rows = []
    for key in google_metrics.keys() | bing_metrics.keys():
        google_row = google_metrics.get(key, _missing_metrics())
        bing_row = bing_metrics.get(key, _missing_metrics())
        rows.append(
            {
                dimension: key,
                "google": google_row,
                "bing": bing_row,
                **_comparison_fields(google_row, bing_row, comparable),
            }
        )
    rows.sort(
        key=lambda row: (
            -int(row["google"]["impressions"])
            - int(row["bing"]["impressions"]),
            str(row[dimension]),
        )
    )

    google_totals = _totals(google_metrics)
    bing_totals = _totals(bing_metrics)
    comparison = _comparison_fields(google_totals, bing_totals, comparable)
    data = {
        "google_site": google_site,
        "bing_site": bing_site,
        "dimension": dimension,
        "requested_window": {
            "start": start_date,
            "end": end_date,
            "days": days,
        },
        "observed_windows": {
            "google": {
                "start": google_batch.observed_start,
                "end": google_batch.observed_end,
                "exact": google_batch.window_exact,
            },
            "bing": {
                "start": bing_batch.observed_start,
                "end": bing_batch.observed_end,
                "exact": bing_batch.window_exact,
            },
        },
        "windows_comparable": comparable,
        **({} if comparable else {"reason": "observed_windows_differ"}),
        "metric_provenance": {
            "clicks": "measured",
            "impressions": "measured",
            "ctr": "derived_clicks_divided_by_impressions",
            "missing_row": "zero_filled_with_present_false",
            "position": {
                "google": google_batch.position_semantics,
                "bing": bing_batch.position_semantics,
                "comparison": "side_by_side_only",
            },
        },
        "totals": {
            "google": google_totals,
            "bing": bing_totals,
            **comparison,
        },
        "row_count": len(rows),
        "returned_count": len(rows[:limit]),
        "rows": rows[:limit],
        "recommendations": [],
    }
    return json.dumps(
        with_meta(
            data,
            tool="compare_search_engines",
            params={
                "google_site": google_site,
                "bing_site": bing_site,
                "days": days,
                "dimension": dimension,
                "limit": limit,
            },
        )
    )
