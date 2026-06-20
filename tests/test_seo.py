import json
import pytest
from unittest.mock import patch
from gsc_mcp.tools.seo import quick_wins, traffic_drops, check_alerts

SITE = "https://example.com/"

_ROWS_QUICK_WINS = [
    {"keys": ["https://example.com/a", "buy shoes"], "clicks": 10, "impressions": 500, "ctr": 0.02, "position": 6.5},
    {"keys": ["https://example.com/b", "running tips"], "clicks": 1, "impressions": 1000, "ctr": 0.001, "position": 12.0},
    {"keys": ["https://example.com/c", "top query"], "clicks": 300, "impressions": 1000, "ctr": 0.3, "position": 1.2},
]

_ROWS_TRAFFIC = [
    {"keys": ["landing page"], "clicks": 50, "impressions": 500, "ctr": 0.1, "position": 5.0},
]


def test_quick_wins_returns_opportunities(mock_gsc_service):
    mock_gsc_service.searchanalytics.return_value.query.return_value.execute.return_value = {
        "rows": _ROWS_QUICK_WINS
    }
    with patch("gsc_mcp.tools.seo.get_gsc_service", return_value=mock_gsc_service):
        result = json.loads(quick_wins(SITE))

    assert "opportunities" in result
    assert "_meta" in result
    for opp in result["opportunities"]:
        assert 4 <= opp["position"] <= 15


def test_quick_wins_excludes_position_1_to_3(mock_gsc_service):
    mock_gsc_service.searchanalytics.return_value.query.return_value.execute.return_value = {
        "rows": _ROWS_QUICK_WINS
    }
    with patch("gsc_mcp.tools.seo.get_gsc_service", return_value=mock_gsc_service):
        result = json.loads(quick_wins(SITE))

    positions = [opp["position"] for opp in result["opportunities"]]
    assert all(p > 3 for p in positions)


def test_traffic_drops_returns_drops(mock_gsc_service):
    mock_gsc_service.searchanalytics.return_value.query.return_value.execute.return_value = {
        "rows": _ROWS_TRAFFIC
    }
    with patch("gsc_mcp.tools.seo.get_gsc_service", return_value=mock_gsc_service):
        result = json.loads(traffic_drops(SITE))

    assert "drops" in result
    assert "_meta" in result


def test_check_alerts_returns_list(mock_gsc_service):
    mock_gsc_service.searchanalytics.return_value.query.return_value.execute.return_value = {
        "rows": _ROWS_QUICK_WINS
    }
    with patch("gsc_mcp.tools.seo.get_gsc_service", return_value=mock_gsc_service):
        result = json.loads(check_alerts(SITE))

    assert "alerts" in result
    assert "_meta" in result
    for alert in result["alerts"]:
        assert alert["severity"] in ("high", "medium")
