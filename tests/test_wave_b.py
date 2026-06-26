"""Tests for Wave B tools: preload_audit, crux_lcp_subparts, indexnow_submit, parasite_risk."""

import json
from unittest.mock import MagicMock, patch

import httpx
import pytest

from gsc_mcp.tools.content import preload_audit
from gsc_mcp.tools.crux import crux_lcp_subparts
from gsc_mcp.tools.indexing import indexnow_submit
from gsc_mcp.tools.seo import parasite_risk, _parasite_check_url
from gsc_mcp.url_safety import URLSafetyError


# ===========================================================================
# Helpers
# ===========================================================================

def _mock_httpx_resp(text: str = "", status_code: int = 200, headers: dict | None = None):
    """Build a minimal httpx.Response mock for safe_httpx_get."""
    m = MagicMock()
    m.text = text
    m.status_code = status_code
    m.headers = headers or {}
    return m


def _make_crux_client(status_code: int = 200, json_body: dict | None = None):
    """Build a mock httpx.Client context manager for CrUX calls."""
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.json.return_value = json_body or {}
    mock_resp.raise_for_status = MagicMock()
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.post.return_value = mock_resp
    return mock_client


def _make_indexnow_client(status_code: int = 200):
    """Build a mock httpx.Client context manager for IndexNow calls."""
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.post.return_value = mock_resp
    return mock_client


def _crux_lcp_payload(lcp_p75=2800, ttfb=400, delay=200, duration=800, render=1400):
    return {
        "record": {
            "metrics": {
                "largest_contentful_paint": {"percentiles": {"p75": lcp_p75}},
                "largest_contentful_paint_image_time_to_first_byte": {"percentiles": {"p75": ttfb}},
                "largest_contentful_paint_image_resource_load_delay": {"percentiles": {"p75": delay}},
                "largest_contentful_paint_image_resource_load_duration": {"percentiles": {"p75": duration}},
                "largest_contentful_paint_image_element_render_delay": {"percentiles": {"p75": render}},
            }
        }
    }


@pytest.fixture(autouse=True)
def set_crux_key(monkeypatch):
    monkeypatch.setenv("CRUX_API_KEY", "test-key-wave-b")


# ===========================================================================
# preload_audit
# ===========================================================================

_HTML_NO_SPECULATION = """<html><head><title>Test</title></head><body></body></html>"""

_HTML_PREFETCH_ONLY = """<html><head>
<script type="speculationrules">{"prefetch":[{"source":"list","urls":["/"]}]}</script>
</head><body></body></html>"""

_HTML_FULL_SPECULATION = """<html><head>
<script type="speculationrules">{"prefetch":[{"source":"list","urls":["/"]}],"prerender":[{"source":"list","urls":["/next"]}]}</script>
</head><body></body></html>"""

_HTML_PRERENDER_DEPRECATED = """<html><head>
<link rel="prerender" href="/old-page">
</head><body></body></html>"""

_HTML_PRELOAD_IMAGE = """<html><head>
<link rel="preload" as="image" href="/hero.jpg">
<link rel="preload" as="script" href="/app.js">
</head><body></body></html>"""

_HTML_PRELOAD_IMAGE_HIGH = """<html><head>
<link rel="preload" as="image" href="/hero.jpg" fetchpriority="high">
</head><body></body></html>"""


def test_preload_audit_not_implemented():
    """No speculation rules at all returns not_implemented."""
    with patch("gsc_mcp.tools.content.safe_httpx_get", return_value=_mock_httpx_resp(_HTML_NO_SPECULATION)):
        result = json.loads(preload_audit("https://example.com/"))
    assert result["verdict"] == "not_implemented"
    assert result["speculation_rules_html"] is False
    assert result["speculation_rules_header"] is False
    assert result["speculation_actions"] == []


def test_preload_audit_optimised():
    """Both prefetch and prerender with no bfcache killer returns optimised."""
    with patch("gsc_mcp.tools.content.safe_httpx_get", return_value=_mock_httpx_resp(_HTML_FULL_SPECULATION)):
        result = json.loads(preload_audit("https://example.com/"))
    assert result["verdict"] == "optimised"
    assert "prefetch" in result["speculation_actions"]
    assert "prerender" in result["speculation_actions"]
    assert result["bfcache_no_store"] is False


def test_preload_audit_improvements_available_missing_prerender():
    """Only prefetch action defined results in improvements_available."""
    with patch("gsc_mcp.tools.content.safe_httpx_get", return_value=_mock_httpx_resp(_HTML_PREFETCH_ONLY)):
        result = json.loads(preload_audit("https://example.com/"))
    assert result["verdict"] == "improvements_available"
    assert result["speculation_rules_html"] is True
    assert "prerender" not in result["speculation_actions"]


def test_preload_audit_bfcache_no_store():
    """cache-control: no-store in response headers causes improvements_available even with full speculation."""
    headers = {"cache-control": "no-store, no-cache"}
    with patch("gsc_mcp.tools.content.safe_httpx_get",
               return_value=_mock_httpx_resp(_HTML_FULL_SPECULATION, headers=headers)):
        result = json.loads(preload_audit("https://example.com/"))
    assert result["verdict"] == "improvements_available"
    assert result["bfcache_no_store"] is True
    issue_checks = [i["check"] for i in result["issues"]]
    assert "bfcache" in issue_checks


def test_preload_audit_speculation_header():
    """Speculation-Rules response header detected correctly."""
    headers = {"Speculation-Rules": '"/speculationrules.json"'}
    with patch("gsc_mcp.tools.content.safe_httpx_get",
               return_value=_mock_httpx_resp(_HTML_NO_SPECULATION, headers=headers)):
        result = json.loads(preload_audit("https://example.com/"))
    assert result["speculation_rules_header"] is True
    # Has header but no actions defined in HTML body, so improvements_available
    assert result["verdict"] == "improvements_available"


def test_preload_audit_prerender_deprecated():
    """Deprecated <link rel="prerender"> is flagged in issues."""
    with patch("gsc_mcp.tools.content.safe_httpx_get",
               return_value=_mock_httpx_resp(_HTML_PRERENDER_DEPRECATED)):
        result = json.loads(preload_audit("https://example.com/"))
    assert result["prerender_deprecated"] is True
    checks = [i["check"] for i in result["issues"]]
    assert "prerender_deprecated" in checks


def test_preload_audit_preload_tags_parsed():
    """Preload tags are extracted with as, href, and fetchpriority attributes."""
    with patch("gsc_mcp.tools.content.safe_httpx_get",
               return_value=_mock_httpx_resp(_HTML_PRELOAD_IMAGE)):
        result = json.loads(preload_audit("https://example.com/"))
    assert len(result["preload_tags"]) == 2
    image_tag = next(t for t in result["preload_tags"] if t["as"] == "image")
    assert image_tag["href"] == "/hero.jpg"
    assert image_tag["fetchpriority"] is None


def test_preload_audit_image_fetchpriority_issue():
    """Image preload without fetchpriority=high triggers an issue."""
    with patch("gsc_mcp.tools.content.safe_httpx_get",
               return_value=_mock_httpx_resp(_HTML_PRELOAD_IMAGE)):
        result = json.loads(preload_audit("https://example.com/"))
    checks = [i["check"] for i in result["issues"]]
    assert "lcp_fetchpriority" in checks


def test_preload_audit_no_issue_when_fetchpriority_high():
    """Image preload with fetchpriority=high does NOT trigger the lcp_fetchpriority issue."""
    with patch("gsc_mcp.tools.content.safe_httpx_get",
               return_value=_mock_httpx_resp(_HTML_PRELOAD_IMAGE_HIGH)):
        result = json.loads(preload_audit("https://example.com/"))
    checks = [i["check"] for i in result["issues"]]
    assert "lcp_fetchpriority" not in checks


def test_preload_audit_url_safety_error():
    """URLSafetyError from safe_httpx_get returns fetch_error verdict."""
    with patch("gsc_mcp.tools.content.safe_httpx_get", side_effect=URLSafetyError("blocked")):
        result = json.loads(preload_audit("https://192.168.1.1/"))
    assert result["verdict"] == "fetch_error"
    assert "blocked" in result["error"]


def test_preload_audit_http_error():
    """httpx.HTTPError returns fetch_error verdict."""
    with patch("gsc_mcp.tools.content.safe_httpx_get",
               side_effect=httpx.ConnectError("refused")):
        result = json.loads(preload_audit("https://down.example.com/"))
    assert result["verdict"] == "fetch_error"


def test_preload_audit_meta():
    """_meta block contains correct tool name and url param."""
    with patch("gsc_mcp.tools.content.safe_httpx_get",
               return_value=_mock_httpx_resp(_HTML_NO_SPECULATION)):
        result = json.loads(preload_audit("https://example.com/"))
    assert result["_meta"]["tool"] == "preload_audit"
    assert result["_meta"]["params"]["url"] == "https://example.com/"


# ===========================================================================
# crux_lcp_subparts
# ===========================================================================

def test_crux_lcp_subparts_returns_data():
    """Normal response: lcp_p75_ms, subparts, and dominant_phase populated."""
    payload = _crux_lcp_payload(lcp_p75=3200, ttfb=400, delay=200, duration=800, render=1800)
    with patch("gsc_mcp.tools.crux.httpx.Client", return_value=_make_crux_client(200, payload)):
        result = json.loads(crux_lcp_subparts("https://example.com/"))
    assert result["lcp_p75_ms"] == 3200
    assert result["subparts"]["ttfb_ms"] == 400
    assert result["subparts"]["resource_load_delay_ms"] == 200
    assert result["subparts"]["resource_load_duration_ms"] == 800
    assert result["subparts"]["render_delay_ms"] == 1800
    assert result["subparts"]["dominant_phase"] == "render_delay"


def test_crux_lcp_subparts_dominant_phase_ttfb():
    """TTFB largest value sets dominant_phase to ttfb."""
    payload = _crux_lcp_payload(lcp_p75=2000, ttfb=1600, delay=100, duration=100, render=200)
    with patch("gsc_mcp.tools.crux.httpx.Client", return_value=_make_crux_client(200, payload)):
        result = json.loads(crux_lcp_subparts("https://example.com/"))
    assert result["subparts"]["dominant_phase"] == "ttfb"


def test_crux_lcp_subparts_not_enough_data():
    """404 from CrUX API returns not_enough_data verdict."""
    with patch("gsc_mcp.tools.crux.httpx.Client", return_value=_make_crux_client(404)):
        result = json.loads(crux_lcp_subparts("https://tiny-site.example/"))
    assert result["verdict"] == "not_enough_data"


def test_crux_lcp_subparts_missing_key(monkeypatch):
    """Missing CRUX_API_KEY environment variable returns missing_key verdict."""
    monkeypatch.delenv("CRUX_API_KEY", raising=False)
    result = json.loads(crux_lcp_subparts("https://example.com/"))
    assert result["verdict"] == "missing_key"


def test_crux_lcp_subparts_lcp_rating_good():
    """LCP p75=1800ms rates as good (threshold 2500ms)."""
    payload = _crux_lcp_payload(lcp_p75=1800)
    with patch("gsc_mcp.tools.crux.httpx.Client", return_value=_make_crux_client(200, payload)):
        result = json.loads(crux_lcp_subparts("https://example.com/"))
    assert result["lcp_rating"] == "good"
    assert result["verdict"] == "good"


def test_crux_lcp_subparts_lcp_rating_needs_improvement():
    """LCP p75=3000ms rates as needs_improvement."""
    payload = _crux_lcp_payload(lcp_p75=3000)
    with patch("gsc_mcp.tools.crux.httpx.Client", return_value=_make_crux_client(200, payload)):
        result = json.loads(crux_lcp_subparts("https://example.com/"))
    assert result["lcp_rating"] == "needs_improvement"
    assert result["verdict"] == "needs_improvement"


def test_crux_lcp_subparts_lcp_rating_poor():
    """LCP p75=5000ms rates as poor."""
    payload = _crux_lcp_payload(lcp_p75=5000)
    with patch("gsc_mcp.tools.crux.httpx.Client", return_value=_make_crux_client(200, payload)):
        result = json.loads(crux_lcp_subparts("https://example.com/"))
    assert result["lcp_rating"] == "poor"
    assert result["verdict"] == "poor"


def test_crux_lcp_subparts_form_factor_in_payload():
    """PHONE form factor is sent in the POST payload."""
    mock_client = _make_crux_client(200, _crux_lcp_payload())
    with patch("gsc_mcp.tools.crux.httpx.Client", return_value=mock_client):
        crux_lcp_subparts("https://example.com/", form_factor="PHONE")
    _, kwargs = mock_client.post.call_args
    assert kwargs["json"]["formFactor"] == "PHONE"


def test_crux_lcp_subparts_all_form_factors_not_in_payload():
    """ALL_FORM_FACTORS means formFactor is NOT sent."""
    mock_client = _make_crux_client(200, _crux_lcp_payload())
    with patch("gsc_mcp.tools.crux.httpx.Client", return_value=mock_client):
        crux_lcp_subparts("https://example.com/", form_factor="ALL_FORM_FACTORS")
    _, kwargs = mock_client.post.call_args
    assert "formFactor" not in kwargs["json"]


def test_crux_lcp_subparts_meta():
    """_meta block contains correct tool name, url, and form_factor."""
    with patch("gsc_mcp.tools.crux.httpx.Client",
               return_value=_make_crux_client(200, _crux_lcp_payload())):
        result = json.loads(crux_lcp_subparts("https://example.com/", form_factor="DESKTOP"))
    assert result["_meta"]["tool"] == "crux_lcp_subparts"
    assert result["_meta"]["params"]["url"] == "https://example.com/"
    assert result["_meta"]["params"]["form_factor"] == "DESKTOP"


def test_crux_lcp_subparts_metrics_in_request():
    """All 5 LCP metrics (including overall lcp) are requested from the API."""
    mock_client = _make_crux_client(200, _crux_lcp_payload())
    with patch("gsc_mcp.tools.crux.httpx.Client", return_value=mock_client):
        crux_lcp_subparts("https://example.com/")
    _, kwargs = mock_client.post.call_args
    metrics = kwargs["json"]["metrics"]
    assert "largest_contentful_paint" in metrics
    assert "largest_contentful_paint_image_time_to_first_byte" in metrics
    assert "largest_contentful_paint_image_element_render_delay" in metrics


# ===========================================================================
# indexnow_submit
# ===========================================================================

@pytest.fixture(autouse=True)
def mock_validate_url_strict_indexing():
    """Patch validate_url_strict in indexing module so DNS resolution is skipped."""
    with patch("gsc_mcp.tools.indexing.validate_url_strict", side_effect=lambda u: (u, "1.2.3.4")):
        yield


def test_indexnow_submit_ok():
    """All valid URLs and HTTP 200 returns verdict=ok."""
    mock_client = _make_indexnow_client(200)
    with patch("gsc_mcp.tools.indexing.httpx.Client", return_value=mock_client):
        result = json.loads(indexnow_submit(
            site="https://example.com",
            key="abc123xyz",
            urls=["https://example.com/page1", "https://example.com/page2"],
        ))
    assert result["verdict"] == "ok"
    assert result["submitted"] == 2
    assert result["skipped_invalid"] == 0
    assert result["status_code"] == 200


def test_indexnow_submit_202():
    """HTTP 202 Accepted also maps to verdict=ok."""
    mock_client = _make_indexnow_client(202)
    with patch("gsc_mcp.tools.indexing.httpx.Client", return_value=mock_client):
        result = json.loads(indexnow_submit(
            site="https://example.com",
            key="abc123",
            urls=["https://example.com/p"],
        ))
    assert result["verdict"] == "ok"
    assert result["status_code"] == 202


def test_indexnow_submit_partial_skipped():
    """Some invalid URLs skipped + HTTP 200 = partial verdict."""
    def _validate(u):
        if "bad" in u:
            raise URLSafetyError("blocked")
        return u, "1.2.3.4"

    mock_client = _make_indexnow_client(200)
    with patch("gsc_mcp.tools.indexing.validate_url_strict", side_effect=_validate), \
         patch("gsc_mcp.tools.indexing.httpx.Client", return_value=mock_client):
        result = json.loads(indexnow_submit(
            site="https://example.com",
            key="key1",
            urls=["https://example.com/ok", "https://bad.internal/skip"],
        ))
    assert result["verdict"] == "partial"
    assert result["submitted"] == 1
    assert result["skipped_invalid"] == 1


def test_indexnow_submit_all_invalid():
    """All URLs invalid (SSRF blocked) returns error without making HTTP call."""
    def _validate(u):
        raise URLSafetyError("private IP")

    with patch("gsc_mcp.tools.indexing.validate_url_strict", side_effect=_validate):
        result = json.loads(indexnow_submit(
            site="https://example.com",
            key="key1",
            urls=["https://192.168.1.1/page"],
        ))
    assert result["verdict"] == "error"
    assert result["submitted"] == 0
    assert result["skipped_invalid"] == 1
    assert result["status_code"] is None


def test_indexnow_submit_empty_urls():
    """Empty URL list returns error immediately (no HTTP call)."""
    result = json.loads(indexnow_submit(
        site="https://example.com",
        key="key1",
        urls=[],
    ))
    assert result["verdict"] == "error"
    assert result["submitted"] == 0
    assert result["skipped_invalid"] == 0


def test_indexnow_submit_422():
    """HTTP 422 Key Not Found maps to verdict=error."""
    mock_client = _make_indexnow_client(422)
    with patch("gsc_mcp.tools.indexing.httpx.Client", return_value=mock_client):
        result = json.loads(indexnow_submit(
            site="https://example.com",
            key="wrong-key",
            urls=["https://example.com/p"],
        ))
    assert result["verdict"] == "error"
    assert result["status_code"] == 422


def test_indexnow_submit_429():
    """HTTP 429 Rate Limited maps to verdict=error."""
    mock_client = _make_indexnow_client(429)
    with patch("gsc_mcp.tools.indexing.httpx.Client", return_value=mock_client):
        result = json.loads(indexnow_submit(
            site="https://example.com",
            key="key1",
            urls=["https://example.com/p"],
        ))
    assert result["verdict"] == "error"


def test_indexnow_submit_host_extracted():
    """Host is extracted from site URL (no scheme in the POST body host field)."""
    mock_client = _make_indexnow_client(200)
    with patch("gsc_mcp.tools.indexing.httpx.Client", return_value=mock_client):
        indexnow_submit(
            site="https://example.com",
            key="mykey",
            urls=["https://example.com/p"],
        )
    _, kwargs = mock_client.post.call_args
    assert kwargs["json"]["host"] == "example.com"


def test_indexnow_submit_key_location_format():
    """keyLocation is {site}/{key}.txt."""
    mock_client = _make_indexnow_client(200)
    with patch("gsc_mcp.tools.indexing.httpx.Client", return_value=mock_client):
        indexnow_submit(
            site="https://example.com",
            key="abc123",
            urls=["https://example.com/p"],
        )
    _, kwargs = mock_client.post.call_args
    assert kwargs["json"]["keyLocation"] == "https://example.com/abc123.txt"


def test_indexnow_submit_meta():
    """_meta block contains site and url_count."""
    mock_client = _make_indexnow_client(200)
    with patch("gsc_mcp.tools.indexing.httpx.Client", return_value=mock_client):
        result = json.loads(indexnow_submit(
            site="https://example.com",
            key="k",
            urls=["https://example.com/p1", "https://example.com/p2"],
        ))
    assert result["_meta"]["tool"] == "indexnow_submit"
    assert result["_meta"]["params"]["site"] == "https://example.com"
    assert result["_meta"]["params"]["url_count"] == 2


# ===========================================================================
# parasite_risk
# ===========================================================================

def test_parasite_risk_clean():
    """URLs with no parasite patterns return clean verdict and none site_risk."""
    result = json.loads(parasite_risk(
        site="https://example.com",
        urls=["https://example.com/blog/post-1", "https://example.com/about"],
    ))
    assert result["verdict"] == "clean"
    assert result["site_risk"] == "none"
    assert result["high_risk_count"] == 0


def test_parasite_risk_sponsored_path_high():
    """/sponsored/ in path flags as high risk."""
    result = json.loads(parasite_risk(
        site="https://example.com",
        urls=["https://example.com/sponsored/product-review"],
    ))
    assert result["results"][0]["risk"] == "high"
    assert "sponsored" in result["results"][0]["patterns"]
    assert result["site_risk"] == "high"
    assert result["verdict"] == "high_risk"


def test_parasite_risk_affiliate_path_high():
    """/affiliate/ path is high risk."""
    result = json.loads(parasite_risk(
        site="https://example.com",
        urls=["https://example.com/affiliate/top-vpns"],
    ))
    assert result["results"][0]["risk"] == "high"
    assert "affiliate" in result["results"][0]["patterns"]


def test_parasite_risk_brand_studio_high():
    """/brand-studio/ path is high risk."""
    result = json.loads(parasite_risk(
        site="https://example.com",
        urls=["https://example.com/brand-studio/campaign"],
    ))
    assert result["results"][0]["risk"] == "high"
    assert "brand-studio" in result["results"][0]["patterns"]


def test_parasite_risk_advisor_medium():
    """/advisor/ path is medium risk (Forbes Advisor pattern)."""
    result = json.loads(parasite_risk(
        site="https://example.com",
        urls=["https://example.com/advisor/best-savings"],
    ))
    assert result["results"][0]["risk"] == "medium"
    assert "advisor" in result["results"][0]["patterns"]
    assert result["site_risk"] == "medium"
    assert result["verdict"] == "at_risk"


def test_parasite_risk_select_medium():
    """/select/ path is medium risk (WSJ Select pattern)."""
    result = json.loads(parasite_risk(
        site="https://example.com",
        urls=["https://example.com/select/laptops"],
    ))
    assert result["results"][0]["risk"] == "medium"
    assert "select" in result["results"][0]["patterns"]


def test_parasite_risk_underscored_medium():
    """/underscored/ path is medium risk (CNN Underscored pattern)."""
    result = json.loads(parasite_risk(
        site="https://example.com",
        urls=["https://example.com/underscored/tech"],
    ))
    assert result["results"][0]["risk"] == "medium"


def test_parasite_risk_affiliate_query_param_low():
    """?ref= query param alone is low risk."""
    result = json.loads(parasite_risk(
        site="https://example.com",
        urls=["https://example.com/reviews?ref=partner123"],
    ))
    assert result["results"][0]["risk"] == "low"
    assert "affiliate-param" in result["results"][0]["patterns"]
    assert result["verdict"] == "at_risk"


def test_parasite_risk_commercial_section_high():
    """Path matching best-deals or top-picks pattern is high risk."""
    result = json.loads(parasite_risk(
        site="https://example.com",
        urls=["https://example.com/best-deals/electronics"],
    ))
    assert result["results"][0]["risk"] == "high"
    assert "commercial-section" in result["results"][0]["patterns"]


def test_parasite_risk_site_risk_is_max():
    """site_risk is the maximum risk across all URLs."""
    result = json.loads(parasite_risk(
        site="https://example.com",
        urls=[
            "https://example.com/about",
            "https://example.com/advisor/loans",
            "https://example.com/sponsored/review",
        ],
    ))
    assert result["site_risk"] == "high"
    assert result["high_risk_count"] == 1


def test_parasite_risk_empty_urls():
    """Empty URL list returns clean verdict with zero counts."""
    result = json.loads(parasite_risk(site="https://example.com", urls=[]))
    assert result["verdict"] == "clean"
    assert result["urls_analysed"] == 0
    assert result["high_risk_count"] == 0
    assert result["site_risk"] == "none"


def test_parasite_risk_meta():
    """_meta block contains correct tool and params."""
    result = json.loads(parasite_risk(
        site="https://example.com",
        urls=["https://example.com/page"],
    ))
    assert result["_meta"]["tool"] == "parasite_risk"
    assert result["_meta"]["params"]["site"] == "https://example.com"
    assert result["_meta"]["params"]["url_count"] == 1


def test_parasite_risk_multiple_patterns_same_url():
    """A URL can match multiple patterns; all are collected."""
    url = "https://example.com/sponsored/?ref=aff123"
    check = _parasite_check_url(url)
    # sponsored is high, affiliate-param is low — both should appear
    assert "sponsored" in check["patterns"]
    assert "affiliate-param" in check["patterns"]
    # overall risk is high (highest tier wins)
    assert check["risk"] == "high"


def test_parasite_risk_partner_path_high():
    """/partner/ and /partners/ paths are high risk."""
    result_single = json.loads(parasite_risk(
        site="https://example.com",
        urls=["https://example.com/partner/offer"],
    ))
    result_plural = json.loads(parasite_risk(
        site="https://example.com",
        urls=["https://example.com/partners/deals"],
    ))
    assert result_single["results"][0]["risk"] == "high"
    assert result_plural["results"][0]["risk"] == "high"
