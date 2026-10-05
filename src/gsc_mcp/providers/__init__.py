"""Stable exports for external search providers."""

from gsc_mcp.providers.base import (
    SearchMetricBatch,
    SearchMetricRow,
    SearchMetricsProvider,
    UnsupportedProviderFeature,
)


def get_search_provider(engine: str) -> SearchMetricsProvider:
    if engine == "google":
        from gsc_mcp.providers.google import GoogleSearchProvider

        return GoogleSearchProvider()
    if engine == "bing":
        from gsc_mcp.providers.bing import BingSearchProvider

        return BingSearchProvider()
    raise ValueError("engine must be one of: google, bing")


__all__ = [
    "SearchMetricBatch",
    "SearchMetricRow",
    "SearchMetricsProvider",
    "UnsupportedProviderFeature",
    "get_search_provider",
]
