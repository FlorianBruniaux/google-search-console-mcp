import json
import pytest
from unittest.mock import patch
from gsc_mcp.tools.analytics import (
    get_search_analytics,
    get_performance_overview,
    compare_search_periods,
    get_search_by_page_query,
    get_advanced_search_analytics,
)

SITE = "https://example.com/"

_ROW = {"keys": ["query1"], "clicks": 100, "impressions": 1000, "ctr": 0.1, "position": 3.0}


def _mock_response(rows):
    return {"rows": rows}


def test_get_search_analytics(mock_gsc_service):
    mock_gsc_service.searchanalytics.return_value.query.return_value.execute.return_value = (
        _mock_response([_ROW])
    )
    with patch("gsc_mcp.tools.analytics.get_gsc_service", return_value=mock_gsc_service):
        result = json.loads(get_search_analytics(SITE))
    assert result["site"] == SITE
    assert len(result["rows"]) == 1
    assert result["rows"][0]["query"] == "query1"
    assert "_meta" in result


def test_get_search_analytics_empty(mock_gsc_service):
    mock_gsc_service.searchanalytics.return_value.query.return_value.execute.return_value = {}
    with patch("gsc_mcp.tools.analytics.get_gsc_service", return_value=mock_gsc_service):
        result = json.loads(get_search_analytics(SITE))
    assert result["rows"] == []


def test_get_performance_overview(mock_gsc_service):
    mock_gsc_service.searchanalytics.return_value.query.return_value.execute.return_value = (
        _mock_response([_ROW])
    )
    with patch("gsc_mcp.tools.analytics.get_gsc_service", return_value=mock_gsc_service):
        result = json.loads(get_performance_overview(SITE))
    assert "totals" in result
    assert result["totals"]["clicks"] == 100
    assert "_meta" in result


def test_compare_search_periods(mock_gsc_service):
    mock_gsc_service.searchanalytics.return_value.query.return_value.execute.return_value = (
        _mock_response([_ROW])
    )
    with patch("gsc_mcp.tools.analytics.get_gsc_service", return_value=mock_gsc_service):
        result = json.loads(compare_search_periods(SITE, days=28))
    assert "period_a" in result
    assert "period_b" in result
    assert "_meta" in result


def test_get_search_by_page_query(mock_gsc_service):
    page_row = {"keys": ["https://example.com/page", "query1"], "clicks": 50, "impressions": 500, "ctr": 0.1, "position": 4.0}
    mock_gsc_service.searchanalytics.return_value.query.return_value.execute.return_value = (
        _mock_response([page_row])
    )
    with patch("gsc_mcp.tools.analytics.get_gsc_service", return_value=mock_gsc_service):
        result = json.loads(get_search_by_page_query(SITE))
    assert len(result["rows"]) == 1
    assert result["rows"][0]["page"] == "https://example.com/page"
    assert result["rows"][0]["query"] == "query1"
    assert "_meta" in result


def test_get_advanced_search_analytics(mock_gsc_service):
    mock_gsc_service.searchanalytics.return_value.query.return_value.execute.return_value = (
        _mock_response([_ROW])
    )
    with patch("gsc_mcp.tools.analytics.get_gsc_service", return_value=mock_gsc_service):
        result = json.loads(get_advanced_search_analytics(
            SITE,
            dimensions=["query"],
            date_range_days=28,
            row_limit=100,
        ))
    assert len(result["rows"]) >= 0
    assert "_meta" in result
