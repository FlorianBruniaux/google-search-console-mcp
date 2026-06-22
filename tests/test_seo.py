import json
import pytest
from unittest.mock import patch
from gsc_mcp.tools.seo import quick_wins, traffic_drops, check_alerts

SITE = "https://example.com/"

_ROWS_QUICK_WINS = [
    # position 4-15, impressions >= 10, CTR below benchmark → opportunity
    {"keys": ["https://example.com/a"], "clicks": 10, "impressions": 500, "ctr": 0.02, "position": 6.5},
    # position 4-15, impressions >= 10, CTR = 0 → opportunity (the real bug case)
    {"keys": ["https://example.com/projects"], "clicks": 0, "impressions": 80, "ctr": 0.0, "position": 8.1},
    # position 4-15, impressions >= 10, CTR = 0 → opportunity
    {"keys": ["https://example.com/about"], "clicks": 0, "impressions": 32, "ctr": 0.0, "position": 8.6},
    # position 1-3 → excluded
    {"keys": ["https://example.com/c"], "clicks": 300, "impressions": 1000, "ctr": 0.3, "position": 1.2},
    # CTR already at benchmark → excluded
    {"keys": ["https://example.com/d"], "clicks": 50, "impressions": 1000, "ctr": 0.05, "position": 6.0},
    # impressions below threshold → excluded
    {"keys": ["https://example.com/e"], "clicks": 0, "impressions": 5, "ctr": 0.0, "position": 7.0},
]

_ROWS_TRAFFIC = [
    {"keys": ["landing page"], "clicks": 50, "impressions": 500, "ctr": 0.1, "position": 5.0},
]


def test_quick_wins_returns_opportunities(mock_gsc_service):
    mock_gsc_service.searchanalytics.return_value.query.return_value.execute.return_value = {
        "rows": _ROWS_QUICK_WINS
    }
    with patch("gsc_mcp.tools.seo.get_searchconsole_service", return_value=mock_gsc_service):
        result = json.loads(quick_wins(SITE))

    assert "opportunities" in result
    assert "_meta" in result
    assert len(result["opportunities"]) > 0
    for opp in result["opportunities"]:
        assert 4 <= opp["position"] <= 15


def test_quick_wins_detects_zero_ctr_pages(mock_gsc_service):
    """Pages with CTR=0 and sufficient impressions must be detected."""
    mock_gsc_service.searchanalytics.return_value.query.return_value.execute.return_value = {
        "rows": _ROWS_QUICK_WINS
    }
    with patch("gsc_mcp.tools.seo.get_searchconsole_service", return_value=mock_gsc_service):
        result = json.loads(quick_wins(SITE))

    pages = [opp["page"] for opp in result["opportunities"]]
    assert "https://example.com/projects" in pages
    assert "https://example.com/about" in pages


def test_quick_wins_excludes_position_1_to_3(mock_gsc_service):
    mock_gsc_service.searchanalytics.return_value.query.return_value.execute.return_value = {
        "rows": _ROWS_QUICK_WINS
    }
    with patch("gsc_mcp.tools.seo.get_searchconsole_service", return_value=mock_gsc_service):
        result = json.loads(quick_wins(SITE))

    positions = [opp["position"] for opp in result["opportunities"]]
    assert all(p > 3 for p in positions)


def test_quick_wins_excludes_low_impressions(mock_gsc_service):
    """Pages below min_impressions threshold must be excluded."""
    mock_gsc_service.searchanalytics.return_value.query.return_value.execute.return_value = {
        "rows": _ROWS_QUICK_WINS
    }
    with patch("gsc_mcp.tools.seo.get_searchconsole_service", return_value=mock_gsc_service):
        result = json.loads(quick_wins(SITE))

    pages = [opp["page"] for opp in result["opportunities"]]
    assert "https://example.com/e" not in pages


def test_quick_wins_excludes_ctr_above_benchmark(mock_gsc_service):
    """Pages already meeting or beating benchmark CTR must be excluded."""
    mock_gsc_service.searchanalytics.return_value.query.return_value.execute.return_value = {
        "rows": _ROWS_QUICK_WINS
    }
    with patch("gsc_mcp.tools.seo.get_searchconsole_service", return_value=mock_gsc_service):
        result = json.loads(quick_wins(SITE))

    pages = [opp["page"] for opp in result["opportunities"]]
    assert "https://example.com/d" not in pages


def test_traffic_drops_returns_drops(mock_gsc_service):
    mock_gsc_service.searchanalytics.return_value.query.return_value.execute.return_value = {
        "rows": _ROWS_TRAFFIC
    }
    with patch("gsc_mcp.tools.seo.get_searchconsole_service", return_value=mock_gsc_service):
        result = json.loads(traffic_drops(SITE))

    assert "drops" in result
    assert "_meta" in result


def test_check_alerts_returns_list(mock_gsc_service):
    mock_gsc_service.searchanalytics.return_value.query.return_value.execute.return_value = {
        "rows": _ROWS_QUICK_WINS
    }
    with patch("gsc_mcp.tools.seo.get_searchconsole_service", return_value=mock_gsc_service):
        result = json.loads(check_alerts(SITE))

    assert "alerts" in result
    assert "_meta" in result
    for alert in result["alerts"]:
        assert alert["severity"] in ("high", "medium")
