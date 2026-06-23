import json
import pytest
from datetime import date, timedelta
from unittest.mock import patch
from gsc_mcp.tools.analytics import (
    get_search_analytics,
    get_performance_overview,
    compare_search_periods,
    get_search_by_page_query,
    get_advanced_search_analytics,
    analytics_anomalies,
    discover_performance,
)

SITE = "https://example.com/"

_ROW = {"keys": ["query1"], "clicks": 100, "impressions": 1000, "ctr": 0.1, "position": 3.0}


def _mock_response(rows):
    return {"rows": rows}


def test_get_search_analytics(mock_gsc_service):
    mock_gsc_service.searchanalytics.return_value.query.return_value.execute.return_value = (
        _mock_response([_ROW])
    )
    with patch("gsc_mcp.tools.analytics.get_searchconsole_service", return_value=mock_gsc_service):
        result = json.loads(get_search_analytics(SITE))
    assert result["site"] == SITE
    assert len(result["rows"]) == 1
    assert result["rows"][0]["query"] == "query1"
    assert "_meta" in result


def test_get_search_analytics_empty(mock_gsc_service):
    mock_gsc_service.searchanalytics.return_value.query.return_value.execute.return_value = {}
    with patch("gsc_mcp.tools.analytics.get_searchconsole_service", return_value=mock_gsc_service):
        result = json.loads(get_search_analytics(SITE))
    assert result["rows"] == []


def test_get_performance_overview(mock_gsc_service):
    mock_gsc_service.searchanalytics.return_value.query.return_value.execute.return_value = (
        _mock_response([_ROW])
    )
    with patch("gsc_mcp.tools.analytics.get_searchconsole_service", return_value=mock_gsc_service):
        result = json.loads(get_performance_overview(SITE))
    assert "totals" in result
    assert result["totals"]["clicks"] == 100
    assert "_meta" in result


def test_compare_search_periods(mock_gsc_service):
    mock_gsc_service.searchanalytics.return_value.query.return_value.execute.return_value = (
        _mock_response([_ROW])
    )
    with patch("gsc_mcp.tools.analytics.get_searchconsole_service", return_value=mock_gsc_service):
        result = json.loads(compare_search_periods(SITE, days=28))
    assert "period_a" in result
    assert "period_b" in result
    assert "_meta" in result


def test_get_search_by_page_query(mock_gsc_service):
    page_row = {"keys": ["https://example.com/page", "query1"], "clicks": 50, "impressions": 500, "ctr": 0.1, "position": 4.0}
    mock_gsc_service.searchanalytics.return_value.query.return_value.execute.return_value = (
        _mock_response([page_row])
    )
    with patch("gsc_mcp.tools.analytics.get_searchconsole_service", return_value=mock_gsc_service):
        result = json.loads(get_search_by_page_query(SITE))
    assert len(result["rows"]) == 1
    assert result["rows"][0]["page"] == "https://example.com/page"
    assert result["rows"][0]["query"] == "query1"
    assert "_meta" in result


def test_get_advanced_search_analytics(mock_gsc_service):
    mock_gsc_service.searchanalytics.return_value.query.return_value.execute.return_value = (
        _mock_response([_ROW])
    )
    with patch("gsc_mcp.tools.analytics.get_searchconsole_service", return_value=mock_gsc_service):
        result = json.loads(get_advanced_search_analytics(
            SITE,
            dimensions=["query"],
            date_range_days=28,
            row_limit=100,
        ))
    assert len(result["rows"]) >= 0
    assert "_meta" in result


# ===========================
# analytics_anomalies tests
# ===========================

def _date_row(days_ago, clicks):
    d = (date.today() - timedelta(days=3 + days_ago)).isoformat()
    return {"keys": [d], "clicks": clicks, "impressions": 5000, "ctr": 0.02, "position": 5.0}


def test_anomalies_flags_spike_above_threshold(mock_gsc_service):
    # 29 normal days at 100 clicks, one spike at 500 (z >> 2.5)
    rows = [_date_row(i, 100) for i in range(1, 30)] + [_date_row(30, 500)]
    mock_gsc_service.searchanalytics.return_value.query.return_value.execute.return_value = {"rows": rows}
    with patch("gsc_mcp.tools.analytics.get_searchconsole_service", return_value=mock_gsc_service):
        result = json.loads(analytics_anomalies(SITE, days=90))
    assert "anomalies" in result
    assert len(result["anomalies"]) >= 1
    spike = next(a for a in result["anomalies"] if a["type"] == "spike")
    assert spike["clicks"] == 500
    assert spike["z_score"] > 2.5


def test_anomalies_does_not_flag_below_threshold(mock_gsc_service):
    # Uniform series: std = 0, no anomalies
    rows = [_date_row(i, 100) for i in range(30)]
    mock_gsc_service.searchanalytics.return_value.query.return_value.execute.return_value = {"rows": rows}
    with patch("gsc_mcp.tools.analytics.get_searchconsole_service", return_value=mock_gsc_service):
        result = json.loads(analytics_anomalies(SITE))
    assert result["anomalies"] == []


def test_anomalies_std_zero_returns_empty(mock_gsc_service):
    """Uniform series: std == 0, no crash, returns empty anomalies."""
    rows = [_date_row(i, 200) for i in range(30)]
    mock_gsc_service.searchanalytics.return_value.query.return_value.execute.return_value = {"rows": rows}
    with patch("gsc_mcp.tools.analytics.get_searchconsole_service", return_value=mock_gsc_service):
        result = json.loads(analytics_anomalies(SITE))
    assert result["anomalies"] == []


def test_anomalies_all_zero_returns_empty(mock_gsc_service):
    rows = [_date_row(i, 0) for i in range(30)]
    mock_gsc_service.searchanalytics.return_value.query.return_value.execute.return_value = {"rows": rows}
    with patch("gsc_mcp.tools.analytics.get_searchconsole_service", return_value=mock_gsc_service):
        result = json.loads(analytics_anomalies(SITE))
    assert result["anomalies"] == []


def test_anomalies_single_data_point_returns_empty(mock_gsc_service):
    mock_gsc_service.searchanalytics.return_value.query.return_value.execute.return_value = {
        "rows": [_date_row(1, 100)]
    }
    with patch("gsc_mcp.tools.analytics.get_searchconsole_service", return_value=mock_gsc_service):
        result = json.loads(analytics_anomalies(SITE))
    assert result["anomalies"] == []


def test_anomalies_empty_rows_returns_empty(mock_gsc_service):
    mock_gsc_service.searchanalytics.return_value.query.return_value.execute.return_value = {"rows": []}
    with patch("gsc_mcp.tools.analytics.get_searchconsole_service", return_value=mock_gsc_service):
        result = json.loads(analytics_anomalies(SITE))
    assert result["anomalies"] == []
    assert "_meta" in result


def test_anomalies_custom_threshold_respected(mock_gsc_service):
    # 29 days at 100, one spike at 500: pstdev ~= 71.8, z ~= 5.4 for the spike.
    # threshold=2.5 flags it (tested above); threshold=6.0 must NOT flag it.
    rows = [_date_row(i, 100) for i in range(1, 30)] + [_date_row(30, 500)]
    mock_gsc_service.searchanalytics.return_value.query.return_value.execute.return_value = {"rows": rows}
    with patch("gsc_mcp.tools.analytics.get_searchconsole_service", return_value=mock_gsc_service):
        result = json.loads(analytics_anomalies(SITE, days=90, threshold=6.0))
    assert result["anomalies"] == []


def test_anomalies_meta_includes_days_and_threshold(mock_gsc_service):
    mock_gsc_service.searchanalytics.return_value.query.return_value.execute.return_value = {"rows": []}
    with patch("gsc_mcp.tools.analytics.get_searchconsole_service", return_value=mock_gsc_service):
        result = json.loads(analytics_anomalies(SITE, days=60, threshold=3.0))
    assert result["_meta"]["params"]["days"] == 60
    assert result["_meta"]["params"]["threshold"] == 3.0
    assert result["_meta"]["tool"] == "analytics_anomalies"


def test_anomalies_anomaly_has_date_field(mock_gsc_service):
    rows = [_date_row(i, 100) for i in range(1, 30)] + [_date_row(30, 500)]
    mock_gsc_service.searchanalytics.return_value.query.return_value.execute.return_value = {"rows": rows}
    with patch("gsc_mcp.tools.analytics.get_searchconsole_service", return_value=mock_gsc_service):
        result = json.loads(analytics_anomalies(SITE))
    assert len(result["anomalies"]) >= 1
    a = result["anomalies"][0]
    assert "date" in a
    assert "clicks" in a
    assert "z_score" in a
    assert "type" in a


# ===========================
# discover_performance tests
# ===========================

_DISCOVER_ROW_HIGH = {"keys": ["https://example.com/popular"], "clicks": 200, "impressions": 5000, "ctr": 0.04, "position": 1.0}
_DISCOVER_ROW_LOW = {"keys": ["https://example.com/other"], "clicks": 10, "impressions": 300, "ctr": 0.033, "position": 2.0}


def test_discover_performance_returns_rows_sorted_by_impressions_desc(mock_gsc_service):
    """Rows must be sorted by impressions descending."""
    mock_gsc_service.searchanalytics.return_value.query.return_value.execute.return_value = {
        "rows": [_DISCOVER_ROW_LOW, _DISCOVER_ROW_HIGH]
    }
    with patch("gsc_mcp.tools.analytics.get_searchconsole_service", return_value=mock_gsc_service):
        result = json.loads(discover_performance(SITE))
    assert result["rows"][0]["impressions"] == 5000
    assert result["rows"][1]["impressions"] == 300


def test_discover_performance_limit_applied(mock_gsc_service):
    """When more rows than limit, only limit rows are returned."""
    many_rows = [
        {"keys": [f"https://example.com/page{i}"], "clicks": i, "impressions": i * 10, "ctr": 0.1, "position": 1.0}
        for i in range(1, 11)
    ]
    mock_gsc_service.searchanalytics.return_value.query.return_value.execute.return_value = {"rows": many_rows}
    with patch("gsc_mcp.tools.analytics.get_searchconsole_service", return_value=mock_gsc_service):
        result = json.loads(discover_performance(SITE, limit=3))
    assert result["count"] == 3
    assert len(result["rows"]) == 3


def test_discover_performance_request_body_uses_discover_type(mock_gsc_service):
    """The API request body must contain 'type': 'discover' and dimensions ['page']."""
    mock_gsc_service.searchanalytics.return_value.query.return_value.execute.return_value = {"rows": []}
    with patch("gsc_mcp.tools.analytics.get_searchconsole_service", return_value=mock_gsc_service):
        discover_performance(SITE)
    call_kwargs = mock_gsc_service.searchanalytics.return_value.query.call_args
    body_sent = call_kwargs.kwargs["body"]
    assert body_sent["type"] == "discover"
    assert body_sent["dimensions"] == ["page"]


def test_discover_performance_empty_response_returns_count_zero(mock_gsc_service):
    """Empty API response must not raise and must return count=0."""
    mock_gsc_service.searchanalytics.return_value.query.return_value.execute.return_value = {}
    with patch("gsc_mcp.tools.analytics.get_searchconsole_service", return_value=mock_gsc_service):
        result = json.loads(discover_performance(SITE))
    assert result["count"] == 0
    assert result["rows"] == []


def test_discover_performance_meta_block_correct(mock_gsc_service):
    """_meta block must be present with correct tool name and params."""
    mock_gsc_service.searchanalytics.return_value.query.return_value.execute.return_value = {"rows": []}
    with patch("gsc_mcp.tools.analytics.get_searchconsole_service", return_value=mock_gsc_service):
        result = json.loads(discover_performance(SITE, days=14, limit=25))
    assert "_meta" in result
    assert result["_meta"]["tool"] == "discover_performance"
    assert result["_meta"]["params"]["site"] == SITE
    assert result["_meta"]["params"]["days"] == 14
    assert result["_meta"]["params"]["limit"] == 25
