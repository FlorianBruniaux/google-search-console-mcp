"""Google Search Console adapter for normalized search metrics."""

from __future__ import annotations

from gsc_mcp.auth import get_searchconsole_service
from gsc_mcp.providers.base import (
    SearchMetricBatch,
    SearchMetricRow,
    UnsupportedProviderFeature,
)
from gsc_mcp.tools.analytics import _fetch_rows


_SUPPORTED_DIMENSIONS = frozenset(
    {"query", "page", "date", "country", "device"}
)
_COMMON_DIMENSIONS = frozenset({"query", "page", "date"})


class GoogleSearchProvider:
    def fetch(
        self,
        site: str,
        start_date: str,
        end_date: str,
        dimensions: tuple[str, ...],
    ) -> SearchMetricBatch:
        if not dimensions or not set(dimensions) <= _SUPPORTED_DIMENSIONS:
            raise UnsupportedProviderFeature(
                f"Google does not support dimensions {dimensions!r}"
            )

        rows = _fetch_rows(
            get_searchconsole_service(),
            site,
            {
                "startDate": start_date,
                "endDate": end_date,
                "dimensions": list(dimensions),
            },
        )
        normalized_rows = tuple(self._normalize_row(row) for row in rows)
        observed_dates = [
            row.date for row in normalized_rows if row.date is not None
        ]
        return SearchMetricBatch(
            engine="google",
            dimensions=dimensions,
            rows=normalized_rows,
            requested_start=start_date,
            requested_end=end_date,
            observed_start=min(observed_dates) if observed_dates else None,
            observed_end=max(observed_dates) if observed_dates else None,
            window_exact=True,
            position_semantics="google_average_position",
        )

    @staticmethod
    def _normalize_row(row: dict) -> SearchMetricRow:
        provider_metrics = {
            key: row.get(key)
            for key in row.keys() - _COMMON_DIMENSIONS
            if key not in {"clicks", "impressions", "ctr", "position"}
        }
        position = row.get("position")
        return SearchMetricRow(
            engine="google",
            date=row.get("date"),
            query=row.get("query"),
            page=row.get("page"),
            clicks=int(row.get("clicks", 0)),
            impressions=int(row.get("impressions", 0)),
            ctr=float(row.get("ctr", 0.0)),
            position=float(position) if position is not None else None,
            provider_metrics=provider_metrics,
        )
