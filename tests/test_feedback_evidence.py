"""Consumer regressions for reviewed expert-feedback provenance."""

import json
from datetime import date, timedelta

import pytest

from gsc_mcp.tools import bing_analytics, seo
from gsc_mcp.tools.search_compare import compare_search_engines

SITE = "https://example.com/"


def assert_basis(result, path, basis):
    record = result["_meta"]["evidence"]["fields"][path]
    assert record["basis"] == basis
    assert record["confidence_tier"] == {
        "measured": "observed", "derived": "calculated",
        "rule": "heuristic", None: "unavailable",
    }[basis]
    assert record["scope"]


def google_row(query, clicks, impressions, ctr, position=3.0):
    return {"keys": [query], "clicks": clicks, "impressions": impressions,
            "ctr": ctr, "position": position}


def install_google(monkeypatch, service, responses):
    monkeypatch.setattr("gsc_mcp.providers.google.get_searchconsole_service", lambda: service)
    service.searchanalytics.return_value.query.return_value.execute.side_effect = responses


def install_bing(monkeypatch, client, rows):
    client.read.return_value = rows
    monkeypatch.setattr("gsc_mcp.providers.bing.get_bing_client", lambda: client)
    monkeypatch.setattr(bing_analytics, "get_bing_client", lambda: client)


@pytest.mark.parametrize("current,diagnosis,basis", [
    (google_row("seo", 40, 1000, 0.04), "ctr_collapse", "rule"),
    (google_row("seo", 90, 1000, 0.09), "unknown", None),
    (google_row("seo", 0, 0, 0.0), "unknown", None),
])
def test_traffic_candidate_and_insufficient_evidence_are_distinct(
    monkeypatch, mock_gsc_service, current, diagnosis, basis
):
    install_google(monkeypatch, mock_gsc_service, [
        {"rows": [google_row("seo", 100, 1000, 0.1)]}, {"rows": [current]},
    ])
    result = json.loads(seo.traffic_drops(SITE))
    assert result["drops"][0]["diagnosis"] == diagnosis
    assert result["drops"][0]["clicks_delta"] == current["clicks"] - 100
    for key in ("diagnosis", "diagnosis_status", "diagnosis_candidates"):
        assert_basis(result, f"/drops/0/{key}", basis)
    for period in ("metrics_previous", "metrics_current"):
        for key in ("clicks", "impressions"):
            assert_basis(result, f"/drops/0/{period}/{key}", "measured")
    assert_basis(result, "/drops/0/metrics_previous/ctr", "measured")
    assert_basis(result, "/drops/0/metrics_current/ctr", "measured" if current["impressions"] else None)
    assert_basis(result, "/drops/0/clicks_delta", "derived")
    assert_basis(result, "/drops/0/impressions_delta", "derived")


def test_unreturned_current_query_cannot_support_diagnosis(monkeypatch, mock_gsc_service):
    install_google(monkeypatch, mock_gsc_service, [
        {"rows": [google_row("spike", 588, 600, 0.98)]}, {"rows": []},
    ])
    result = json.loads(seo.traffic_drops(SITE))
    assert result["unavailable_queries"][0]["metrics_previous"]["clicks"] == 588
    for key in ("diagnosis", "diagnosis_status", "diagnosis_candidates", "metrics_current"):
        assert_basis(result, f"/unavailable_queries/0/{key}", None)
    assert_basis(result, "/unavailable_queries/0/reason", "rule")
    assert_basis(result, "/unavailable_queries/0/metrics_previous/clicks", "measured")


@pytest.mark.parametrize("daily,counts_basis", [(False, "derived"), (True, "measured")])
def test_bing_query_counts_and_positions_follow_aggregation_scope(
    monkeypatch, mock_bing_client, daily, counts_basis
):
    observed = (date.today() - timedelta(days=4)).isoformat()
    install_bing(monkeypatch, mock_bing_client, [
        {"Query": "seo", "Date": observed, "Clicks": 1, "Impressions": 10,
         "AvgClickPosition": 3, "AvgImpressionPosition": 2},
        {"Query": "seo", "Date": observed, "Clicks": 3, "Impressions": 30,
         "AvgClickPosition": 7, "AvgImpressionPosition": 6},
    ])
    result = json.loads(bing_analytics.bing_query_stats(SITE, daily=daily))
    assert result["rows"][0]["clicks"] == (3 if daily else 4)
    assert result["rows"][0]["position"] == (6.0 if daily else 5.0)
    for key in ("clicks", "impressions", "position", "avg_click_position", "avg_impression_position"):
        assert_basis(result, f"/rows/0/{key}", counts_basis)
    assert_basis(result, "/rows/0/ctr", "derived")
    for path in ("/count", "/row_count", "/source_row_count", "/date_filtering/invalid_date_row_count"):
        assert_basis(result, path, "derived")
    assert_basis(result, "/local_truncated", "rule")


@pytest.mark.parametrize("tool,args", [
    (bing_analytics.bing_query_stats, {}),
    (bing_analytics.bing_page_stats, {}),
    (bing_analytics.bing_page_query_stats, {"page": SITE + "page"}),
    (bing_analytics.bing_rank_traffic_stats, {}),
])
def test_direct_bing_source_anomaly_evidence_preserves_counts(
    monkeypatch, mock_bing_client, tool, args
):
    observed = (date.today() - timedelta(days=4)).isoformat()
    install_bing(monkeypatch, mock_bing_client, [
        {"Query": "seo", "Date": observed, "Clicks": 3, "Impressions": 2,
         "AvgClickPosition": 3, "AvgImpressionPosition": 2},
        {"Query": "zero", "Date": observed, "Clicks": 0, "Impressions": 0},
    ])
    result = json.loads(tool(SITE, **args))
    assert result["rows"][0]["ctr"] is None
    assert_basis(result, "/rows/0/ctr", None)
    assert result["rows"][1]["ctr"] == 0.0
    assert_basis(result, "/rows/1/ctr", None)
    assert_basis(result, "/rows/0/metric_diagnostics/0/reason", "rule")
    assert_basis(result, "/rows/0/metric_diagnostics/0/raw_ratio", "derived")
    for key in ("clicks", "impressions"):
        assert_basis(result, f"/rows/0/metric_diagnostics/0/{key}", "measured")


def test_comparison_aggregated_counts_and_missing_zero_placeholders(monkeypatch, mock_gsc_service, mock_bing_client):
    install_google(monkeypatch, mock_gsc_service, [
        {"rows": [google_row("google-only", 1, 10, 0.1), google_row("google-zero", 0, 0, 0.0)]},
    ])
    install_bing(monkeypatch, mock_bing_client, [
        {"Query": "bing-only", "Date": (date.today() - timedelta(days=4)).isoformat(),
         "Clicks": 3, "Impressions": 2},
    ])
    result = json.loads(compare_search_engines(SITE, SITE))
    google_index = next(i for i, row in enumerate(result["rows"]) if row["query"] == "google-only")
    bing_index = next(i for i, row in enumerate(result["rows"]) if row["query"] == "bing-only")
    zero_index = next(i for i, row in enumerate(result["rows"]) if row["query"] == "google-zero")
    assert result["rows"][google_index]["bing"]["ctr"] == 0.0
    for engine, index in (("google", google_index), ("bing", bing_index)):
        for key in ("clicks", "impressions"):
            assert_basis(result, f"/rows/{index}/{engine}/{key}", "derived")
        assert_basis(result, f"/totals/{engine}/clicks", "derived")
    assert_basis(result, f"/rows/{bing_index}/bing/ctr", None)
    assert_basis(result, f"/rows/{google_index}/bing/ctr", None)
    assert_basis(result, f"/rows/{google_index}/bing/clicks", None)
    assert_basis(result, "/totals/bing/ctr", None)
    assert result["rows"][zero_index]["google"]["ctr"] == 0.0
    assert_basis(result, f"/rows/{zero_index}/google/ctr", None)
    assert_basis(result, f"/rows/{bing_index}/bing/metric_diagnostics/0/clicks", "measured")


def test_operator_filter_count_and_skipped_bing_ctr_are_calculations(monkeypatch, mock_gsc_service, mock_bing_client):
    rows = [
        {**google_row(query, 50, 500, 0.1), "keys": [query, SITE + page]}
        for query in ("site:example.com", "seo") for page in ("a", "b")
    ]
    install_google(monkeypatch, mock_gsc_service, [{"rows": rows}])
    result = json.loads(seo.seo_cannibalization(SITE))
    assert result["excluded_search_operator_queries"] == 1
    assert_basis(result, "/excluded_search_operator_queries", "derived")
    install_bing(monkeypatch, mock_bing_client, [
        {"Query": SITE + "anomaly", "Date": (date.today() - timedelta(days=4)).isoformat(),
         "Clicks": 120, "Impressions": 100, "AvgImpressionPosition": 5},
    ])
    result = json.loads(seo.quick_wins(SITE, engine="bing"))
    assert result["skipped_metric_rows"]["ctr_unavailable"] == 1
    assert_basis(result, "/skipped_metric_rows/ctr_unavailable", "derived")


@pytest.mark.parametrize("tool,args", [
    (bing_analytics.bing_query_stats, {}),
    (bing_analytics.bing_query_stats, {"daily": True}),
    (bing_analytics.bing_page_stats, {}),
    (bing_analytics.bing_page_query_stats, {"page": SITE + "page"}),
    (bing_analytics.bing_rank_traffic_stats, {}),
])
@pytest.mark.parametrize("source_key,metric", [("Clicks", "clicks"), ("Impressions", "impressions")])
@pytest.mark.parametrize("missing_value", ["absent", None])
def test_bing_missing_count_input_is_not_a_measured_zero(
    monkeypatch, mock_bing_client, tool, args, source_key, metric, missing_value
):
    raw = {"Query": "query or page", "Date": date.today().isoformat(),
           "Clicks": 1, "Impressions": 10,
           "AvgClickPosition": 3, "AvgImpressionPosition": 2}
    if missing_value == "absent":
        del raw[source_key]
    else:
        raw[source_key] = missing_value
    install_bing(monkeypatch, mock_bing_client, [raw])
    result = json.loads(tool(SITE, days=1, **args))
    assert result["rows"][0][metric] == 0
    assert result["rows"][0]["ctr"] is None
    assert metric in result["rows"][0]["unavailable_metrics"]
    assert not result["rows"][0].get("metric_diagnostics")
    assert_basis(result, f"/rows/0/{metric}", None)
    assert_basis(result, "/rows/0/ctr", None)
    if tool == bing_analytics.bing_query_stats and not args.get("daily"):
        weighted = "avg_click_position" if metric == "clicks" else "position"
        assert_basis(result, f"/rows/0/{weighted}", None)


@pytest.mark.parametrize("tool,args,counts_basis", [
    (bing_analytics.bing_query_stats, {}, "derived"),
    (bing_analytics.bing_query_stats, {"daily": True}, "measured"),
    (bing_analytics.bing_page_stats, {}, "measured"),
    (bing_analytics.bing_page_query_stats, {"page": SITE + "page"}, "measured"),
    (bing_analytics.bing_rank_traffic_stats, {}, "measured"),
])
def test_bing_explicit_count_zeros_remain_observations(
    monkeypatch, mock_bing_client, tool, args, counts_basis
):
    install_bing(monkeypatch, mock_bing_client, [
        {"Query": "zero", "Date": date.today().isoformat(), "Clicks": 0, "Impressions": 0},
    ])
    result = json.loads(tool(SITE, days=1, **args))
    assert result["rows"][0]["clicks"] == 0
    assert result["rows"][0]["impressions"] == 0
    assert not result["rows"][0].get("unavailable_metrics")
    assert_basis(result, "/rows/0/clicks", counts_basis)
    assert_basis(result, "/rows/0/impressions", counts_basis)
    assert_basis(result, "/rows/0/ctr", None)


@pytest.mark.parametrize("source_key,metric", [("Clicks", "clicks"), ("Impressions", "impressions")])
def test_bing_source_count_unavailability_survives_comparison_aggregation(
    monkeypatch, mock_gsc_service, mock_bing_client, source_key, metric
):
    install_google(monkeypatch, mock_gsc_service, [{"rows": [google_row("same", 1, 10, 0.1)]}])
    observed = (date.today() - timedelta(days=4)).isoformat()
    raw = {"Query": "same", "Date": observed, "Clicks": 1, "Impressions": 10,
           "AvgClickPosition": 3, "AvgImpressionPosition": 2}
    del raw[source_key]
    install_bing(monkeypatch, mock_bing_client, [
        raw, {"Query": "same", "Date": observed, "Clicks": 1, "Impressions": 10,
              "AvgClickPosition": 5, "AvgImpressionPosition": 4},
    ])
    result = json.loads(compare_search_engines(SITE, SITE))
    assert result["rows"][0]["bing"][metric] == (1 if metric == "clicks" else 10)
    assert result["rows"][0]["bing"]["ctr"] is None
    assert result["totals"]["bing"]["ctr"] is None
    assert_basis(result, f"/rows/0/bing/{metric}", None)
    assert_basis(result, f"/totals/bing/{metric}", None)
    assert_basis(result, "/rows/0/bing/ctr", None)
    assert not result["rows"][0]["bing"].get("metric_diagnostics")
