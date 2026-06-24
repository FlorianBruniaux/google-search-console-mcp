import json
import math
import pytest
from unittest.mock import patch

from gsc_mcp.tools.cross import (
    _normalize_url,
    content_brief,
    traffic_health_check,
    page_analysis,
    page_health_score,
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
        traffic_health_check(SITE, property_id="987654321")
    _, kwargs = mock_ga4.call_args
    assert kwargs.get("property_id") == "987654321"


def test_pa_property_id_propagated():
    """property_id is forwarded to ga4_organic_landing_pages."""
    with patch("gsc_mcp.tools.cross.get_search_analytics", return_value=_gsc_json([])), \
         patch("gsc_mcp.tools.cross.ga4_organic_landing_pages", return_value=_ga4_json([])) as mock_ga4:
        page_analysis(SITE, property_id="987654321")
    _, kwargs = mock_ga4.call_args
    assert kwargs.get("property_id") == "987654321"


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


# ---------------------------------------------------------------------------
# page_health_score helpers
# ---------------------------------------------------------------------------

URL = "https://example.com/blog"


def _inspect_json(verdict="PASS", indexing_state="INDEXING_ALLOWED"):
    return json.dumps({
        "url": URL,
        "verdict": verdict,
        "robots_txt_state": "ALLOWED",
        "indexing_state": indexing_state,
        "last_crawl": None,
        "page_fetch_state": "SUCCESSFUL",
        "google_canonical": URL,
        "user_canonical": URL,
        "category": "indexed",
        "_meta": {"tool": "inspect_url", "params": {}},
    })


def _ga4_page_perf_json(active_users=100, engagement_rate=0.75):
    return json.dumps({
        "start_date": "30daysAgo",
        "end_date": "today",
        "count": 1,
        "pages": [
            {
                "page_path": "/blog",
                "page_views": 200,
                "active_users": active_users,
                "avg_session_duration": 90.0,
                "engagement_rate": engagement_rate,
                "bounce_rate": 0.25,
                "conversions": 5.0,
                "total_revenue": 0.0,
            }
        ],
        "_meta": {"tool": "ga4_page_performance", "params": {}},
    })


def _crux_json(lcp="good", inp="good", cls_="good"):
    return json.dumps({
        "url": URL,
        "form_factor": "ALL_FORM_FACTORS",
        "metrics": {
            "largest_contentful_paint": {"p75": 1800, "rating": lcp},
            "interaction_to_next_paint": {"p75": 100, "rating": inp},
            "cumulative_layout_shift": {"p75": 0.05, "rating": cls_},
        },
        "_meta": {"tool": "crux_page_vitals", "params": {}},
    })


def _crux_not_enough_data_json():
    return json.dumps({
        "url": URL,
        "form_factor": "ALL_FORM_FACTORS",
        "verdict": "not_enough_data",
        "_meta": {"tool": "crux_page_vitals", "params": {}},
    })


def _schema_json(schemas_detected=1, errors_count=0):
    schemas = []
    if schemas_detected > 0:
        schemas.append({
            "type": "Article",
            "valid": errors_count == 0,
            "missing_required_fields": ["headline"] * errors_count,
            "fields_present": ["author", "datePublished"],
        })
    return json.dumps({
        "url": URL,
        "schemas_detected": schemas_detected,
        "schemas": schemas,
        "recommendations": [],
        "verdict": "healthy" if schemas_detected > 0 and errors_count == 0 else "invalid_schemas",
        "_meta": {"tool": "schema_validate", "params": {}},
    })


def _phs(inspect_rv, ga4_rv, crux_rv, schema_rv, property_id=None, hostname=None, country=None):
    """Run page_health_score with all four components mocked."""
    with patch("gsc_mcp.tools.cross.inspect_url", return_value=inspect_rv), \
         patch("gsc_mcp.tools.cross.ga4_page_performance", return_value=ga4_rv), \
         patch("gsc_mcp.tools.cross.crux_page_vitals", return_value=crux_rv), \
         patch("gsc_mcp.tools.cross.schema_validate", return_value=schema_rv):
        return json.loads(page_health_score(SITE, URL, property_id=property_id, hostname=hostname, country=country))


# ---------------------------------------------------------------------------
# page_health_score tests
# ---------------------------------------------------------------------------

def test_phs_all_perfect_score_100():
    """All components succeed with max scores -> score == 100."""
    result = _phs(
        _inspect_json(verdict="PASS", indexing_state="INDEXING_ALLOWED"),
        _ga4_page_perf_json(active_users=100, engagement_rate=0.75),
        _crux_json(lcp="good", inp="good", cls_="good"),
        _schema_json(schemas_detected=1, errors_count=0),
    )
    assert result["score"] == 100
    assert result["components"]["gsc"]["score"] == 30
    assert result["components"]["ga4"]["score"] == 25
    assert result["components"]["crux"]["score"] == 25
    assert result["components"]["schema"]["score"] == 20


def test_phs_ga4_raises_runtime_error_renormalized():
    """GA4 RuntimeError -> ga4 available=False, score renormalized over 75 pts."""
    with patch("gsc_mcp.tools.cross.inspect_url", return_value=_inspect_json()), \
         patch("gsc_mcp.tools.cross.ga4_page_performance", side_effect=RuntimeError("no GA4 creds")), \
         patch("gsc_mcp.tools.cross.crux_page_vitals", return_value=_crux_json()), \
         patch("gsc_mcp.tools.cross.schema_validate", return_value=_schema_json()):
        result = json.loads(page_health_score(SITE, URL))

    assert result["components"]["ga4"]["available"] is False
    assert result["components"]["ga4"]["score"] == 0
    # max_available = 30+25+20 = 75; earned = 30+25+20 = 75 -> score = 100
    assert result["score"] == 100


def test_phs_crux_not_enough_data_treated_as_unavailable():
    """CrUX verdict == not_enough_data -> crux available=False, no crash."""
    result = _phs(
        _inspect_json(),
        _ga4_page_perf_json(),
        _crux_not_enough_data_json(),
        _schema_json(),
    )
    assert result["components"]["crux"]["available"] is False
    assert result["components"]["crux"]["score"] == 0
    # score renormalized over 30+25+20 = 75 pts
    assert result["score"] == 100


def test_phs_schema_with_errors_partial_score():
    """Schema with validation errors -> schemas_found pts but not error-free pts."""
    result = _phs(
        _inspect_json(),
        _ga4_page_perf_json(),
        _crux_json(),
        _schema_json(schemas_detected=1, errors_count=1),
    )
    # schema: 10 pts for schemas_found, 0 pts for errors -> total schema = 10
    assert result["components"]["schema"]["score"] == 10
    assert result["components"]["schema"]["available"] is True
    # max 100, earned = 30+25+25+10 = 90 -> score = 90
    assert result["score"] == 90


def test_phs_meta_block_correct():
    """_meta block present with tool='page_health_score' and correct params."""
    result = _phs(
        _inspect_json(),
        _ga4_page_perf_json(),
        _crux_json(),
        _schema_json(),
    )
    assert "_meta" in result
    assert result["_meta"]["tool"] == "page_health_score"
    assert result["_meta"]["params"]["site"] == SITE
    assert result["_meta"]["params"]["url"] == URL
    assert result["_meta"]["params"]["property_id"] is None


def test_phs_all_fail_score_zero():
    """All components raise RuntimeError -> score == 0."""
    with patch("gsc_mcp.tools.cross.inspect_url", side_effect=RuntimeError("no GSC")), \
         patch("gsc_mcp.tools.cross.ga4_page_performance", side_effect=RuntimeError("no GA4")), \
         patch("gsc_mcp.tools.cross.crux_page_vitals", side_effect=RuntimeError("no CrUX")), \
         patch("gsc_mcp.tools.cross.schema_validate", side_effect=RuntimeError("no schema")):
        result = json.loads(page_health_score(SITE, URL))

    assert result["score"] == 0
    for comp in result["components"].values():
        assert comp["available"] is False


def test_phs_partial_crux_score():
    """CrUX with only LCP good -> 10 pts out of 25."""
    result = _phs(
        _inspect_json(),
        _ga4_page_perf_json(),
        _crux_json(lcp="good", inp="poor", cls_="needs_improvement"),
        _schema_json(),
    )
    assert result["components"]["crux"]["score"] == 10


def test_phs_ga4_zero_active_users():
    """GA4 with 0 active_users -> 0 pts for sessions check but engagement still counted."""
    result = _phs(
        _inspect_json(),
        _ga4_page_perf_json(active_users=0, engagement_rate=0.75),
        _crux_json(),
        _schema_json(),
    )
    # active_users = 0 -> no 15 pts; engagement_rate 0.75 > 0.4 -> 10 pts
    assert result["components"]["ga4"]["score"] == 10


def test_phs_output_fields():
    """Verify top-level output fields are present."""
    result = _phs(_inspect_json(), _ga4_page_perf_json(), _crux_json(), _schema_json())
    assert "url" in result
    assert "score" in result
    assert "components" in result
    for comp_name in ("gsc", "ga4", "crux", "schema"):
        assert comp_name in result["components"]
        comp = result["components"][comp_name]
        assert "score" in comp
        assert "max" in comp
        assert "available" in comp


def test_phs_schema_no_schemas_detected_zero_pts():
    """Schema with no schemas detected -> 0 pts (no error-free bonus without schemas)."""
    result = _phs(
        _inspect_json(),
        _ga4_page_perf_json(),
        _crux_json(),
        _schema_json(schemas_detected=0, errors_count=0),
    )
    # schema: 0 pts because schemas_detected=0, no error-free bonus
    assert result["components"]["schema"]["score"] == 0
    assert result["components"]["schema"]["available"] is True
    # max 100, earned = 30+25+25+0 = 80 -> score = 80
    assert result["score"] == 80


def test_phs_meta_includes_hostname_and_country():
    """_meta params includes hostname and country when provided."""
    result = _phs(
        _inspect_json(),
        _ga4_page_perf_json(),
        _crux_json(),
        _schema_json(),
        property_id="987654321",
        hostname="blog.example.com",
        country="US",
    )
    assert result["_meta"]["params"]["hostname"] == "blog.example.com"
    assert result["_meta"]["params"]["country"] == "US"
    assert result["_meta"]["params"]["property_id"] == "987654321"


# ---------------------------------------------------------------------------
# content_brief helpers
# ---------------------------------------------------------------------------

PAGE_URL = "https://example.com/blog"
PAGE_PATH = "/blog"


def _gsc_query_page_json(rows, date_range=None):
    """GSC response with query+page dimensions."""
    return json.dumps({
        "site": SITE,
        "date_range": date_range or {"start": "2025-03-24", "end": "2025-06-23"},
        "rows": rows,
        "_meta": {"tool": "get_search_analytics", "params": {}},
    })


def _gsc_qp_row(query, page, clicks=10, impressions=100, position=5.0):
    return {"query": query, "page": page, "clicks": clicks, "impressions": impressions, "ctr": 0.1, "position": position}


def _ga4_perf_json(active_users=200, engagement_rate=0.65):
    return json.dumps({
        "start_date": "90daysAgo",
        "end_date": "today",
        "count": 1,
        "pages": [
            {
                "page_path": PAGE_PATH,
                "page_views": 400,
                "active_users": active_users,
                "avg_session_duration": 120.0,
                "engagement_rate": engagement_rate,
                "bounce_rate": 0.35,
                "conversions": 3.0,
                "total_revenue": 0.0,
            }
        ],
        "_meta": {"tool": "ga4_page_performance", "params": {}},
    })


def _cb(gsc_rows, ga4_rv=None, page_url=PAGE_URL, site=SITE, days=90, property_id=None):
    """Run content_brief with mocked GSC and GA4."""
    if ga4_rv is None:
        ga4_rv = _ga4_perf_json()
    with patch("gsc_mcp.tools.cross.get_search_analytics", return_value=_gsc_query_page_json(gsc_rows)), \
         patch("gsc_mcp.tools.cross.ga4_page_performance", return_value=ga4_rv):
        return json.loads(content_brief(site, page_url, days, property_id))


# ---------------------------------------------------------------------------
# content_brief tests
# ---------------------------------------------------------------------------

def test_content_brief_top_queries_and_current_focus():
    """Top queries sorted by clicks; current_focus == query with highest clicks."""
    rows = [
        _gsc_qp_row("seo tips", PAGE_URL, clicks=50),
        _gsc_qp_row("seo guide", PAGE_URL, clicks=120),
        _gsc_qp_row("seo basics", PAGE_URL, clicks=30),
    ]
    result = _cb(rows)
    assert result["current_focus"] == "seo guide"
    assert result["top_queries"][0]["query"] == "seo guide"
    assert result["top_queries"][0]["clicks"] == 120
    assert len(result["top_queries"]) == 3


def test_content_brief_question_queries_classified():
    """Only queries starting with who/what/when/where/why/how are classified."""
    rows = [
        _gsc_qp_row("how to write seo", PAGE_URL, clicks=80),
        _gsc_qp_row("what is seo", PAGE_URL, clicks=60),
        _gsc_qp_row("seo tips", PAGE_URL, clicks=40),
        _gsc_qp_row("why does seo matter", PAGE_URL, clicks=20),
        _gsc_qp_row("best seo tools", PAGE_URL, clicks=10),
    ]
    result = _cb(rows)
    question_queries_text = [q["query"] for q in result["question_queries"]]
    assert "how to write seo" in question_queries_text
    assert "what is seo" in question_queries_text
    assert "why does seo matter" in question_queries_text
    assert "seo tips" not in question_queries_text
    assert "best seo tools" not in question_queries_text
    assert len(result["question_queries"]) == 3


def test_content_brief_ga4_runtime_error_returns_none():
    """GA4 RuntimeError -> ga4 field is None, no crash."""
    rows = [_gsc_qp_row("seo guide", PAGE_URL, clicks=50)]
    with patch("gsc_mcp.tools.cross.get_search_analytics", return_value=_gsc_query_page_json(rows)), \
         patch("gsc_mcp.tools.cross.ga4_page_performance", side_effect=RuntimeError("no GA4 creds")):
        result = json.loads(content_brief(SITE, PAGE_URL))
    assert result["ga4"] is None
    assert result["current_focus"] == "seo guide"


def test_content_brief_page_url_filter_applied():
    """Only rows matching the target page_url are returned, not rows for other pages."""
    other_page = "https://example.com/other"
    rows = [
        _gsc_qp_row("blog query", PAGE_URL, clicks=100),
        _gsc_qp_row("other query", other_page, clicks=999),
    ]
    result = _cb(rows)
    queries = [q["query"] for q in result["top_queries"]]
    assert "blog query" in queries
    assert "other query" not in queries
    assert len(result["top_queries"]) == 1


def test_content_brief_empty_gsc_data():
    """Empty GSC rows -> top_queries=[], current_focus=None, no error."""
    result = _cb([])
    assert result["top_queries"] == []
    assert result["current_focus"] is None
    assert result["question_queries"] == []


def test_content_brief_ga4_sessions_and_engagement_rate():
    """GA4 active_users and engagement_rate are extracted from first page."""
    rows = [_gsc_qp_row("seo", PAGE_URL, clicks=10)]
    result = _cb(rows, ga4_rv=_ga4_perf_json(active_users=350, engagement_rate=0.82))
    assert result["ga4"] is not None
    assert result["ga4"]["active_users"] == 350
    assert result["ga4"]["engagement_rate"] == pytest.approx(0.82)


def test_content_brief_top_20_cap():
    """Only top 20 queries returned even if more match the page."""
    rows = [_gsc_qp_row(f"query {i}", PAGE_URL, clicks=i) for i in range(1, 30)]
    result = _cb(rows)
    assert len(result["top_queries"]) == 20
    # Highest-click query should be first
    assert result["top_queries"][0]["clicks"] == 29


def test_content_brief_meta_block():
    """_meta block has tool='content_brief' and correct params."""
    rows = [_gsc_qp_row("test", PAGE_URL, clicks=5)]
    result = _cb(rows, property_id="123456")
    assert result["_meta"]["tool"] == "content_brief"
    assert result["_meta"]["params"]["site"] == SITE
    assert result["_meta"]["params"]["page_url"] == PAGE_URL
    assert result["_meta"]["params"]["days"] == 90
    assert result["_meta"]["params"]["property_id"] == "123456"


def test_content_brief_question_queries_from_full_filtered_list():
    """question_queries captures question queries beyond the top-20 cap.

    Creates 22 rows: first 20 are non-question queries sorted by clicks desc,
    21st and 22nd are question queries with lower clicks. Tests that question_queries
    includes question queries from the full filtered list, not just from top_queries.
    """
    rows = [
        _gsc_qp_row(f"seo tip {i}", PAGE_URL, clicks=100 - i)
        for i in range(20)
    ] + [
        _gsc_qp_row("how to optimize", PAGE_URL, clicks=10),
        _gsc_qp_row("what are best practices", PAGE_URL, clicks=5),
    ]
    result = _cb(rows)

    # top_queries capped at 20 (non-question)
    assert len(result["top_queries"]) == 20
    assert all(not q["query"].split()[0] in {"who", "what", "when", "where", "why", "how"}
               for q in result["top_queries"])

    # question_queries should include the question queries from full list (ranks 21, 22)
    assert len(result["question_queries"]) == 2
    question_texts = [q["query"] for q in result["question_queries"]]
    assert "how to optimize" in question_texts
    assert "what are best practices" in question_texts


# ---------------------------------------------------------------------------
# Bug-fix regression tests
# ---------------------------------------------------------------------------

def test_phs_ga4_receives_normalized_path_not_absolute_url():
    """page_health_score must pass the relative path to ga4_page_performance, not the full URL."""
    captured = {}

    def fake_ga4_page_performance(**kw):
        captured["page_path"] = kw.get("page_path")
        return _ga4_page_perf_json()

    with patch("gsc_mcp.tools.cross.inspect_url", return_value=_inspect_json()), \
         patch("gsc_mcp.tools.cross.ga4_page_performance", side_effect=fake_ga4_page_performance), \
         patch("gsc_mcp.tools.cross.crux_page_vitals", return_value=_crux_json()), \
         patch("gsc_mcp.tools.cross.schema_validate", return_value=_schema_json()):
        page_health_score(SITE, "https://example.com/article")

    assert captured["page_path"] == "/article", (
        f"Expected '/article' but got {captured['page_path']!r}. "
        "page_health_score must call _normalize_url(url) before passing to ga4_page_performance."
    )


def test_phs_gsc_raises_runtime_error_renormalized_over_remaining_70():
    """GSC RuntimeError -> gsc available=False, score renormalized over GA4+CrUX+schema=70 pts.

    When all remaining components earn full marks the score must be 100.
    """
    with patch("gsc_mcp.tools.cross.inspect_url", side_effect=RuntimeError("no GSC creds")), \
         patch("gsc_mcp.tools.cross.ga4_page_performance", return_value=_ga4_page_perf_json(active_users=100, engagement_rate=0.75)), \
         patch("gsc_mcp.tools.cross.crux_page_vitals", return_value=_crux_json(lcp="good", inp="good", cls_="good")), \
         patch("gsc_mcp.tools.cross.schema_validate", return_value=_schema_json(schemas_detected=1, errors_count=0)):
        result = json.loads(page_health_score(SITE, URL))

    assert result["components"]["gsc"]["available"] is False
    assert result["components"]["gsc"]["score"] == 0
    # max_available = 25+25+20 = 70; earned = 25+25+20 = 70 -> score = 100
    assert result["score"] == 100


def test_content_brief_ga4_empty_pages_returns_none():
    """GA4 responding successfully with pages=[] must set ga4 to None (not an error path)."""
    ga4_empty = json.dumps({
        "start_date": "90daysAgo",
        "end_date": "today",
        "count": 0,
        "pages": [],
        "_meta": {"tool": "ga4_page_performance", "params": {}},
    })
    rows = [_gsc_qp_row("seo guide", PAGE_URL, clicks=50)]
    with patch("gsc_mcp.tools.cross.get_search_analytics", return_value=_gsc_query_page_json(rows)), \
         patch("gsc_mcp.tools.cross.ga4_page_performance", return_value=ga4_empty):
        result = json.loads(content_brief(SITE, PAGE_URL))

    assert result["ga4"] is None
    # The GSC path must still work normally
    assert result["current_focus"] == "seo guide"
