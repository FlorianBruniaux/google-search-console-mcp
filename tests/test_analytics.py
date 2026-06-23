import json
import pytest
import httplib2
from datetime import date, timedelta
from unittest.mock import patch
from googleapiclient.errors import HttpError
from gsc_mcp.tools.analytics import (
    get_search_analytics,
    get_performance_overview,
    compare_search_periods,
    get_search_by_page_query,
    get_advanced_search_analytics,
    analytics_anomalies,
    discover_performance,
    news_performance,
    search_type_breakdown,
    ai_overviews_impact,
    _SEARCH_TYPES,
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


# ===========================
# news_performance tests
# ===========================

_NEWS_ROW_HIGH = {"keys": ["https://example.com/news1"], "clicks": 150, "impressions": 4000, "ctr": 0.0375, "position": 1.5}
_NEWS_ROW_LOW = {"keys": ["https://example.com/news2"], "clicks": 5, "impressions": 200, "ctr": 0.025, "position": 2.5}


def test_news_performance_returns_rows_sorted_by_impressions_desc(mock_gsc_service):
    """Rows must be sorted by impressions descending."""
    mock_gsc_service.searchanalytics.return_value.query.return_value.execute.return_value = {
        "rows": [_NEWS_ROW_LOW, _NEWS_ROW_HIGH]
    }
    with patch("gsc_mcp.tools.analytics.get_searchconsole_service", return_value=mock_gsc_service):
        result = json.loads(news_performance(SITE))
    assert result["rows"][0]["impressions"] == 4000
    assert result["rows"][1]["impressions"] == 200


def test_news_performance_limit_applied(mock_gsc_service):
    """When more rows than limit, only limit rows are returned."""
    many_rows = [
        {"keys": [f"https://example.com/news{i}"], "clicks": i, "impressions": i * 10, "ctr": 0.1, "position": 1.0}
        for i in range(1, 11)
    ]
    mock_gsc_service.searchanalytics.return_value.query.return_value.execute.return_value = {"rows": many_rows}
    with patch("gsc_mcp.tools.analytics.get_searchconsole_service", return_value=mock_gsc_service):
        result = json.loads(news_performance(SITE, limit=3))
    assert result["count"] == 3
    assert len(result["rows"]) == 3


def test_news_performance_request_body_uses_googlenews_type(mock_gsc_service):
    """The API request body must contain 'type': 'googleNews' and dimensions ['page']."""
    mock_gsc_service.searchanalytics.return_value.query.return_value.execute.return_value = {"rows": []}
    with patch("gsc_mcp.tools.analytics.get_searchconsole_service", return_value=mock_gsc_service):
        news_performance(SITE)
    call_kwargs = mock_gsc_service.searchanalytics.return_value.query.call_args
    body_sent = call_kwargs.kwargs["body"]
    assert body_sent["type"] == "googleNews"
    assert body_sent["dimensions"] == ["page"]


def test_news_performance_empty_response_returns_count_zero(mock_gsc_service):
    """Empty API response must not raise and must return count=0."""
    mock_gsc_service.searchanalytics.return_value.query.return_value.execute.return_value = {}
    with patch("gsc_mcp.tools.analytics.get_searchconsole_service", return_value=mock_gsc_service):
        result = json.loads(news_performance(SITE))
    assert result["count"] == 0
    assert result["rows"] == []


def test_news_performance_meta_block_correct(mock_gsc_service):
    """_meta block must be present with correct tool name and params."""
    mock_gsc_service.searchanalytics.return_value.query.return_value.execute.return_value = {"rows": []}
    with patch("gsc_mcp.tools.analytics.get_searchconsole_service", return_value=mock_gsc_service):
        result = json.loads(news_performance(SITE, days=14, limit=25))
    assert "_meta" in result
    assert result["_meta"]["tool"] == "news_performance"
    assert result["_meta"]["params"]["site"] == SITE
    assert result["_meta"]["params"]["days"] == 14
    assert result["_meta"]["params"]["limit"] == 25


# ===========================
# search_type_breakdown tests
# ===========================

def _make_breakdown_side_effect(clicks_per_type):
    """Build 5 mock responses, one per search type (indexed in _SEARCH_TYPES order)."""
    responses = []
    for clicks in clicks_per_type:
        if clicks is None:
            responses.append({})
        else:
            rows = [{"keys": [f"https://example.com/page"], "clicks": clicks, "impressions": clicks * 10, "ctr": 0.1, "position": 3.0}]
            responses.append({"rows": rows})
    return responses


def test_search_type_breakdown_all_five_keys_present(mock_gsc_service):
    """Result breakdown must contain all 5 search types."""
    mock_gsc_service.searchanalytics.return_value.query.return_value.execute.side_effect = (
        _make_breakdown_side_effect([100, 50, 30, 20, 10])
    )
    with patch("gsc_mcp.tools.analytics.get_searchconsole_service", return_value=mock_gsc_service):
        result = json.loads(search_type_breakdown(SITE))
    assert set(result["breakdown"].keys()) == set(_SEARCH_TYPES)


def test_search_type_breakdown_five_gsc_calls_made(mock_gsc_service):
    """Exactly 5 GSC searchanalytics calls must be made (one per type)."""
    mock_gsc_service.searchanalytics.return_value.query.return_value.execute.side_effect = (
        _make_breakdown_side_effect([10, 20, 30, 40, 50])
    )
    with patch("gsc_mcp.tools.analytics.get_searchconsole_service", return_value=mock_gsc_service):
        search_type_breakdown(SITE)
    assert mock_gsc_service.searchanalytics.return_value.query.call_count == 5


def test_search_type_breakdown_url_inserts_filter(mock_gsc_service):
    """When url is provided, at least one call must include dimensionFilterGroups in the body."""
    mock_gsc_service.searchanalytics.return_value.query.return_value.execute.side_effect = (
        _make_breakdown_side_effect([10, 10, 10, 10, 10])
    )
    target_url = "https://example.com/specific-page"
    with patch("gsc_mcp.tools.analytics.get_searchconsole_service", return_value=mock_gsc_service):
        search_type_breakdown(SITE, url=target_url)
    all_calls = mock_gsc_service.searchanalytics.return_value.query.call_args_list
    bodies = [call.kwargs["body"] for call in all_calls]
    assert all("dimensionFilterGroups" in b for b in bodies), "All 5 calls must include dimensionFilterGroups when url is set"
    filter_expr = bodies[0]["dimensionFilterGroups"][0]["filters"][0]["expression"]
    assert filter_expr == target_url


def test_search_type_breakdown_clicks_aggregated(mock_gsc_service):
    """Clicks should sum correctly across multiple rows per type."""
    # For 'web' (first call), return 2 rows summing to 150 clicks
    two_rows = [
        {"keys": ["https://example.com/a"], "clicks": 100, "impressions": 1000, "ctr": 0.1, "position": 2.0},
        {"keys": ["https://example.com/b"], "clicks": 50, "impressions": 500, "ctr": 0.1, "position": 3.0},
    ]
    single_row = [{"keys": ["https://example.com/c"], "clicks": 20, "impressions": 200, "ctr": 0.1, "position": 4.0}]
    mock_gsc_service.searchanalytics.return_value.query.return_value.execute.side_effect = [
        {"rows": two_rows},   # web
        {"rows": single_row}, # discover
        {"rows": single_row}, # googleNews
        {"rows": single_row}, # image
        {"rows": single_row}, # video
    ]
    with patch("gsc_mcp.tools.analytics.get_searchconsole_service", return_value=mock_gsc_service):
        result = json.loads(search_type_breakdown(SITE))
    assert result["breakdown"]["web"]["clicks"] == 150
    assert result["breakdown"]["discover"]["clicks"] == 20


def test_search_type_breakdown_empty_type_returns_zero(mock_gsc_service):
    """An empty API response for a type must yield 0 clicks/impressions without error."""
    mock_gsc_service.searchanalytics.return_value.query.return_value.execute.side_effect = (
        _make_breakdown_side_effect([100, None, None, None, None])
    )
    with patch("gsc_mcp.tools.analytics.get_searchconsole_service", return_value=mock_gsc_service):
        result = json.loads(search_type_breakdown(SITE))
    assert result["breakdown"]["discover"]["clicks"] == 0
    assert result["breakdown"]["discover"]["impressions"] == 0
    assert result["breakdown"]["googleNews"]["clicks"] == 0


def test_search_type_breakdown_meta_block_correct(mock_gsc_service):
    """_meta block must be present with correct tool name and params."""
    mock_gsc_service.searchanalytics.return_value.query.return_value.execute.side_effect = (
        _make_breakdown_side_effect([0, 0, 0, 0, 0])
    )
    with patch("gsc_mcp.tools.analytics.get_searchconsole_service", return_value=mock_gsc_service):
        result = json.loads(search_type_breakdown(SITE, days=14))
    assert "_meta" in result
    assert result["_meta"]["tool"] == "search_type_breakdown"
    assert result["_meta"]["params"]["site"] == SITE
    assert result["_meta"]["params"]["days"] == 14
    assert result["_meta"]["params"]["url"] is None


# ---------------------------------------------------------------------------
# ai_overviews_impact tests
# ---------------------------------------------------------------------------

def _make_http_error(status: int) -> HttpError:
    resp = httplib2.Response({"status": str(status)})
    resp.status = status
    return HttpError(resp=resp, content=b"Bad Request")


def test_ai_overviews_impact_success_sorted_by_impressions(mock_gsc_service):
    """Successful call returns rows sorted by impressions desc and count matches slice."""
    rows = [
        {"keys": ["best query", "AI_OVERVIEW"], "clicks": 10, "impressions": 500, "ctr": 0.02, "position": 1.5},
        {"keys": ["second query", "AI_OVERVIEW"], "clicks": 5, "impressions": 1000, "ctr": 0.005, "position": 2.0},
        {"keys": ["third query", "AI_OVERVIEW"], "clicks": 1, "impressions": 100, "ctr": 0.01, "position": 3.0},
    ]
    mock_gsc_service.searchanalytics.return_value.query.return_value.execute.return_value = {"rows": rows}
    with patch("gsc_mcp.tools.analytics.get_searchconsole_service", return_value=mock_gsc_service):
        result = json.loads(ai_overviews_impact(SITE, days=28, limit=10))
    assert result["count"] == 3
    impressions = [r["impressions"] for r in result["rows"]]
    assert impressions == sorted(impressions, reverse=True)


def test_ai_overviews_impact_http_error_400_returns_structured_error(mock_gsc_service):
    """HttpError(400) must return AI_OVERVIEWS_NOT_AVAILABLE without raising."""
    mock_gsc_service.searchanalytics.return_value.query.return_value.execute.side_effect = _make_http_error(400)
    with patch("gsc_mcp.tools.analytics.get_searchconsole_service", return_value=mock_gsc_service):
        result = json.loads(ai_overviews_impact(SITE))
    assert result["error"] == "AI_OVERVIEWS_NOT_AVAILABLE"
    assert "reason" in result


def test_ai_overviews_impact_http_error_403_returns_structured_error(mock_gsc_service):
    """HttpError(403) must return AI_OVERVIEWS_NOT_AVAILABLE without raising."""
    mock_gsc_service.searchanalytics.return_value.query.return_value.execute.side_effect = _make_http_error(403)
    with patch("gsc_mcp.tools.analytics.get_searchconsole_service", return_value=mock_gsc_service):
        result = json.loads(ai_overviews_impact(SITE))
    assert result["error"] == "AI_OVERVIEWS_NOT_AVAILABLE"
    assert "reason" in result


@patch("gsc_mcp.retry.time.sleep")
def test_ai_overviews_impact_http_error_500_reraises(mock_sleep, mock_gsc_service):
    """HttpError(500) must not be caught: it should propagate for @with_retry to handle."""
    mock_gsc_service.searchanalytics.return_value.query.return_value.execute.side_effect = _make_http_error(500)
    with patch("gsc_mcp.tools.analytics.get_searchconsole_service", return_value=mock_gsc_service):
        with pytest.raises(HttpError):
            ai_overviews_impact(SITE)


def test_ai_overviews_impact_meta_block_present_in_success_and_error(mock_gsc_service):
    """_meta block must appear in both success and error response paths."""
    # Success path
    mock_gsc_service.searchanalytics.return_value.query.return_value.execute.return_value = {"rows": []}
    with patch("gsc_mcp.tools.analytics.get_searchconsole_service", return_value=mock_gsc_service):
        success_result = json.loads(ai_overviews_impact(SITE, days=14))
    assert "_meta" in success_result
    assert success_result["_meta"]["tool"] == "ai_overviews_impact"
    assert success_result["_meta"]["params"]["site"] == SITE

    # Error path
    mock_gsc_service.searchanalytics.return_value.query.return_value.execute.side_effect = _make_http_error(400)
    with patch("gsc_mcp.tools.analytics.get_searchconsole_service", return_value=mock_gsc_service):
        error_result = json.loads(ai_overviews_impact(SITE, days=14))
    assert "_meta" in error_result
    assert error_result["_meta"]["tool"] == "ai_overviews_impact"
    assert error_result["_meta"]["params"]["site"] == SITE
