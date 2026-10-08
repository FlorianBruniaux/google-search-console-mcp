"""Traffic comparisons retain missing data and only compare covered windows."""

import json
from unittest.mock import patch

import pytest
from google.analytics.data_v1beta.types import RunReportResponse, ResponseMetaData, Row

from gsc_mcp.tools.cross import traffic_health_check


SITE = "sc-domain:example.com"
WINDOW = {"start": "2026-09-08", "end": "2026-10-05"}


def gsc(rows=None, **updates):
    return {"site": SITE, "date_range": WINDOW, "rows": [{"clicks": 100}] if rows is None else rows, **updates}


def ga4(pages=None, **updates):
    pages = [{"sessions": 90}] if pages is None else pages
    return {
        "start_date": WINDOW["start"], "end_date": WINDOW["end"],
        "pages": pages, "count": len(pages),
        "coverage": {"row_count": len(pages), "returned_rows": len(pages), "complete": True,
                     "data_loss_from_other_row": False, "sampling": False, "subject_to_thresholding": False, "metric_restrictions": []},
        "time_zone": "Europe/Paris",
        "_meta": {"sources": {"ga4": {"property": "properties/123456789"}}},
        **updates,
    }


def run(gsc_data=None, ga4_data=None, **kwargs):
    with patch("gsc_mcp.tools.cross.get_search_analytics", return_value=json.dumps(gsc() if gsc_data is None else gsc_data)), \
         patch("gsc_mcp.tools.cross.ga4_organic_landing_pages", return_value=json.dumps(ga4() if ga4_data is None else ga4_data)):
        return json.loads(traffic_health_check(SITE, **kwargs))


def test_ga4_request_uses_concrete_gsc_dates_and_preserves_filters():
    with patch("gsc_mcp.tools.cross.get_search_analytics", return_value=json.dumps(gsc())) as search, \
         patch("gsc_mcp.tools.cross.ga4_organic_landing_pages", return_value=json.dumps(ga4())) as analytics:
        result = json.loads(traffic_health_check(SITE, property_id="123456789", hostname="example.com", country="France"))
    search.assert_called_once_with(SITE, 28, dimensions=[])
    assert analytics.call_args.kwargs == {
        "start_date": "2026-09-08", "end_date": "2026-10-05", "limit": 10000,
        "property_id": "123456789", "hostname": "example.com", "country": "France",
    }
    assert result["_meta"]["sources"]["ga4"] == {"property": "properties/123456789"}
    assert result["source_data"]["ga4"]["filters"] == {"hostname": "example.com", "country": "France", "session_medium": "organic"}
    assert result["source_data"]["ga4"]["requested_window"] == WINDOW
    assert result["source_data"]["gsc"]["site"] == SITE


@pytest.mark.parametrize("source", ["gsc", "ga4"])
def test_empty_rows_are_unknown_totals_not_measured_zero(source):
    result = run(gsc([]) if source == "gsc" else gsc(), ga4([]) if source == "ga4" else ga4())
    assert result["source_data"][source]["availability"] == "empty"
    assert result["total_gsc_clicks" if source == "gsc" else "total_ga4_sessions"] is None
    assert result["ratio"] is None
    assert result["status"] == "insufficient_data"


def test_explicit_zero_ga4_is_a_measurement():
    result = run(ga4_data=ga4([{"sessions": 0}]))
    assert result["source_data"]["ga4"]["availability"] == "measured"
    assert result["total_ga4_sessions"] == 0
    assert result["ratio"] == 0
    assert result["status"] == "tracking_gap"


def test_explicit_zero_gsc_is_available_with_null_ratio():
    result = run(gsc_data=gsc([{"clicks": 0}]))
    assert result["source_data"]["gsc"]["availability"] == "measured"
    assert result["total_gsc_clicks"] == 0
    assert result["ratio"] is None
    assert result["status"] == "no_gsc_data"
    assert "zero_gsc_clicks" in result["comparison"]["reasons"]


@pytest.mark.parametrize("source,exception,reason", [
    ("gsc", RuntimeError("No GSC config"), "configuration_error"),
    ("ga4", RuntimeError("No GA4 config"), "configuration_error"),
    ("gsc", OSError("upstream failed"), "upstream_error"),
    ("ga4", OSError("upstream failed"), "upstream_error"),
    ("ga4", RuntimeError("upstream failed"), "upstream_error"),
])
def test_source_errors_return_a_partial_report_without_ratio(source, exception, reason):
    with patch("gsc_mcp.tools.cross.get_search_analytics", return_value=json.dumps(gsc())) as search, \
         patch("gsc_mcp.tools.cross.ga4_organic_landing_pages", return_value=json.dumps(ga4())) as analytics:
        (search if source == "gsc" else analytics).side_effect = exception
        result = json.loads(traffic_health_check(SITE))
    assert result["source_data"][source]["availability"] == "unavailable"
    assert result["source_data"][source]["reason"] == reason
    assert result["ratio"] is None
    assert result["status"] == "source_unavailable"
    if source == "ga4":
        assert result["_meta"]["sources"]["ga4"] == {"property": None}


def test_mismatched_reported_ga4_dates_prevent_comparison():
    result = run(ga4_data=ga4(start_date="2026-09-09"))
    assert result["ratio"] is None
    assert result["status"] == "window_mismatch"
    assert result["source_data"]["ga4"]["reported_window"]["start"] == "2026-09-09"


@pytest.mark.parametrize("coverage", [None, {"complete": False}, {"complete": None},
    {"complete": True, "data_loss_from_other_row": True, "sampling": False},
    {"complete": True, "data_loss_from_other_row": False, "sampling": True},
    {"complete": True, "data_loss_from_other_row": None, "sampling": False},
    {"complete": True, "data_loss_from_other_row": False, "sampling": False, "subject_to_thresholding": True},
])
def test_unknown_truncated_or_sampled_ga4_coverage_prevents_comparison(coverage):
    if coverage is not None:
        coverage = {**ga4()["coverage"], **coverage}
    result = run(ga4_data=ga4(coverage=coverage))
    assert result["ratio"] is None
    assert result["status"] == "incomplete_coverage"


@pytest.mark.parametrize("filters", [{"country": "France"}, {"hostname": "blog.example.com"}, {"hostname": "example.com"}])
def test_ga4_filters_incompatible_with_unfiltered_domain_gsc_prevent_comparison(filters):
    result = run(**filters)
    assert result["ratio"] is None
    assert result["status"] == "incompatible_scope"


def test_missing_metric_does_not_become_zero():
    result = run(ga4_data=ga4([{"landing_page": "/"}]))
    assert result["total_ga4_sessions"] is None
    assert result["source_data"]["ga4"]["availability"] == "unknown"
    assert result["ratio"] is None


def test_unverified_calendar_and_property_mapping_are_disclosed():
    result = run()
    assert result["ratio"] == 0.9
    assert result["comparison"]["calendar_alignment"] == "unknown"
    assert result["comparison"]["property_mapping"] == "unverified"
    assert result["source_data"]["ga4"]["time_zone"] == "Europe/Paris"
    assert result["source_data"]["ga4"]["observed_window"] is None


def test_malformed_gsc_rows_remain_unknown_not_unavailable():
    result = run(gsc_data=gsc(rows=None, rows_invalid=True) | {"rows": None})
    assert result["source_data"]["gsc"]["availability"] == "unknown"
    assert result["total_gsc_clicks"] is None


def test_incompatible_reported_gsc_site_prevents_comparison():
    result = run(gsc_data=gsc(site="sc-domain:other.example"))
    assert result["source_data"]["gsc"]["reported_site"] == "sc-domain:other.example"
    assert result["status"] == "incompatible_scope"
    assert result["ratio"] is None


@pytest.mark.parametrize("reported", [{"start": "28daysAgo", "end": "today"},
    {"start": "2026-10-05", "end": "2026-09-08"}, {"start": "invalid", "end": "2026-10-05"}])
def test_invalid_gsc_window_is_not_forwarded_to_ga4(reported):
    with patch("gsc_mcp.tools.cross._date_range", return_value=("2026-09-08", "2026-10-05")), \
         patch("gsc_mcp.tools.cross.get_search_analytics", return_value=json.dumps(gsc(date_range=reported))), \
         patch("gsc_mcp.tools.cross.ga4_organic_landing_pages", return_value=json.dumps(ga4())) as analytics:
        result = json.loads(traffic_health_check(SITE))
    assert analytics.call_args.kwargs["start_date"] == "2026-09-08"
    assert analytics.call_args.kwargs["end_date"] == "2026-10-05"
    assert result["ratio"] is None
    assert result["status"] == "window_mismatch"


@pytest.mark.parametrize("metric", [None, -1, float("nan"), True, "0"])
def test_invalid_metrics_do_not_produce_numeric_comparisons(metric):
    result = run(ga4_data=ga4([{"sessions": metric}]))
    assert result["source_data"]["ga4"]["availability"] == "unknown"
    assert result["ratio"] is None


def test_multiple_gsc_aggregate_rows_prevent_comparison():
    result = run(gsc_data=gsc([{"clicks": 50}, {"clicks": 50}]))
    assert result["ratio"] is None
    assert result["status"] == "incomplete_coverage"


@pytest.mark.parametrize("site,wanted", [("https://example.com/", "healthy"),
    ("https://example.com/blog/", "incompatible_scope"), ("https://other.example/", "incompatible_scope")])
def test_hostname_filter_only_matches_the_same_root_url_prefix(site, wanted):
    with patch("gsc_mcp.tools.cross.get_search_analytics", return_value=json.dumps(gsc(site=site))), \
         patch("gsc_mcp.tools.cross.ga4_organic_landing_pages", return_value=json.dumps(ga4())):
        result = json.loads(traffic_health_check(site, hostname="example.com"))
    assert result["status"] == wanted


def test_real_child_tools_send_equal_dates_and_expose_complete_coverage(monkeypatch, mock_gsc_service, mock_ga4_service):
    from gsc_mcp.tools import analytics, ga4 as ga4_tools

    monkeypatch.setenv("GA4_PROPERTY_ID", "123456789")
    monkeypatch.setattr(analytics, "get_searchconsole_service", lambda: mock_gsc_service)
    monkeypatch.setattr(analytics, "_date_range", lambda days: ("2026-09-08", "2026-10-05"))
    monkeypatch.setattr(ga4_tools, "get_ga4_service", lambda: mock_ga4_service)
    mock_gsc_service.searchanalytics().query().execute.return_value = {"rows": [{"clicks": 100}]}
    mock_ga4_service.run_report.return_value = RunReportResponse(
        rows=[Row(dimension_values=[{"value": "/"}], metric_values=[{"value": value} for value in ("90", "60", "0.3", "20", "0", "0")])],
        row_count=1, metadata=ResponseMetaData(time_zone="Europe/Paris"),
    )
    result = json.loads(traffic_health_check(SITE))
    gsc_request = mock_gsc_service.searchanalytics().query.call_args.kwargs["body"]
    ga4_request = mock_ga4_service.run_report.call_args.args[0]
    assert (gsc_request["startDate"], gsc_request["endDate"]) == ("2026-09-08", "2026-10-05")
    assert (ga4_request.date_ranges[0].start_date, ga4_request.date_ranges[0].end_date) == ("2026-09-08", "2026-10-05")
    assert result["status"] == "healthy"
    assert result["ratio"] == 0.9


@pytest.mark.parametrize("source,gsc_row,ga4_sessions,availability,total,status,ratio", [
    ("ga4", {"clicks": 100}, "", "unknown", None, "insufficient_data", None),
    ("ga4", {"clicks": 100}, "invalid", "unknown", None, "insufficient_data", None),
    ("gsc", {"impressions": 50}, "90", "unknown", None, "insufficient_data", None),
    ("ga4", {"clicks": 100}, "0", "measured", 0, "tracking_gap", 0),
    ("gsc", {"clicks": 0}, "90", "measured", 0, "no_gsc_data", None),
])
def test_real_child_parsers_preserve_unknown_and_explicit_zero_measurements(
    monkeypatch, mock_gsc_service, mock_ga4_service, source, gsc_row, ga4_sessions, availability, total, status, ratio,
):
    from gsc_mcp.tools import analytics, ga4 as ga4_tools

    monkeypatch.setenv("GA4_PROPERTY_ID", "123456789")
    monkeypatch.setattr(analytics, "get_searchconsole_service", lambda: mock_gsc_service)
    monkeypatch.setattr(ga4_tools, "get_ga4_service", lambda: mock_ga4_service)
    mock_gsc_service.searchanalytics().query().execute.return_value = {"rows": [gsc_row]}
    mock_ga4_service.run_report.return_value = RunReportResponse(
        rows=[Row(dimension_values=[{"value": "/"}], metric_values=[
            {"value": value} for value in (ga4_sessions, "60", "0.3", "20", "0", "0")
        ])], row_count=1, metadata=ResponseMetaData(time_zone="Europe/Paris"),
    )
    result = json.loads(traffic_health_check(SITE))
    assert result["source_data"][source]["availability"] == availability
    assert result["total_gsc_clicks" if source == "gsc" else "total_ga4_sessions"] == total
    assert result["status"] == status
    assert result["ratio"] == ratio
