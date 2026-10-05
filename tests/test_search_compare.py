import json

import pytest

from gsc_mcp.providers.base import SearchMetricBatch, SearchMetricRow
from gsc_mcp.tools.search_compare import compare_search_engines


def _row(engine: str, dimension: str, value: str, **metrics) -> SearchMetricRow:
    values = {
        "clicks": 0,
        "impressions": 0,
        "ctr": 0.0,
        "position": None,
    }
    values.update(metrics)
    return SearchMetricRow(
        engine=engine,
        date=None,
        query=value if dimension == "query" else None,
        page=value if dimension == "page" else None,
        **values,
    )


def _batch(
    engine: str,
    dimension: str,
    rows: tuple[SearchMetricRow, ...],
    *,
    observed_start: str | None = "2026-01-01",
    observed_end: str | None = "2026-01-28",
    window_exact: bool = True,
) -> SearchMetricBatch:
    return SearchMetricBatch(
        engine=engine,
        dimensions=(dimension,),
        rows=rows,
        requested_start="2026-01-01",
        requested_end="2026-01-28",
        observed_start=observed_start,
        observed_end=observed_end,
        window_exact=window_exact,
        position_semantics=(
            "google_average_position"
            if engine == "google"
            else "bing_average_impression_position"
        ),
    )


def _install_providers(monkeypatch, google_batch, bing_batch):
    class Provider:
        def __init__(self, batch):
            self.batch = batch
            self.calls = []

        def fetch(self, site, start_date, end_date, dimensions):
            self.calls.append((site, start_date, end_date, dimensions))
            return self.batch

    providers = {
        "google": Provider(google_batch),
        "bing": Provider(bing_batch),
    }
    monkeypatch.setattr(
        "gsc_mcp.tools.search_compare.get_search_provider",
        providers.__getitem__,
    )
    monkeypatch.setattr(
        "gsc_mcp.tools.search_compare._date_range",
        lambda days: ("2026-01-01", "2026-01-28"),
    )
    return providers


def test_query_comparison_normalizes_aggregates_outer_joins_and_sorts(monkeypatch):
    google = _batch(
        "google",
        "query",
        (
            _row(
                "google",
                "query",
                " Alpha ",
                clicks=10,
                impressions=100,
                ctr=0.99,
                position=4.0,
            ),
            _row(
                "google",
                "query",
                "ALPHA",
                clicks=2,
                impressions=20,
                ctr=0.0,
                position=8.0,
            ),
            _row(
                "google",
                "query",
                "Beta",
                clicks=1,
                impressions=5,
                ctr=0.2,
                position=3.0,
            ),
        ),
    )
    bing = _batch(
        "bing",
        "query",
        (
            _row(
                "bing",
                "query",
                "alpha",
                clicks=7,
                impressions=140,
                ctr=0.75,
                position=5.1,
            ),
            _row(
                "bing",
                "query",
                " Gamma ",
                clicks=4,
                impressions=200,
                ctr=0.8,
                position=9.0,
            ),
        ),
    )
    providers = _install_providers(monkeypatch, google, bing)

    result = json.loads(
        compare_search_engines(
            "sc-domain:example.com",
            "https://example.com/",
            days=28,
            dimension="query",
            limit=100,
        )
    )

    assert [row["query"] for row in result["rows"]] == [
        "alpha",
        "gamma",
        "beta",
    ]
    alpha = result["rows"][0]
    assert alpha == {
        "query": "alpha",
        "google": {
            "present": True,
            "clicks": 12,
            "impressions": 120,
            "ctr": 0.1,
            "position": 4.7,
        },
        "bing": {
            "present": True,
            "clicks": 7,
            "impressions": 140,
            "ctr": 0.05,
            "position": 5.1,
        },
        "windows_comparable": True,
        "click_delta": -5,
        "impression_delta": 20,
    }
    assert result["rows"][1]["google"] == {
        "present": False,
        "clicks": 0,
        "impressions": 0,
        "ctr": 0.0,
        "position": None,
    }
    assert result["rows"][2]["bing"]["present"] is False
    assert result["totals"] == {
        "google": {"clicks": 13, "impressions": 125, "ctr": 0.104},
        "bing": {"clicks": 11, "impressions": 340, "ctr": 0.0324},
        "windows_comparable": True,
        "click_delta": -2,
        "impression_delta": 215,
    }
    assert result["metric_provenance"] == {
        "clicks": "measured",
        "impressions": "measured",
        "ctr": "derived_clicks_divided_by_impressions",
        "missing_row": "zero_filled_with_present_false",
        "position": {
            "google": "google_average_position",
            "bing": "bing_average_impression_position",
            "comparison": "side_by_side_only",
        },
    }
    assert "position_delta" not in json.dumps(result)
    assert result["recommendations"] == []
    assert providers["google"].calls == [
        (
            "sc-domain:example.com",
            "2026-01-01",
            "2026-01-28",
            ("query",),
        )
    ]
    assert providers["bing"].calls == [
        (
            "https://example.com/",
            "2026-01-01",
            "2026-01-28",
            ("query",),
        )
    ]


def test_page_comparison_normalizes_scheme_host_and_trailing_slash_only(
    monkeypatch,
):
    google = _batch(
        "google",
        "page",
        (
            _row(
                "google",
                "page",
                "HTTPS://Example.COM/Path/?ref=MixedCase",
                clicks=2,
                impressions=10,
                ctr=0.2,
                position=2.0,
            ),
        ),
    )
    bing = _batch(
        "bing",
        "page",
        (
            _row(
                "bing",
                "page",
                "https://example.com/Path?ref=MixedCase",
                clicks=1,
                impressions=20,
                ctr=0.05,
                position=4.0,
            ),
        ),
    )
    _install_providers(monkeypatch, google, bing)

    result = json.loads(
        compare_search_engines(
            "sc-domain:example.com",
            "https://example.com/",
            dimension="page",
        )
    )

    assert len(result["rows"]) == 1
    assert result["rows"][0]["page"] == (
        "https://example.com/Path?ref=MixedCase"
    )


def test_comparison_is_descriptive_when_observed_windows_are_not_exact(
    monkeypatch,
):
    google = _batch(
        "google",
        "query",
        (_row("google", "query", "alpha", clicks=3, impressions=10),),
        observed_start=None,
        observed_end=None,
    )
    bing = _batch(
        "bing",
        "query",
        (_row("bing", "query", "alpha", clicks=4, impressions=20),),
        window_exact=False,
    )
    _install_providers(monkeypatch, google, bing)

    result = json.loads(
        compare_search_engines(
            "sc-domain:example.com", "https://example.com/"
        )
    )

    assert result["windows_comparable"] is False
    assert result["reason"] == "observed_windows_differ"
    assert result["totals"]["windows_comparable"] is False
    assert result["totals"]["click_delta"] is None
    assert result["totals"]["impression_delta"] is None
    assert result["totals"]["reason"] == "observed_windows_differ"
    assert result["rows"][0]["click_delta"] is None
    assert result["rows"][0]["impression_delta"] is None
    assert result["rows"][0]["reason"] == "observed_windows_differ"
    assert result["observed_windows"] == {
        "google": {"start": None, "end": None, "exact": True},
        "bing": {
            "start": "2026-01-01",
            "end": "2026-01-28",
            "exact": False,
        },
    }


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"dimension": "date"}, "dimension must be query or page"),
        ({"days": 0}, "days must be at least 1"),
        ({"limit": 0}, "limit must be between 1 and 1000"),
        ({"limit": 1001}, "limit must be between 1 and 1000"),
    ],
)
def test_invalid_parameters_are_rejected_before_fetch(monkeypatch, kwargs, message):
    monkeypatch.setattr(
        "gsc_mcp.tools.search_compare.get_search_provider",
        lambda engine: pytest.fail("invalid input must not fetch providers"),
    )

    with pytest.raises(ValueError, match=message):
        compare_search_engines(
            "sc-domain:example.com", "https://example.com/", **kwargs
        )


def test_limit_is_applied_after_sorting(monkeypatch):
    google = _batch(
        "google",
        "query",
        (
            _row("google", "query", "low", impressions=2),
            _row("google", "query", "high", impressions=20),
        ),
    )
    bing = _batch("bing", "query", ())
    _install_providers(monkeypatch, google, bing)

    result = json.loads(
        compare_search_engines(
            "sc-domain:example.com",
            "https://example.com/",
            limit=1,
        )
    )

    assert result["row_count"] == 2
    assert result["returned_count"] == 1
    assert [row["query"] for row in result["rows"]] == ["high"]
    assert result["_meta"] == {
        "tool": "compare_search_engines",
        "params": {
            "google_site": "sc-domain:example.com",
            "bing_site": "https://example.com/",
            "days": 28,
            "dimension": "query",
            "limit": 1,
        },
    }
