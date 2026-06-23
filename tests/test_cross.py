import json
import math
import pytest
from unittest.mock import patch

from gsc_mcp.tools.cross import (
    _normalize_url,
    traffic_health_check,
    page_analysis,
)

SITE = "sc-domain:example.com"


def _gsc_json(rows, date_range=None):
    return json.dumps({
        "site": SITE,
        "date_range": date_range or {"start": "2026-05-01", "end": "2026-05-28"},
        "rows": rows,
        "_meta": {"tool": "get_search_analytics", "params": {}},
    })


def _ga4_json(pages):
    return json.dumps({
        "start_date": "28daysAgo",
        "end_date": "today",
        "count": len(pages),
        "pages": pages,
        "_meta": {"tool": "ga4_organic_landing_pages", "params": {}},
    })


def _ga4_page(landing_page, sessions=100, engaged_sessions=70, conversions=5.0):
    return {
        "landing_page": landing_page,
        "sessions": sessions,
        "engaged_sessions": engaged_sessions,
        "bounce_rate": 0.30,
        "avg_session_duration": 90.0,
        "conversions": conversions,
        "total_revenue": 0.0,
    }


# ---------------------------------------------------------------------------
# _normalize_url
# ---------------------------------------------------------------------------

def test_normalize_url_empty():
    assert _normalize_url("") == ""


def test_normalize_url_absolute_trailing_slash():
    assert _normalize_url("https://example.com/blog/") == "/blog"


def test_normalize_url_absolute_with_query():
    assert _normalize_url("https://example.com/blog?x=1") == "/blog"


def test_normalize_url_relative_trailing_slash():
    assert _normalize_url("/blog/") == "/blog"


def test_normalize_url_root():
    assert _normalize_url("/") == "/"


def test_normalize_url_absolute_root():
    assert _normalize_url("https://example.com/") == "/"


def test_normalize_url_query_string_relative():
    assert _normalize_url("/blog?ref=home") == "/blog"


# ---------------------------------------------------------------------------
# traffic_health_check
# ---------------------------------------------------------------------------

def _thc(gsc_rows, ga4_pages, site=SITE, days=28):
    with patch("gsc_mcp.tools.cross.get_search_analytics", return_value=_gsc_json(gsc_rows)), \
         patch("gsc_mcp.tools.cross.ga4_organic_landing_pages", return_value=_ga4_json(ga4_pages)):
        return json.loads(traffic_health_check(site, days))


def test_thc_no_gsc_data():
    result = _thc([], [_ga4_page("/home", sessions=50)])
    assert result["status"] == "no_gsc_data"
    assert result["ratio"] is None
    assert result["total_gsc_clicks"] == 0


def test_thc_tracking_gap():
    # ratio = 50/100 = 0.5 < 0.6
    result = _thc(
        [{"clicks": 100, "impressions": 500, "ctr": 0.2, "position": 3.0}],
        [_ga4_page("/home", sessions=50)],
    )
    assert result["status"] == "tracking_gap"
    assert result["ratio"] == pytest.approx(0.5, rel=1e-3)


def test_thc_filter_issue():
    # ratio = 150/100 = 1.5 > 1.3
    result = _thc(
        [{"clicks": 100, "impressions": 500, "ctr": 0.2, "position": 3.0}],
        [_ga4_page("/home", sessions=150)],
    )
    assert result["status"] == "filter_issue"


def test_thc_healthy():
    # ratio = 90/100 = 0.9, between 0.6 and 1.3
    result = _thc(
        [{"clicks": 100, "impressions": 500, "ctr": 0.2, "position": 3.0}],
        [_ga4_page("/home", sessions=90)],
    )
    assert result["status"] == "healthy"


def test_thc_boundary_low_exact():
    # ratio = 60/100 = 0.6 exactly -> healthy (strict <)
    result = _thc(
        [{"clicks": 100, "impressions": 500, "ctr": 0.2, "position": 3.0}],
        [_ga4_page("/home", sessions=60)],
    )
    assert result["status"] == "healthy"


def test_thc_boundary_high_exact():
    # ratio = 130/100 = 1.3 exactly -> healthy (strict >)
    result = _thc(
        [{"clicks": 100, "impressions": 500, "ctr": 0.2, "position": 3.0}],
        [_ga4_page("/home", sessions=130)],
    )
    assert result["status"] == "healthy"


def test_thc_meta():
    result = _thc(
        [{"clicks": 100, "impressions": 500, "ctr": 0.2, "position": 3.0}],
        [_ga4_page("/home", sessions=90)],
    )
    assert result["_meta"]["tool"] == "traffic_health_check"
    assert result["_meta"]["params"]["site"] == SITE
    assert result["_meta"]["params"]["days"] == 28


def test_thc_output_fields():
    result = _thc(
        [{"clicks": 200, "impressions": 1000, "ctr": 0.2, "position": 3.0}],
        [_ga4_page("/home", sessions=160)],
    )
    for field in ("site", "date_range", "total_gsc_clicks", "total_ga4_sessions", "ratio", "status"):
        assert field in result


# ---------------------------------------------------------------------------
# page_analysis
# ---------------------------------------------------------------------------

def _pa(gsc_rows, ga4_pages, site=SITE, days=28, limit=100):
    with patch("gsc_mcp.tools.cross.get_search_analytics", return_value=_gsc_json(gsc_rows)), \
         patch("gsc_mcp.tools.cross.ga4_organic_landing_pages", return_value=_ga4_json(ga4_pages)):
        return json.loads(page_analysis(site, days, limit))


def test_pa_joined_page():
    """Page present in both GSC and GA4 gets all fields populated."""
    result = _pa(
        [{"page": "https://example.com/blog", "clicks": 50, "impressions": 500, "ctr": 0.1, "position": 5.0}],
        [_ga4_page("/blog", sessions=40, engaged_sessions=30, conversions=2.0)],
    )
    pages = result["pages"]
    assert len(pages) == 1
    p = pages[0]
    assert p["page"] == "/blog"
    assert p["clicks"] == 50
    assert p["sessions"] == 40
    assert p["engagement_rate"] == pytest.approx(0.75)
    assert p["conversions"] == pytest.approx(2.0)
    assert p["opportunity_score"] is not None
    assert p["opportunity_score"] > 0


def test_pa_gsc_only_page():
    """Page only in GSC: GA4 fields are None."""
    result = _pa(
        [{"page": "https://example.com/gsc-only", "clicks": 10, "impressions": 100, "ctr": 0.1, "position": 8.0}],
        [],
    )
    p = result["pages"][0]
    assert p["sessions"] is None
    assert p["engagement_rate"] is None
    assert p["conversions"] is None
    assert p["clicks"] == 10


def test_pa_ga4_only_page():
    """Page only in GA4: GSC fields are None."""
    result = _pa(
        [],
        [_ga4_page("/ga4-only", sessions=20)],
    )
    p = result["pages"][0]
    assert p["clicks"] is None
    assert p["impressions"] is None
    assert p["ctr"] is None
    assert p["position"] is None
    assert p["sessions"] == 20


def test_pa_trailing_slash_join():
    """GSC /services and GA4 /services/ normalise to same path -> 1 entry."""
    result = _pa(
        [{"page": "https://example.com/services", "clicks": 30, "impressions": 300, "ctr": 0.1, "position": 4.0}],
        [_ga4_page("/services/", sessions=25)],
    )
    assert len(result["pages"]) == 1
    p = result["pages"][0]
    assert p["clicks"] == 30
    assert p["sessions"] == 25


def test_pa_query_string_join():
    """GA4 /blog?ref=home and GSC /blog normalise to /blog -> 1 entry."""
    result = _pa(
        [{"page": "https://example.com/blog", "clicks": 20, "impressions": 200, "ctr": 0.1, "position": 6.0}],
        [_ga4_page("/blog?ref=home", sessions=15)],
    )
    assert len(result["pages"]) == 1
    assert result["pages"][0]["page"] == "/blog"


def test_pa_sorted_by_opportunity_score():
    """Pages sorted descending by opportunity_score."""
    result = _pa(
        [
            {"page": "https://example.com/a", "clicks": 1, "impressions": 10, "ctr": 0.1, "position": 20.0},
            {"page": "https://example.com/b", "clicks": 100, "impressions": 5000, "ctr": 0.02, "position": 3.0},
        ],
        [],
    )
    scores = [p["opportunity_score"] for p in result["pages"]]
    assert scores == sorted(scores, reverse=True)


def test_pa_limit():
    """Only top `limit` pages returned."""
    gsc_rows = [
        {"page": f"https://example.com/p{i}", "clicks": i, "impressions": i * 10, "ctr": 0.1, "position": 5.0}
        for i in range(1, 11)
    ]
    result = _pa(gsc_rows, [], limit=5)
    assert len(result["pages"]) == 5


def test_pa_meta():
    result = _pa([], [])
    assert result["_meta"]["tool"] == "page_analysis"
    assert result["_meta"]["params"] == {"site": SITE, "days": 28, "limit": 100, "property_id": None, "hostname": None, "country": None}


def test_thc_property_id_propagated():
    """property_id is forwarded to ga4_organic_landing_pages."""
    gsc_rows = [{"clicks": 100, "impressions": 500, "ctr": 0.2, "position": 3.0}]
    ga4_pages = [_ga4_page("/home", sessions=90)]
    with patch("gsc_mcp.tools.cross.get_search_analytics", return_value=_gsc_json(gsc_rows)), \
         patch("gsc_mcp.tools.cross.ga4_organic_landing_pages", return_value=_ga4_json(ga4_pages)) as mock_ga4:
        traffic_health_check(SITE, property_id="443684366")
    _, kwargs = mock_ga4.call_args
    assert kwargs.get("property_id") == "443684366"


def test_pa_property_id_propagated():
    """property_id is forwarded to ga4_organic_landing_pages."""
    with patch("gsc_mcp.tools.cross.get_search_analytics", return_value=_gsc_json([])), \
         patch("gsc_mcp.tools.cross.ga4_organic_landing_pages", return_value=_ga4_json([])) as mock_ga4:
        page_analysis(SITE, property_id="443684366")
    _, kwargs = mock_ga4.call_args
    assert kwargs.get("property_id") == "443684366"


def test_pa_opportunity_score_formula():
    """Verify opportunity_score matches the documented formula."""
    impressions = 500
    engagement_rate = 30 / 40  # engaged_sessions / sessions
    conversions = 2.0
    expected = (
        math.log10(impressions + 1) * 10
        + engagement_rate * 100
        + math.log10(conversions + 1) * 20
    )
    result = _pa(
        [{"page": "https://example.com/blog", "clicks": 50, "impressions": impressions, "ctr": 0.1, "position": 5.0}],
        [_ga4_page("/blog", sessions=40, engaged_sessions=30, conversions=conversions)],
    )
    assert result["pages"][0]["opportunity_score"] == pytest.approx(round(expected, 2), rel=1e-3)
