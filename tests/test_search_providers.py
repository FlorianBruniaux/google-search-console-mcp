import json
from dataclasses import FrozenInstanceError, asdict
from unittest.mock import MagicMock

import pytest

from gsc_mcp.providers import get_search_provider
from gsc_mcp.providers.base import (
    SearchMetricBatch,
    SearchMetricRow,
    UnsupportedProviderFeature,
)
from gsc_mcp.providers.bing import BingSearchProvider
from gsc_mcp.providers.google import GoogleSearchProvider


SITE = "https://example.com/"


def _metric_row(**overrides):
    values = {
        "engine": "google",
        "date": None,
        "query": "example query",
        "page": None,
        "clicks": 2,
        "impressions": 10,
        "ctr": 0.2,
        "position": 4.5,
    }
    values.update(overrides)
    return SearchMetricRow(**values)


def test_metric_models_are_frozen_and_serialize_to_plain_dicts():
    row = _metric_row(provider_metrics={"country": "fra"})
    batch = SearchMetricBatch(
        engine="google",
        dimensions=("query",),
        rows=(row,),
        requested_start="2026-01-01",
        requested_end="2026-01-31",
        observed_start=None,
        observed_end=None,
        window_exact=True,
        position_semantics="google_average_position",
    )

    with pytest.raises(FrozenInstanceError):
        row.clicks = 3
    with pytest.raises(FrozenInstanceError):
        batch.window_exact = False

    assert asdict(batch) == {
        "engine": "google",
        "dimensions": ("query",),
        "rows": (
            {
                "engine": "google",
                "date": None,
                "query": "example query",
                "page": None,
                "clicks": 2,
                "impressions": 10,
                "ctr": 0.2,
                "position": 4.5,
                "provider_metrics": {"country": "fra"},
            },
        ),
        "requested_start": "2026-01-01",
        "requested_end": "2026-01-31",
        "observed_start": None,
        "observed_end": None,
        "window_exact": True,
        "position_semantics": "google_average_position",
    }
    assert json.loads(json.dumps(asdict(batch)))["rows"][0][
        "provider_metrics"
    ] == {"country": "fra"}
    assert json.loads(json.dumps(batch.to_dict()))["rows"][0][
        "provider_metrics"
    ] == {"country": "fra"}


def test_provider_metrics_are_deeply_immutable_and_json_serializable():
    source = {
        "country": "fra",
        "segments": {"devices": ["mobile"]},
    }
    row = _metric_row(provider_metrics=source)
    source["country"] = "usa"
    source["segments"]["devices"].append("desktop")

    with pytest.raises(TypeError):
        row.provider_metrics["country"] = "usa"
    with pytest.raises(TypeError):
        row.provider_metrics["segments"]["devices"] = ("desktop",)

    assert json.loads(json.dumps(row.to_dict()))["provider_metrics"] == {
        "country": "fra",
        "segments": {"devices": ["mobile"]},
    }


@pytest.mark.parametrize(
    "overrides",
    [
        {"engine": "other"},
        {"clicks": -1},
        {"impressions": -1},
        {"ctr": -0.01},
        {"ctr": 1.01},
    ],
)
def test_metric_row_rejects_invalid_values(overrides):
    with pytest.raises(ValueError):
        _metric_row(**overrides)


def test_metric_batch_rejects_unknown_engine():
    with pytest.raises(ValueError, match="google or bing"):
        SearchMetricBatch(
            engine="other",
            dimensions=("query",),
            rows=(),
            requested_start="2026-01-01",
            requested_end="2026-01-31",
            observed_start=None,
            observed_end=None,
            window_exact=True,
            position_semantics="unknown",
        )


def test_get_search_provider_returns_supported_provider_and_rejects_unknown():
    assert isinstance(get_search_provider("google"), GoogleSearchProvider)
    assert isinstance(get_search_provider("bing"), BingSearchProvider)

    with pytest.raises(ValueError, match="google, bing"):
        get_search_provider("other")


def test_google_query_fetch_keeps_requested_bounds_distinct_from_observed(
    monkeypatch,
):
    service = MagicMock()
    monkeypatch.setattr(
        "gsc_mcp.providers.google.get_searchconsole_service", lambda: service
    )
    monkeypatch.setattr(
        "gsc_mcp.providers.google._fetch_rows",
        lambda svc, site, body: [
            {
                "query": "example query",
                "clicks": 3,
                "impressions": 20,
                "ctr": 0.15,
                "position": 6.2,
            }
        ],
    )

    batch = GoogleSearchProvider().fetch(
        SITE,
        "2026-01-01",
        "2026-01-31",
        dimensions=("query",),
    )

    assert batch == SearchMetricBatch(
        engine="google",
        dimensions=("query",),
        rows=(
            SearchMetricRow(
                engine="google",
                date=None,
                query="example query",
                page=None,
                clicks=3,
                impressions=20,
                ctr=0.15,
                position=6.2,
            ),
        ),
        requested_start="2026-01-01",
        requested_end="2026-01-31",
        observed_start=None,
        observed_end=None,
        window_exact=True,
        position_semantics="google_average_position",
    )


@pytest.mark.parametrize(
    ("dimensions", "raw_row", "expected_metrics"),
    [
        (
            ("page", "query"),
            {
                "page": "https://example.com/page",
                "query": "example query",
                "clicks": 1,
                "impressions": 2,
                "ctr": 0.5,
                "position": 3.0,
            },
            {},
        ),
        (
            ("country", "device"),
            {
                "country": "fra",
                "device": "mobile",
                "clicks": 1,
                "impressions": 2,
                "ctr": 0.5,
                "position": 3.0,
            },
            {"country": "fra", "device": "mobile"},
        ),
    ],
)
def test_google_fetch_supports_google_dimensions(
    monkeypatch, dimensions, raw_row, expected_metrics
):
    monkeypatch.setattr(
        "gsc_mcp.providers.google.get_searchconsole_service", MagicMock
    )
    monkeypatch.setattr(
        "gsc_mcp.providers.google._fetch_rows",
        lambda svc, site, body: [raw_row],
    )

    batch = GoogleSearchProvider().fetch(
        SITE, "2026-01-01", "2026-01-31", dimensions=dimensions
    )

    assert batch.rows[0].provider_metrics == expected_metrics


def test_google_date_fetch_reports_only_observed_dates(monkeypatch):
    monkeypatch.setattr(
        "gsc_mcp.providers.google.get_searchconsole_service", MagicMock
    )
    monkeypatch.setattr(
        "gsc_mcp.providers.google._fetch_rows",
        lambda svc, site, body: [
            {
                "date": "2026-01-20",
                "clicks": 1,
                "impressions": 2,
                "ctr": 0.5,
                "position": 3.0,
            },
            {
                "date": "2026-01-10",
                "clicks": 2,
                "impressions": 4,
                "ctr": 0.5,
                "position": 4.0,
            },
        ],
    )

    batch = GoogleSearchProvider().fetch(
        SITE, "2026-01-01", "2026-01-31", dimensions=("date",)
    )

    assert batch.observed_start == "2026-01-10"
    assert batch.observed_end == "2026-01-20"


def test_bing_rejects_bulk_page_query_before_getting_a_client(monkeypatch):
    monkeypatch.setattr(
        "gsc_mcp.providers.bing.get_bing_client",
        lambda: pytest.fail("unsupported dimensions must not call Bing"),
    )

    with pytest.raises(UnsupportedProviderFeature, match="page.*query"):
        BingSearchProvider().fetch(
            SITE,
            "2026-01-01",
            "2026-01-31",
            dimensions=("page", "query"),
        )


def test_bing_query_fetch_filters_locally_and_aggregates_duplicate_dimensions(
    monkeypatch,
):
    client = MagicMock()
    client.read.return_value = [
        {
            "Query": "same query",
            "Date": "2025-12-31",
            "Clicks": 99,
            "Impressions": 100,
            "AvgClickPosition": 1,
            "AvgImpressionPosition": 1,
        },
        {
            "Query": "same query",
            "Date": "2026-01-01",
            "Clicks": 1,
            "Impressions": 100,
            "AvgClickPosition": 5,
            "AvgImpressionPosition": 2,
        },
        {
            "Query": "same query",
            "Date": "2026-01-02",
            "Clicks": 9,
            "Impressions": 10,
            "AvgClickPosition": 9,
            "AvgImpressionPosition": 4,
        },
    ]
    monkeypatch.setattr(
        "gsc_mcp.providers.bing.get_bing_client", lambda: client
    )

    batch = BingSearchProvider().fetch(
        SITE, "2026-01-01", "2026-01-31", dimensions=("query",)
    )

    assert batch == SearchMetricBatch(
        engine="bing",
        dimensions=("query",),
        rows=(
            SearchMetricRow(
                engine="bing",
                date=None,
                query="same query",
                page=None,
                clicks=10,
                impressions=110,
                ctr=0.0909,
                position=2.2,
                provider_metrics={
                    "avg_click_position": 8.6,
                    "avg_impression_position": 2.2,
                },
            ),
        ),
        requested_start="2026-01-01",
        requested_end="2026-01-31",
        observed_start="2026-01-01",
        observed_end="2026-01-02",
        window_exact=False,
        position_semantics="bing_average_impression_position",
    )
    client.read.assert_called_once_with(
        "GetQueryStats", {"siteUrl": SITE}
    )


def test_bing_query_fetch_does_not_invent_click_position_without_clicks(
    monkeypatch,
):
    client = MagicMock()
    client.read.return_value = [
        {
            "Query": "zero click query",
            "Date": "2026-01-01",
            "Clicks": 0,
            "Impressions": 20,
            "AvgClickPosition": 7,
            "AvgImpressionPosition": 3,
        }
    ]
    monkeypatch.setattr(
        "gsc_mcp.providers.bing.get_bing_client", lambda: client
    )

    batch = BingSearchProvider().fetch(
        SITE, "2026-01-01", "2026-01-31", dimensions=("query",)
    )

    assert batch.rows[0].provider_metrics["avg_click_position"] is None


def test_bing_page_fetch_maps_query_field_to_page(monkeypatch):
    client = MagicMock()
    client.read.return_value = [
        {
            "Query": "https://example.com/page",
            "Date": "2026-01-03",
            "Clicks": 2,
            "Impressions": 10,
            "AvgClickPosition": 6,
            "AvgImpressionPosition": 5,
        }
    ]
    monkeypatch.setattr(
        "gsc_mcp.providers.bing.get_bing_client", lambda: client
    )

    batch = BingSearchProvider().fetch(
        SITE, "2026-01-01", "2026-01-31", dimensions=("page",)
    )

    assert batch.rows[0].page == "https://example.com/page"
    assert batch.rows[0].query is None
    client.read.assert_called_once_with("GetPageStats", {"siteUrl": SITE})


def test_bing_date_fetch_aggregates_duplicates_without_position(monkeypatch):
    client = MagicMock()
    client.read.return_value = [
        {"Date": "2026-01-03", "Clicks": 1, "Impressions": 4},
        {"Date": "2026-01-03", "Clicks": 2, "Impressions": 6},
    ]
    monkeypatch.setattr(
        "gsc_mcp.providers.bing.get_bing_client", lambda: client
    )

    batch = BingSearchProvider().fetch(
        SITE, "2026-01-01", "2026-01-31", dimensions=("date",)
    )

    assert batch.rows == (
        SearchMetricRow(
            engine="bing",
            date="2026-01-03",
            query=None,
            page=None,
            clicks=3,
            impressions=10,
            ctr=0.3,
            position=None,
        ),
    )
    assert batch.position_semantics == "unavailable"
    assert batch.window_exact is False
    client.read.assert_called_once_with(
        "GetRankAndTrafficStats", {"siteUrl": SITE}
    )
