"""Offline regressions for expert feedback on traffic and operator queries."""

import json
from datetime import date, timedelta

import pytest

from gsc_mcp.tools.seo import quick_wins, seo_cannibalization, traffic_drops

SITE = "https://www.twaino.com/"


@pytest.fixture(autouse=True)
def google_service(monkeypatch, mock_gsc_service):
    monkeypatch.setattr(
        "gsc_mcp.providers.google.get_searchconsole_service",
        lambda: mock_gsc_service,
    )


def query_row(query, clicks, impressions, position=3.0):
    return {
        "keys": [query],
        "clicks": clicks,
        "impressions": impressions,
        "ctr": clicks / impressions if impressions else 0.0,
        "position": position,
    }


def traffic_result(service, previous, current):
    service.searchanalytics.return_value.query.return_value.execute.side_effect = [
        {"rows": previous}, {"rows": current}
    ]
    return json.loads(traffic_drops(SITE))


def test_traffic_comparison_excludes_reporting_lag(monkeypatch, mock_gsc_service):
    class FixedDate(date):
        @classmethod
        def today(cls):
            return cls(2026, 10, 8)

    monkeypatch.setattr("gsc_mcp.tools.seo.date", FixedDate)
    result = traffic_result(mock_gsc_service, [], [])
    assert result["period_a"] == {"start": "2026-08-11", "end": "2026-09-07"}
    assert result["period_b"] == {"start": "2026-09-08", "end": "2026-10-05"}
    bodies = [call.kwargs["body"] for call in mock_gsc_service.searchanalytics.return_value.query.call_args_list]
    assert [(body["startDate"], body["endDate"]) for body in bodies] == [
        ("2026-08-11", "2026-09-07"), ("2026-09-08", "2026-10-05")
    ]


def test_historical_spike_missing_current_query_is_unavailable(mock_gsc_service):
    result = traffic_result(mock_gsc_service, [query_row("social blade", 588, 600)], [])
    assert result["drops"] == []
    unavailable = result["unavailable_queries"][0]
    assert unavailable["query"] == "social blade"
    assert unavailable["diagnosis"] == "unknown"
    assert unavailable["diagnosis_status"] == "insufficient_evidence"
    assert unavailable["reason"] == "current_query_not_returned"
    assert unavailable["metrics_previous"]["clicks"] == 588
    assert unavailable["metrics_current"] is None


def test_no_current_impressions_cannot_establish_ctr_collapse(mock_gsc_service):
    result = traffic_result(mock_gsc_service,
                            [query_row("social blade", 588, 600)],
                            [query_row("social blade", 0, 0)])
    drop = result["drops"][0]
    assert drop["diagnosis"] == "unknown"
    assert drop["diagnosis_status"] == "insufficient_evidence"
    assert drop["diagnosis_candidates"] == []
    assert drop["metrics_current"]["impressions"] == 0
    assert drop["metrics_current"]["ctr"] is None


def test_observed_ctr_decline_is_a_candidate_with_metrics(mock_gsc_service):
    result = traffic_result(mock_gsc_service,
                            [query_row("seo", 100, 1000)],
                            [query_row("seo", 40, 1000)])
    drop = result["drops"][0]
    assert drop["diagnosis"] == "ctr_collapse"
    assert drop["diagnosis_status"] == "candidate"
    assert drop["diagnosis_candidates"] == ["ctr_collapse"]
    assert drop["metrics_previous"]["ctr"] == 0.1
    assert drop["metrics_current"]["ctr"] == 0.04


def test_demand_decline_requires_observed_impression_decline(mock_gsc_service):
    result = traffic_result(mock_gsc_service,
                            [query_row("seo", 100, 1000)],
                            [query_row("seo", 90, 1000)])
    drop = result["drops"][0]
    assert drop["diagnosis"] == "unknown"
    assert drop["diagnosis_candidates"] == []


def test_concurrent_metric_changes_are_exposed_as_candidates(mock_gsc_service):
    result = traffic_result(mock_gsc_service,
                            [query_row("seo", 100, 1000)],
                            [query_row("seo", 20, 500, position=7.0)])
    drop = result["drops"][0]
    assert drop["diagnosis_status"] == "candidate"
    assert drop["diagnosis_candidates"] == ["ranking_loss", "ctr_collapse", "demand_decline"]


def page_rows(query):
    return [
        {**query_row(query, 50, 500), "keys": [query, SITE + suffix]}
        for suffix in ("a", "b")
    ]


@pytest.mark.parametrize("operator_query", [
    "site:www.twaino.com", "seo site:www.twaino.com", "SITE:www.twaino.com",
    "-site:www.twaino.com seo", "intitle:seo", "inurl:seo", "filetype:pdf seo",
])
def test_search_operator_queries_are_excluded_with_count(mock_gsc_service, operator_query):
    mock_gsc_service.searchanalytics.return_value.query.return_value.execute.return_value = {
        "rows": page_rows(operator_query) + page_rows("seo agency")
    }
    result = json.loads(seo_cannibalization(SITE))
    assert [conflict["query"] for conflict in result["conflicts"]] == ["seo agency"]
    assert result["excluded_search_operator_queries"] == 1


@pytest.mark.parametrize("query", ["site seo", "website:twaino", "intitle seo", "filetype pdf"])
def test_non_operator_words_remain_eligible(mock_gsc_service, query):
    mock_gsc_service.searchanalytics.return_value.query.return_value.execute.return_value = {
        "rows": page_rows(query)
    }
    result = json.loads(seo_cannibalization(SITE))
    assert result["conflicts"][0]["query"] == query


def test_search_operator_queries_can_be_explicitly_included(mock_gsc_service):
    mock_gsc_service.searchanalytics.return_value.query.return_value.execute.return_value = {
        "rows": page_rows("site:www.twaino.com")
    }
    result = json.loads(seo_cannibalization(SITE, include_search_operators=True))
    assert result["conflicts"][0]["query"] == "site:www.twaino.com"
    assert result["excluded_search_operator_queries"] == 0
    assert result["_meta"]["params"]["include_search_operators"] is True


def test_quick_wins_skips_bing_ctr_anomaly_and_reports_metric_unavailability(
    monkeypatch, mock_bing_client
):
    observed_date = (date.today() - timedelta(days=4)).isoformat()
    mock_bing_client.read.return_value = [
        {
            "Query": SITE + "anomaly",
            "Date": observed_date,
            "Clicks": 120,
            "Impressions": 100,
            "AvgImpressionPosition": 5,
            "AvgClickPosition": 5,
        },
        {
            "Query": SITE + "opportunity",
            "Date": observed_date,
            "Clicks": 1,
            "Impressions": 100,
            "AvgImpressionPosition": 5,
            "AvgClickPosition": 5,
        },
    ]
    monkeypatch.setattr(
        "gsc_mcp.providers.bing.get_bing_client", lambda: mock_bing_client
    )
    result = json.loads(quick_wins(SITE, engine="bing"))
    assert [row["page"] for row in result["opportunities"]] == [SITE + "opportunity"]
    assert result["opportunities"][0]["ctr"] == 0.01
    assert result["skipped_metric_rows"] == {"ctr_unavailable": 1}
