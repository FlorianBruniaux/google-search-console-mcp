import json
import pytest
from datetime import date, timedelta
from unittest.mock import patch
from gsc_mcp.tools.seo import quick_wins, traffic_drops, check_alerts, seo_striking_distance, seo_cannibalization, seo_lost_queries

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


# ===========================
# seo_striking_distance tests
# ===========================

def _make_query_row(query, position, impressions, clicks=5, ctr=0.05):
    return {
        "keys": [query],
        "clicks": clicks,
        "impressions": impressions,
        "ctr": ctr,
        "position": position,
    }


_ROWS_STRIKING = [
    _make_query_row("buy running shoes", 9.2, 800, clicks=10),
    _make_query_row("best shoes 2024", 11.0, 500, clicks=5),
    _make_query_row("shoes review", 4.0, 300, clicks=20),        # pos 4.0 = excluded
    _make_query_row("cheap shoes", 7.9, 200, clicks=3),          # pos 7.9 = below band
    _make_query_row("running shoes red", 15.1, 100, clicks=1),   # pos 15.1 = above band
    _make_query_row("shoes sale", 8.0, 50, clicks=2),            # pos 8.0 = lower bound, included
]


def test_striking_distance_returns_queries_key(mock_gsc_service):
    mock_gsc_service.searchanalytics.return_value.query.return_value.execute.return_value = {
        "rows": _ROWS_STRIKING
    }
    with patch("gsc_mcp.tools.seo.get_searchconsole_service", return_value=mock_gsc_service):
        result = json.loads(seo_striking_distance(SITE))
    assert "queries" in result
    assert "_meta" in result


def test_striking_distance_band_8_to_15_inclusive(mock_gsc_service):
    mock_gsc_service.searchanalytics.return_value.query.return_value.execute.return_value = {
        "rows": _ROWS_STRIKING
    }
    with patch("gsc_mcp.tools.seo.get_searchconsole_service", return_value=mock_gsc_service):
        result = json.loads(seo_striking_distance(SITE))
    positions = [q["position"] for q in result["queries"]]
    assert all(8.0 <= p <= 15.0 for p in positions), f"Out-of-band positions: {positions}"


def test_striking_distance_excludes_pos_4_proving_band_not_4_to_15(mock_gsc_service):
    """Proves band is 8-15, not 4-15 like quick_wins."""
    mock_gsc_service.searchanalytics.return_value.query.return_value.execute.return_value = {
        "rows": _ROWS_STRIKING
    }
    with patch("gsc_mcp.tools.seo.get_searchconsole_service", return_value=mock_gsc_service):
        result = json.loads(seo_striking_distance(SITE))
    query_names = [q["query"] for q in result["queries"]]
    assert "shoes review" not in query_names


def test_striking_distance_excludes_pos_7_9(mock_gsc_service):
    mock_gsc_service.searchanalytics.return_value.query.return_value.execute.return_value = {
        "rows": _ROWS_STRIKING
    }
    with patch("gsc_mcp.tools.seo.get_searchconsole_service", return_value=mock_gsc_service):
        result = json.loads(seo_striking_distance(SITE))
    query_names = [q["query"] for q in result["queries"]]
    assert "cheap shoes" not in query_names


def test_striking_distance_excludes_pos_15_1(mock_gsc_service):
    mock_gsc_service.searchanalytics.return_value.query.return_value.execute.return_value = {
        "rows": _ROWS_STRIKING
    }
    with patch("gsc_mcp.tools.seo.get_searchconsole_service", return_value=mock_gsc_service):
        result = json.loads(seo_striking_distance(SITE))
    query_names = [q["query"] for q in result["queries"]]
    assert "running shoes red" not in query_names


def test_striking_distance_includes_3_in_band(mock_gsc_service):
    mock_gsc_service.searchanalytics.return_value.query.return_value.execute.return_value = {
        "rows": _ROWS_STRIKING
    }
    with patch("gsc_mcp.tools.seo.get_searchconsole_service", return_value=mock_gsc_service):
        result = json.loads(seo_striking_distance(SITE))
    # buy running shoes (9.2), best shoes 2024 (11.0), shoes sale (8.0)
    assert len(result["queries"]) == 3


def test_striking_distance_sorted_impressions_desc(mock_gsc_service):
    mock_gsc_service.searchanalytics.return_value.query.return_value.execute.return_value = {
        "rows": _ROWS_STRIKING
    }
    with patch("gsc_mcp.tools.seo.get_searchconsole_service", return_value=mock_gsc_service):
        result = json.loads(seo_striking_distance(SITE))
    imps = [q["impressions"] for q in result["queries"]]
    assert imps == sorted(imps, reverse=True)


def test_striking_distance_min_impressions_filter(mock_gsc_service):
    mock_gsc_service.searchanalytics.return_value.query.return_value.execute.return_value = {
        "rows": _ROWS_STRIKING
    }
    with patch("gsc_mcp.tools.seo.get_searchconsole_service", return_value=mock_gsc_service):
        result = json.loads(seo_striking_distance(SITE, min_impressions=100))
    for q in result["queries"]:
        assert q["impressions"] >= 100


def test_striking_distance_min_impressions_in_meta(mock_gsc_service):
    mock_gsc_service.searchanalytics.return_value.query.return_value.execute.return_value = {"rows": []}
    with patch("gsc_mcp.tools.seo.get_searchconsole_service", return_value=mock_gsc_service):
        result = json.loads(seo_striking_distance(SITE, min_impressions=50))
    assert result["_meta"]["params"]["min_impressions"] == 50


def test_striking_distance_empty_rows(mock_gsc_service):
    mock_gsc_service.searchanalytics.return_value.query.return_value.execute.return_value = {"rows": []}
    with patch("gsc_mcp.tools.seo.get_searchconsole_service", return_value=mock_gsc_service):
        result = json.loads(seo_striking_distance(SITE))
    assert result["queries"] == []
    assert "_meta" in result


def test_striking_distance_row_has_expected_fields(mock_gsc_service):
    mock_gsc_service.searchanalytics.return_value.query.return_value.execute.return_value = {
        "rows": [_make_query_row("test", 10.0, 200)]
    }
    with patch("gsc_mcp.tools.seo.get_searchconsole_service", return_value=mock_gsc_service):
        result = json.loads(seo_striking_distance(SITE))
    q = result["queries"][0]
    assert "query" in q
    assert "position" in q
    assert "clicks" in q
    assert "impressions" in q
    assert "ctr" in q


def test_striking_distance_uses_lagged_date_range(mock_gsc_service):
    """end must be today - 3 days (3-day GSC lag)."""
    mock_gsc_service.searchanalytics.return_value.query.return_value.execute.return_value = {"rows": []}
    with patch("gsc_mcp.tools.seo.get_searchconsole_service", return_value=mock_gsc_service):
        result = json.loads(seo_striking_distance(SITE, days=28))
    expected_end = (date.today() - timedelta(days=3)).isoformat()
    assert result["date_range"]["end"] == expected_end


# ===========================
# seo_cannibalization tests
# ===========================

def _make_qp_row(query, page, clicks, impressions, position=10.0):
    return {
        "keys": [query, page],
        "clicks": clicks,
        "impressions": impressions,
        "ctr": round(clicks / impressions if impressions else 0, 4),
        "position": position,
    }


_ROWS_CANNIBAL_BASIC = [
    _make_qp_row("best shoes", "https://x.com/page1", 60, 1000, 5.0),
    _make_qp_row("best shoes", "https://x.com/page2", 40, 800, 8.0),
    _make_qp_row("buy shoes", "https://x.com/page1", 80, 2000, 3.0),  # single page
]


def test_cannibalization_returns_conflicts_key(mock_gsc_service):
    mock_gsc_service.searchanalytics.return_value.query.return_value.execute.return_value = {
        "rows": _ROWS_CANNIBAL_BASIC
    }
    with patch("gsc_mcp.tools.seo.get_searchconsole_service", return_value=mock_gsc_service):
        result = json.loads(seo_cannibalization(SITE))
    assert "conflicts" in result
    assert "_meta" in result


def test_cannibalization_two_pages_one_group(mock_gsc_service):
    mock_gsc_service.searchanalytics.return_value.query.return_value.execute.return_value = {
        "rows": _ROWS_CANNIBAL_BASIC
    }
    with patch("gsc_mcp.tools.seo.get_searchconsole_service", return_value=mock_gsc_service):
        result = json.loads(seo_cannibalization(SITE, min_impressions=0))
    conflict_queries = [c["query"] for c in result["conflicts"]]
    assert "best shoes" in conflict_queries


def test_cannibalization_single_page_excluded(mock_gsc_service):
    mock_gsc_service.searchanalytics.return_value.query.return_value.execute.return_value = {
        "rows": _ROWS_CANNIBAL_BASIC
    }
    with patch("gsc_mcp.tools.seo.get_searchconsole_service", return_value=mock_gsc_service):
        result = json.loads(seo_cannibalization(SITE, min_impressions=0))
    conflict_queries = [c["query"] for c in result["conflicts"]]
    assert "buy shoes" not in conflict_queries


def test_cannibalization_score_below_threshold_dropped(mock_gsc_service):
    """95/5 split => HHI ~= 0.905, score ~= 0.095 < 0.1, dropped."""
    rows = [
        _make_qp_row("dominant", "https://x.com/a", 95, 1000),
        _make_qp_row("dominant", "https://x.com/b", 5, 100),
    ]
    mock_gsc_service.searchanalytics.return_value.query.return_value.execute.return_value = {"rows": rows}
    with patch("gsc_mcp.tools.seo.get_searchconsole_service", return_value=mock_gsc_service):
        result = json.loads(seo_cannibalization(SITE, min_impressions=0))
    conflict_queries = [c["query"] for c in result["conflicts"]]
    assert "dominant" not in conflict_queries


def test_cannibalization_score_above_threshold_kept(mock_gsc_service):
    """50/50 split => score = 0.5, kept."""
    rows = [
        _make_qp_row("split", "https://x.com/a", 50, 500),
        _make_qp_row("split", "https://x.com/b", 50, 500),
    ]
    mock_gsc_service.searchanalytics.return_value.query.return_value.execute.return_value = {"rows": rows}
    with patch("gsc_mcp.tools.seo.get_searchconsole_service", return_value=mock_gsc_service):
        result = json.loads(seo_cannibalization(SITE, min_impressions=0))
    conflict_queries = [c["query"] for c in result["conflicts"]]
    assert "split" in conflict_queries
    score = next(c["conflict_score"] for c in result["conflicts"] if c["query"] == "split")
    assert abs(score - 0.5) < 0.001


def test_cannibalization_zero_click_n2_score_is_0_5(mock_gsc_service):
    """Zero-click, n=2: uniform HHI = 1/2, conflict_score = 0.5."""
    rows = [
        _make_qp_row("zero", "https://x.com/a", 0, 500),
        _make_qp_row("zero", "https://x.com/b", 0, 500),
    ]
    mock_gsc_service.searchanalytics.return_value.query.return_value.execute.return_value = {"rows": rows}
    with patch("gsc_mcp.tools.seo.get_searchconsole_service", return_value=mock_gsc_service):
        result = json.loads(seo_cannibalization(SITE, min_impressions=0))
    assert len(result["conflicts"]) == 1
    assert abs(result["conflicts"][0]["conflict_score"] - 0.5) < 0.001


def test_cannibalization_zero_click_n5_score_is_0_8(mock_gsc_service):
    """Zero-click, n=5: uniform HHI = 1/5 = 0.2, conflict_score = 0.8."""
    rows = [
        _make_qp_row("five", f"https://x.com/p{i}", 0, 100) for i in range(5)
    ]
    mock_gsc_service.searchanalytics.return_value.query.return_value.execute.return_value = {"rows": rows}
    with patch("gsc_mcp.tools.seo.get_searchconsole_service", return_value=mock_gsc_service):
        result = json.loads(seo_cannibalization(SITE, min_impressions=0))
    assert len(result["conflicts"]) == 1
    assert abs(result["conflicts"][0]["conflict_score"] - 0.8) < 0.001


def test_cannibalization_no_zero_division_error(mock_gsc_service):
    rows = [
        _make_qp_row("safe", "https://x.com/a", 0, 200),
        _make_qp_row("safe", "https://x.com/b", 0, 200),
    ]
    mock_gsc_service.searchanalytics.return_value.query.return_value.execute.return_value = {"rows": rows}
    with patch("gsc_mcp.tools.seo.get_searchconsole_service", return_value=mock_gsc_service):
        result = json.loads(seo_cannibalization(SITE, min_impressions=0))
    assert "conflicts" in result


def test_cannibalization_min_impressions_by_query_total(mock_gsc_service):
    """min_impressions filters on total query impressions (500 = 400+100 >= 500)."""
    rows = [
        _make_qp_row("combo", "https://x.com/big", 40, 400),
        _make_qp_row("combo", "https://x.com/small", 10, 100),
    ]
    mock_gsc_service.searchanalytics.return_value.query.return_value.execute.return_value = {"rows": rows}
    with patch("gsc_mcp.tools.seo.get_searchconsole_service", return_value=mock_gsc_service):
        result = json.loads(seo_cannibalization(SITE, min_impressions=500))
    assert any(c["query"] == "combo" for c in result["conflicts"])


def test_cannibalization_query_below_min_impressions_excluded(mock_gsc_service):
    rows = [
        _make_qp_row("low", "https://x.com/a", 5, 20),
        _make_qp_row("low", "https://x.com/b", 5, 20),
    ]
    mock_gsc_service.searchanalytics.return_value.query.return_value.execute.return_value = {"rows": rows}
    with patch("gsc_mcp.tools.seo.get_searchconsole_service", return_value=mock_gsc_service):
        result = json.loads(seo_cannibalization(SITE, min_impressions=100))
    assert not any(c["query"] == "low" for c in result["conflicts"])


def test_cannibalization_three_page_hhi(mock_gsc_service):
    """Three pages: HHI = 0.5^2 + 0.3^2 + 0.2^2 = 0.38, conflict = 0.62."""
    rows = [
        _make_qp_row("triple", "https://x.com/a", 50, 500),
        _make_qp_row("triple", "https://x.com/b", 30, 300),
        _make_qp_row("triple", "https://x.com/c", 20, 200),
    ]
    mock_gsc_service.searchanalytics.return_value.query.return_value.execute.return_value = {"rows": rows}
    with patch("gsc_mcp.tools.seo.get_searchconsole_service", return_value=mock_gsc_service):
        result = json.loads(seo_cannibalization(SITE, min_impressions=0))
    conflict = next(c for c in result["conflicts"] if c["query"] == "triple")
    assert abs(conflict["conflict_score"] - 0.62) < 0.01


def test_cannibalization_pages_have_page_field(mock_gsc_service):
    mock_gsc_service.searchanalytics.return_value.query.return_value.execute.return_value = {
        "rows": _ROWS_CANNIBAL_BASIC
    }
    with patch("gsc_mcp.tools.seo.get_searchconsole_service", return_value=mock_gsc_service):
        result = json.loads(seo_cannibalization(SITE, min_impressions=0))
    for c in result["conflicts"]:
        for p in c["pages"]:
            assert "page" in p


def test_cannibalization_empty_rows(mock_gsc_service):
    mock_gsc_service.searchanalytics.return_value.query.return_value.execute.return_value = {"rows": []}
    with patch("gsc_mcp.tools.seo.get_searchconsole_service", return_value=mock_gsc_service):
        result = json.loads(seo_cannibalization(SITE))
    assert result["conflicts"] == []


# ===========================
# seo_lost_queries tests
# ===========================

def _make_q_row(query, clicks, impressions=1000):
    return {
        "keys": [query],
        "clicks": clicks,
        "impressions": impressions,
        "ctr": 0.05,
        "position": 10.0,
    }


_PREV_ROWS = [
    _make_q_row("seo tutorial", 100),
    _make_q_row("python guide", 50),
    _make_q_row("small traffic", 4),   # prev < 5, excluded
    _make_q_row("stable query", 30),
]

_CURR_ROWS = [
    _make_q_row("seo tutorial", 10),   # 90% drop, prev=100 >= 5
    _make_q_row("python guide", 45),   # 10% drop, not >= 80%
    _make_q_row("small traffic", 0),   # prev < 5, excluded
    _make_q_row("stable query", 29),   # ~3% drop, not flagged
]

_PREV_WITH_GONE = _PREV_ROWS + [_make_q_row("gone query", 20)]
_CURR_WITHOUT_GONE = _CURR_ROWS  # "gone query" absent in curr


def test_lost_queries_returns_lost_queries_key(mock_gsc_service):
    mock_gsc_service.searchanalytics.return_value.query.return_value.execute.side_effect = [
        {"rows": _PREV_ROWS}, {"rows": _CURR_ROWS}
    ]
    with patch("gsc_mcp.tools.seo.get_searchconsole_service", return_value=mock_gsc_service):
        result = json.loads(seo_lost_queries(SITE))
    assert "lost_queries" in result
    assert "_meta" in result


def test_lost_queries_flags_drop_80pct(mock_gsc_service):
    mock_gsc_service.searchanalytics.return_value.query.return_value.execute.side_effect = [
        {"rows": _PREV_ROWS}, {"rows": _CURR_ROWS}
    ]
    with patch("gsc_mcp.tools.seo.get_searchconsole_service", return_value=mock_gsc_service):
        result = json.loads(seo_lost_queries(SITE))
    queries = [q["query"] for q in result["lost_queries"]]
    assert "seo tutorial" in queries


def test_lost_queries_ignores_small_drop(mock_gsc_service):
    mock_gsc_service.searchanalytics.return_value.query.return_value.execute.side_effect = [
        {"rows": _PREV_ROWS}, {"rows": _CURR_ROWS}
    ]
    with patch("gsc_mcp.tools.seo.get_searchconsole_service", return_value=mock_gsc_service):
        result = json.loads(seo_lost_queries(SITE))
    queries = [q["query"] for q in result["lost_queries"]]
    assert "python guide" not in queries
    assert "stable query" not in queries


def test_lost_queries_prev_less_than_5_not_flagged(mock_gsc_service):
    mock_gsc_service.searchanalytics.return_value.query.return_value.execute.side_effect = [
        {"rows": _PREV_ROWS}, {"rows": _CURR_ROWS}
    ]
    with patch("gsc_mcp.tools.seo.get_searchconsole_service", return_value=mock_gsc_service):
        result = json.loads(seo_lost_queries(SITE))
    queries = [q["query"] for q in result["lost_queries"]]
    assert "small traffic" not in queries


def test_lost_queries_absent_in_curr_flagged(mock_gsc_service):
    """Query present in prev but absent in curr (100% loss) is flagged."""
    mock_gsc_service.searchanalytics.return_value.query.return_value.execute.side_effect = [
        {"rows": _PREV_WITH_GONE}, {"rows": _CURR_WITHOUT_GONE}
    ]
    with patch("gsc_mcp.tools.seo.get_searchconsole_service", return_value=mock_gsc_service):
        result = json.loads(seo_lost_queries(SITE))
    queries = [q["query"] for q in result["lost_queries"]]
    assert "gone query" in queries
    gone = next(q for q in result["lost_queries"] if q["query"] == "gone query")
    assert gone["clicks_current"] == 0
    assert gone["drop_pct"] == 1.0


def test_lost_queries_new_query_in_curr_not_flagged(mock_gsc_service):
    curr_with_new = _CURR_ROWS + [_make_q_row("brand new query", 50)]
    mock_gsc_service.searchanalytics.return_value.query.return_value.execute.side_effect = [
        {"rows": _PREV_ROWS}, {"rows": curr_with_new}
    ]
    with patch("gsc_mcp.tools.seo.get_searchconsole_service", return_value=mock_gsc_service):
        result = json.loads(seo_lost_queries(SITE))
    queries = [q["query"] for q in result["lost_queries"]]
    assert "brand new query" not in queries


def test_lost_queries_has_period_keys(mock_gsc_service):
    mock_gsc_service.searchanalytics.return_value.query.return_value.execute.side_effect = [
        {"rows": _PREV_ROWS}, {"rows": _CURR_ROWS}
    ]
    with patch("gsc_mcp.tools.seo.get_searchconsole_service", return_value=mock_gsc_service):
        result = json.loads(seo_lost_queries(SITE))
    assert "period_a" in result
    assert "period_b" in result
    assert "start" in result["period_a"]
    assert "end" in result["period_a"]


def test_lost_queries_no_lag_end_b_is_today(mock_gsc_service):
    """end_b must be today (no lag, matching traffic_drops behaviour)."""
    mock_gsc_service.searchanalytics.return_value.query.return_value.execute.side_effect = [
        {"rows": []}, {"rows": []}
    ]
    with patch("gsc_mcp.tools.seo.get_searchconsole_service", return_value=mock_gsc_service):
        result = json.loads(seo_lost_queries(SITE))
    assert result["period_b"]["end"] == date.today().isoformat()


def test_lost_queries_empty_prev(mock_gsc_service):
    mock_gsc_service.searchanalytics.return_value.query.return_value.execute.side_effect = [
        {"rows": []}, {"rows": _CURR_ROWS}
    ]
    with patch("gsc_mcp.tools.seo.get_searchconsole_service", return_value=mock_gsc_service):
        result = json.loads(seo_lost_queries(SITE))
    assert result["lost_queries"] == []


def test_lost_queries_empty_curr_flags_prev_above_threshold(mock_gsc_service):
    """All prev absent in curr: those with prev >= 5 flagged."""
    mock_gsc_service.searchanalytics.return_value.query.return_value.execute.side_effect = [
        {"rows": _PREV_ROWS}, {"rows": []}
    ]
    with patch("gsc_mcp.tools.seo.get_searchconsole_service", return_value=mock_gsc_service):
        result = json.loads(seo_lost_queries(SITE))
    lost = [q["query"] for q in result["lost_queries"]]
    assert "seo tutorial" in lost
    assert "python guide" in lost
    assert "stable query" in lost
    assert "small traffic" not in lost
