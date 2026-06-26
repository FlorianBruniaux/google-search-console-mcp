"""Tests for schema_validate, schema_generate, ai_visibility_audit, gbp_deprecation_lint, and pagespeed_audit tools."""

import json
from unittest.mock import MagicMock, patch

import httpx
import pytest

from gsc_mcp.tools.technical import (
    schema_validate,
    schema_generate,
    _JsonLdExtractor,
    ai_visibility_audit,
    gbp_deprecation_lint,
    pagespeed_audit,
)


@pytest.fixture(autouse=True)
def _mock_dns(monkeypatch):
    """Return a public IP for any hostname to prevent real DNS calls in tests."""
    monkeypatch.setattr(
        "gsc_mcp.url_safety.socket.getaddrinfo",
        lambda *args, **kwargs: [(None, None, None, None, ("93.184.216.34", 0))],
    )


def _mock_http_get(html: str, status: int = 200):
    """Build a mock httpx.Client that returns html for get()."""
    resp = MagicMock()
    resp.status_code = status
    resp.text = html
    resp.raise_for_status = MagicMock()

    client = MagicMock()
    client.__enter__ = MagicMock(return_value=client)
    client.__exit__ = MagicMock(return_value=False)
    client.get.return_value = resp
    return client


# ---------------------------------------------------------------------------
# _JsonLdExtractor
# ---------------------------------------------------------------------------

def test_extractor_single_schema():
    html = '<script type="application/ld+json">{"@type":"WebSite","name":"Foo","url":"https://foo.com"}</script>'
    p = _JsonLdExtractor()
    p.feed(html)
    assert len(p.schemas) == 1
    assert p.schemas[0]["@type"] == "WebSite"


def test_extractor_array_in_single_block():
    """JSON-LD block containing an array is expanded to multiple schemas."""
    html = '<script type="application/ld+json">[{"@type":"WebSite"},{"@type":"LocalBusiness","name":"B","@context":"https://schema.org"}]</script>'
    p = _JsonLdExtractor()
    p.feed(html)
    assert len(p.schemas) == 2


def test_extractor_multiple_blocks():
    html = (
        '<script type="application/ld+json">{"@type":"WebSite","name":"A"}</script>'
        '<script type="application/ld+json">{"@type":"LocalBusiness","name":"B","@context":"https://schema.org"}</script>'
    )
    p = _JsonLdExtractor()
    p.feed(html)
    assert len(p.schemas) == 2


def test_extractor_no_jsonld():
    html = "<html><head><title>No schema</title></head><body></body></html>"
    p = _JsonLdExtractor()
    p.feed(html)
    assert p.schemas == []


def test_extractor_invalid_json_is_skipped():
    html = '<script type="application/ld+json">NOT VALID JSON</script>'
    p = _JsonLdExtractor()
    p.feed(html)
    assert p.schemas == []


# ---------------------------------------------------------------------------
# schema_validate
# ---------------------------------------------------------------------------

LOCALBUSINESS_HTML = """<html><head>
<script type="application/ld+json">
{"@type": "LocalBusiness", "name": "Example Business", "@context": "https://schema.org"}
</script></head><body></body></html>"""

ARTICLE_MISSING_FIELDS_HTML = """<html><head>
<script type="application/ld+json">
{"@type": "Article", "headline": "Mon article", "@context": "https://schema.org"}
</script></head><body></body></html>"""

NO_SCHEMA_HTML = "<html><head></head><body><p>No schema here.</p></body></html>"

FAQ_NO_SCHEMA_HTML = "<html><head></head><body><h1>FAQ</h1></body></html>"


def test_schema_validate_localbusiness_valid():
    """LocalBusiness with name + @type → valid=True, verdict=healthy."""
    with patch("httpx.Client", return_value=_mock_http_get(LOCALBUSINESS_HTML)):
        result = json.loads(schema_validate("https://www.example.com/"))
    schemas = result["schemas"]
    assert any(s["type"] == "LocalBusiness" and s["valid"] for s in schemas)
    assert result["verdict"] == "healthy"


def test_schema_validate_article_missing_fields():
    """Article schema missing author and datePublished → valid=False."""
    with patch("httpx.Client", return_value=_mock_http_get(ARTICLE_MISSING_FIELDS_HTML)):
        result = json.loads(schema_validate("https://example.com/blog/test"))
    article = next(s for s in result["schemas"] if s["type"] == "Article")
    assert article["valid"] is False
    assert "author" in article["missing_required_fields"]
    assert "datePublished" in article["missing_required_fields"]
    assert result["verdict"] == "invalid_schemas"


def test_schema_validate_no_schema():
    """HTML with no JSON-LD → schemas_detected=0, verdict=missing_schemas."""
    with patch("httpx.Client", return_value=_mock_http_get(NO_SCHEMA_HTML)):
        result = json.loads(schema_validate("https://example.com/"))
    assert result["schemas_detected"] == 0
    assert result["verdict"] == "missing_schemas"


def test_schema_validate_faq_url_recommends_faqpage():
    """URL matching /faq with no FAQPage schema → FAQPage in recommendations."""
    with patch("httpx.Client", return_value=_mock_http_get(FAQ_NO_SCHEMA_HTML)):
        result = json.loads(schema_validate("https://example.com/faq"))
    assert "FAQPage" in result["recommendations"]


def test_schema_validate_blog_url_recommends_blogposting():
    with patch("httpx.Client", return_value=_mock_http_get(NO_SCHEMA_HTML)):
        result = json.loads(schema_validate("https://example.com/blog/my-post"))
    assert "BlogPosting" in result["recommendations"]


def test_schema_validate_no_recommendations_when_schema_present():
    """If FAQPage is already present, don't recommend it again."""
    html = """<html><head>
    <script type="application/ld+json">
    {"@type": "FAQPage", "mainEntity": [], "@context": "https://schema.org"}
    </script></head></html>"""
    with patch("httpx.Client", return_value=_mock_http_get(html)):
        result = json.loads(schema_validate("https://example.com/faq"))
    assert "FAQPage" not in result["recommendations"]


def test_schema_validate_fetch_error():
    """httpx.HTTPError → verdict=fetch_error."""
    client = MagicMock()
    client.__enter__ = MagicMock(return_value=client)
    client.__exit__ = MagicMock(return_value=False)
    client.get.side_effect = httpx.HTTPError("connection refused")
    with patch("httpx.Client", return_value=client):
        result = json.loads(schema_validate("https://unreachable.example/"))
    assert result["verdict"] == "fetch_error"
    assert "error" in result


def test_schema_validate_array_jsonld():
    """Multiple schemas in one JSON-LD block are all parsed."""
    html = """<html><head>
    <script type="application/ld+json">
    [
      {"@type": "WebSite", "name": "Example", "url": "https://example.com"},
      {"@type": "Organization", "name": "Org", "@context": "https://schema.org"}
    ]
    </script></head></html>"""
    with patch("httpx.Client", return_value=_mock_http_get(html)):
        result = json.loads(schema_validate("https://example.com/"))
    assert result["schemas_detected"] == 2
    types = {s["type"] for s in result["schemas"]}
    assert types == {"WebSite", "Organization"}


def test_schema_validate_meta():
    with patch("httpx.Client", return_value=_mock_http_get(NO_SCHEMA_HTML)):
        result = json.loads(schema_validate("https://example.com/test"))
    assert result["_meta"]["tool"] == "schema_validate"
    assert result["_meta"]["params"]["url"] == "https://example.com/test"


def test_schema_validate_ssrf_private_ip_blocked():
    """Private IP from DNS resolution → fetch_error (DNS rebinding refused message)."""
    with patch(
        "gsc_mcp.url_safety.socket.getaddrinfo",
        return_value=[(None, None, None, None, ("192.168.1.1", 0))],
    ):
        result = json.loads(schema_validate("http://internal.corp/"))
    assert result["verdict"] == "fetch_error"
    assert "192.168.1.1" in result["error"]


def test_schema_validate_ssrf_loopback_blocked():
    """Loopback IP → fetch_error."""
    with patch(
        "gsc_mcp.url_safety.socket.getaddrinfo",
        return_value=[(None, None, None, None, ("127.0.0.1", 0))],
    ):
        result = json.loads(schema_validate("http://localhost/"))
    assert result["verdict"] == "fetch_error"
    assert "Blocked" in result["error"]


def test_schema_validate_ssrf_metadata_ip_blocked():
    """AWS metadata IP 169.254.169.254 → fetch_error."""
    with patch(
        "gsc_mcp.url_safety.socket.getaddrinfo",
        return_value=[(None, None, None, None, ("169.254.169.254", 0))],
    ):
        result = json.loads(schema_validate("http://169.254.169.254/latest/meta-data/"))
    assert result["verdict"] == "fetch_error"
    assert "Blocked" in result["error"]


# ---------------------------------------------------------------------------
# schema_generate
# ---------------------------------------------------------------------------


class TestSchemaGenerateProfile:
    def test_basic(self):
        result = json.loads(schema_generate(
            schema_type="profile",
            name="Alice Dupont",
            profile_url="https://example.com/about",
        ))
        assert result["verdict"] == "generated"
        assert result["schema_type"] == "profile"
        ld = result["json_ld"]
        assert ld["@type"] == "ProfilePage"
        assert ld["mainEntity"]["name"] == "Alice Dupont"
        assert ld["mainEntity"]["url"] == "https://example.com/about"

    def test_optional_fields(self):
        result = json.loads(schema_generate(
            schema_type="profile",
            name="Bob",
            profile_url="https://example.com/bob",
            job_title="Developer",
            works_for="Acme Corp",
            same_as=["https://linkedin.com/in/bob"],
        ))
        ld = result["json_ld"]["mainEntity"]
        assert ld["jobTitle"] == "Developer"
        assert ld["worksFor"]["name"] == "Acme Corp"
        assert "https://linkedin.com/in/bob" in ld["sameAs"]

    def test_missing_required_fields(self):
        result = json.loads(schema_generate(schema_type="profile", name="Alice"))
        assert result["verdict"] == "error"
        assert "profile_url" in result["error"]

    def test_meta(self):
        result = json.loads(schema_generate(
            schema_type="profile",
            name="Test",
            profile_url="https://example.com/",
        ))
        assert result["_meta"]["tool"] == "schema_generate"
        assert result["_meta"]["params"]["schema_type"] == "profile"

    def test_strip_nones(self):
        """None optional fields must not appear in the output."""
        result = json.loads(schema_generate(
            schema_type="profile",
            name="Min",
            profile_url="https://example.com/min",
        ))
        ld = result["json_ld"]["mainEntity"]
        assert "description" not in ld
        assert "sameAs" not in ld
        assert "image" not in ld


class TestSchemaGenerateReservation:
    def test_basic(self):
        result = json.loads(schema_generate(
            schema_type="reservation",
            provider="Le Bistrot",
            start_time="2026-07-15T20:00",
        ))
        assert result["verdict"] == "generated"
        ld = result["json_ld"]
        assert ld["@type"] == "FoodEstablishmentReservation"
        assert ld["provider"]["name"] == "Le Bistrot"

    def test_missing_required(self):
        result = json.loads(schema_generate(schema_type="reservation", provider="Resto"))
        assert result["verdict"] == "error"

    def test_optional_end_time_and_party_size(self):
        result = json.loads(schema_generate(
            schema_type="reservation",
            provider="Bistro",
            start_time="2026-07-15T20:00",
            end_time="2026-07-15T22:00",
            party_size=4,
        ))
        ld = result["json_ld"]
        assert ld["endTime"] == "2026-07-15T22:00"
        assert ld["partySize"] == 4


class TestSchemaGenerateOrderAction:
    def test_basic(self):
        result = json.loads(schema_generate(
            schema_type="order_action",
            merchant="Pizza Palace",
            order_url="https://order.pizzapalace.com/",
        ))
        assert result["verdict"] == "generated"
        ld = result["json_ld"]
        assert ld["@type"] == "OrderAction"
        assert ld["merchant"]["name"] == "Pizza Palace"
        assert ld["target"]["urlTemplate"] == "https://order.pizzapalace.com/"

    def test_missing_required(self):
        result = json.loads(schema_generate(schema_type="order_action", merchant="X"))
        assert result["verdict"] == "error"


class TestSchemaGenerateDiscussion:
    def test_basic(self):
        result = json.loads(schema_generate(
            schema_type="discussion",
            headline="Comment choisir son stack ?",
            author="Marie",
            url="https://forum.example.com/topic/42",
            date_published="2026-01-10",
        ))
        assert result["verdict"] == "generated"
        ld = result["json_ld"]
        assert ld["@type"] == "DiscussionForumPosting"
        assert ld["headline"] == "Comment choisir son stack ?"
        assert ld["author"]["name"] == "Marie"

    def test_missing_required(self):
        result = json.loads(schema_generate(
            schema_type="discussion",
            headline="Missing fields",
        ))
        assert result["verdict"] == "error"

    def test_optional_comment_count(self):
        result = json.loads(schema_generate(
            schema_type="discussion",
            headline="H",
            author="A",
            url="https://example.com/post",
            date_published="2026-01-01",
            comment_count=17,
        ))
        assert result["json_ld"]["commentCount"] == 17


class TestSchemaGenerateUnknownType:
    def test_unknown_type_returns_error(self):
        result = json.loads(schema_generate(schema_type="unknown_type"))
        assert result["verdict"] == "error"
        assert "unknown_type" in result["error"].lower()


def test_schema_validate_fields_present_excludes_at_fields():
    """fields_present should not include @type, @context, @id."""
    html = """<html><head>
    <script type="application/ld+json">
    {"@type": "WebSite", "@context": "https://schema.org", "name": "Example", "url": "https://example.com"}
    </script></head></html>"""
    with patch("httpx.Client", return_value=_mock_http_get(html)):
        result = json.loads(schema_validate("https://example.com/"))
    website = next(s for s in result["schemas"] if s["type"] == "WebSite")
    assert "name" in website["fields_present"]
    assert "url" in website["fields_present"]
    assert "@context" not in website["fields_present"]
    assert "@type" not in website["fields_present"]


def test_schema_validate_faqpage_deprecated_rich_result():
    """FAQPage detected → deprecated_rich_result populated with deprecation notice."""
    html = """<html><head>
    <script type="application/ld+json">
    {"@type": "FAQPage", "mainEntity": [], "@context": "https://schema.org"}
    </script></head></html>"""
    with patch("httpx.Client", return_value=_mock_http_get(html)):
        result = json.loads(schema_validate("https://example.com/faq"))
    faq = next(s for s in result["schemas"] if s["type"] == "FAQPage")
    assert faq["deprecated_rich_result"] is not None
    assert "deprecated" in faq["deprecated_rich_result"].lower()
    assert "May 2026" in faq["deprecated_rich_result"]


def test_schema_validate_non_deprecated_schema_no_deprecation_note():
    """LocalBusiness → deprecated_rich_result is None."""
    with patch("httpx.Client", return_value=_mock_http_get(LOCALBUSINESS_HTML)):
        result = json.loads(schema_validate("https://www.example.com/"))
    lb = next(s for s in result["schemas"] if s["type"] == "LocalBusiness")
    assert lb["deprecated_rich_result"] is None


# ---------------------------------------------------------------------------
# ai_visibility_audit
# ---------------------------------------------------------------------------

def _ai_fetch_side_effect(robots_txt_content=None, robots_raises=None, llms_found=False):
    """Build a safe_fetch_html side_effect for ai_visibility_audit tests."""
    def side_effect(url):
        if "robots.txt" in url:
            if robots_raises is not None:
                raise robots_raises
            return (robots_txt_content or "", 200)
        # llms.txt call
        if llms_found:
            return ("# llms.txt\n", 200)
        raise httpx.HTTPError("404 Not Found")
    return side_effect


def test_ai_visibility_all_allowed():
    """robots.txt allows all AI crawlers → verdict open."""
    robots = "User-agent: *\nAllow: /"
    with patch("gsc_mcp.tools.technical.safe_fetch_html",
               side_effect=_ai_fetch_side_effect(robots_txt_content=robots)):
        result = json.loads(ai_visibility_audit("https://example.com/"))
    assert result["verdict"] == "open"
    assert result["robots_txt_found"] is True
    assert result["allowed_count"] == result["total_crawlers"]


def test_ai_visibility_all_blocked():
    """robots.txt Disallow: / for * → all crawlers blocked, verdict closed."""
    robots = "User-agent: *\nDisallow: /"
    with patch("gsc_mcp.tools.technical.safe_fetch_html",
               side_effect=_ai_fetch_side_effect(robots_txt_content=robots)):
        result = json.loads(ai_visibility_audit("https://example.com/"))
    assert result["verdict"] == "closed"
    assert result["allowed_count"] == 0
    assert result["robots_txt_found"] is True


def test_ai_visibility_partial():
    """GPTBot explicitly blocked, others allowed → verdict partial."""
    robots = "User-agent: GPTBot\nDisallow: /"
    with patch("gsc_mcp.tools.technical.safe_fetch_html",
               side_effect=_ai_fetch_side_effect(robots_txt_content=robots)):
        result = json.loads(ai_visibility_audit("https://example.com/"))
    assert result["verdict"] == "partial"
    gptbot = next(c for c in result["crawlers"] if c["agent"] == "GPTBot")
    assert gptbot["allowed"] is False
    other = next(c for c in result["crawlers"] if c["agent"] == "PerplexityBot")
    assert other["allowed"] is True


def test_ai_visibility_no_robots():
    """robots.txt returns 404 → robots_txt_found=False, verdict open."""
    with patch("gsc_mcp.tools.technical.safe_fetch_html",
               side_effect=_ai_fetch_side_effect(robots_raises=httpx.HTTPError("404"))):
        result = json.loads(ai_visibility_audit("https://example.com/"))
    assert result["verdict"] == "open"
    assert result["robots_txt_found"] is False


def test_ai_visibility_llms_txt_present():
    """llms.txt returns 200 → llms_txt_present=True."""
    robots = "User-agent: *\nAllow: /"
    with patch("gsc_mcp.tools.technical.safe_fetch_html",
               side_effect=_ai_fetch_side_effect(robots_txt_content=robots, llms_found=True)):
        result = json.loads(ai_visibility_audit("https://example.com/"))
    assert result["llms_txt_present"] is True


def test_ai_visibility_ssrf_blocked():
    """validate_url_strict raises URLSafetyError → verdict fetch_error."""
    from gsc_mcp.url_safety import URLSafetyError
    with patch("gsc_mcp.tools.technical.validate_url_strict",
               side_effect=URLSafetyError("Blocked")):
        result = json.loads(ai_visibility_audit("http://internal.corp/"))
    assert result["verdict"] == "fetch_error"
    assert "error" in result


def test_ai_visibility_meta():
    """_meta block is present with correct tool name."""
    robots = "User-agent: *\nAllow: /"
    with patch("gsc_mcp.tools.technical.safe_fetch_html",
               side_effect=_ai_fetch_side_effect(robots_txt_content=robots)):
        result = json.loads(ai_visibility_audit("https://example.com/"))
    assert result["_meta"]["tool"] == "ai_visibility_audit"
    assert result["_meta"]["params"]["url"] == "https://example.com/"


# ---------------------------------------------------------------------------
# gbp_deprecation_lint
# ---------------------------------------------------------------------------

def _mock_gbp_fetch(html_content: str, raises=None):
    """Build a safe_fetch_html side_effect for gbp_deprecation_lint tests."""
    def side_effect(url):
        if raises is not None:
            raise raises
        return (html_content, 200)
    return side_effect


def test_gbp_lint_clean():
    """Page with no GBP patterns → verdict clean."""
    html = "<html><body><p>No deprecated GBP features here.</p></body></html>"
    with patch("gsc_mcp.tools.technical.safe_fetch_html",
               side_effect=_mock_gbp_fetch(html)):
        result = json.loads(gbp_deprecation_lint("https://example.com/"))
    assert result["verdict"] == "clean"
    assert result["issues_count"] == 0
    assert result["issues"] == []


def test_gbp_lint_business_site():
    """HTML contains .business.site link → deprecated_found."""
    html = '<html><body><a href="https://mybiz.business.site">Order</a></body></html>'
    with patch("gsc_mcp.tools.technical.safe_fetch_html",
               side_effect=_mock_gbp_fetch(html)):
        result = json.loads(gbp_deprecation_lint("https://example.com/"))
    assert result["verdict"] == "deprecated_found"
    assert result["issues_count"] >= 1
    descriptions = [i["description"] for i in result["issues"]]
    assert any("business.site" in d for d in descriptions)


def test_gbp_lint_reserve_with_google():
    """reservewithgoogle.com in HTML → deprecated_found."""
    html = '<script src="https://www.reservewithgoogle.com/embed.js"></script>'
    with patch("gsc_mcp.tools.technical.safe_fetch_html",
               side_effect=_mock_gbp_fetch(html)):
        result = json.loads(gbp_deprecation_lint("https://example.com/"))
    assert result["verdict"] == "deprecated_found"
    descriptions = [i["description"] for i in result["issues"]]
    assert any("Reserve with Google" in d for d in descriptions)


def test_gbp_lint_multiple_issues():
    """Two GBP patterns present → issues_count == 2."""
    html = (
        '<a href="https://mybiz.business.site">link</a>'
        '<script src="https://www.reservewithgoogle.com/e.js"></script>'
    )
    with patch("gsc_mcp.tools.technical.safe_fetch_html",
               side_effect=_mock_gbp_fetch(html)):
        result = json.loads(gbp_deprecation_lint("https://example.com/"))
    assert result["verdict"] == "deprecated_found"
    assert result["issues_count"] == 2


def test_gbp_lint_ssrf_blocked():
    """validate_url_strict raises URLSafetyError → verdict fetch_error."""
    from gsc_mcp.url_safety import URLSafetyError
    with patch("gsc_mcp.tools.technical.validate_url_strict",
               side_effect=URLSafetyError("Blocked")):
        result = json.loads(gbp_deprecation_lint("http://internal.corp/"))
    assert result["verdict"] == "fetch_error"


def test_gbp_lint_fetch_error():
    """safe_fetch_html raises httpx.HTTPError → verdict fetch_error."""
    with patch("gsc_mcp.tools.technical.safe_fetch_html",
               side_effect=_mock_gbp_fetch("", raises=httpx.HTTPError("500"))):
        result = json.loads(gbp_deprecation_lint("https://example.com/"))
    assert result["verdict"] == "fetch_error"
    assert "error" in result


def test_gbp_lint_meta():
    """_meta block is present with correct tool name."""
    html = "<html><body></body></html>"
    with patch("gsc_mcp.tools.technical.safe_fetch_html",
               side_effect=_mock_gbp_fetch(html)):
        result = json.loads(gbp_deprecation_lint("https://example.com/"))
    assert result["_meta"]["tool"] == "gbp_deprecation_lint"
    assert result["_meta"]["params"]["url"] == "https://example.com/"


# ---------------------------------------------------------------------------
# pagespeed_audit
# ---------------------------------------------------------------------------

def _mock_psi_client(score: float, audits: dict | None = None):
    """Build a mock httpx.Client for pagespeed_audit tests."""
    response_data = {
        "lighthouseResult": {
            "categories": {"performance": {"score": score}},
            "audits": audits or {},
        }
    }
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = response_data
    resp.raise_for_status = MagicMock()

    client = MagicMock()
    client.__enter__ = MagicMock(return_value=client)
    client.__exit__ = MagicMock(return_value=False)
    client.get.return_value = resp
    return client


def test_pagespeed_audit_missing_key(monkeypatch):
    """No GOOGLE_API_KEY env var → verdict missing_key."""
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    result = json.loads(pagespeed_audit("https://example.com/"))
    assert result["verdict"] == "missing_key"
    assert "GOOGLE_API_KEY" in result["error"]


def test_pagespeed_audit_good_score(monkeypatch):
    """Score 0.95 → verdict good, performance_score 95."""
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    with patch("gsc_mcp.tools.technical.httpx.Client", return_value=_mock_psi_client(0.95)):
        result = json.loads(pagespeed_audit("https://example.com/"))
    assert result["verdict"] == "good"
    assert result["performance_score"] == 95


def test_pagespeed_audit_needs_improvement(monkeypatch):
    """Score 0.72 → verdict needs_improvement."""
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    with patch("gsc_mcp.tools.technical.httpx.Client", return_value=_mock_psi_client(0.72)):
        result = json.loads(pagespeed_audit("https://example.com/"))
    assert result["verdict"] == "needs_improvement"
    assert result["performance_score"] == 72


def test_pagespeed_audit_poor(monkeypatch):
    """Score 0.38 → verdict poor."""
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    with patch("gsc_mcp.tools.technical.httpx.Client", return_value=_mock_psi_client(0.38)):
        result = json.loads(pagespeed_audit("https://example.com/"))
    assert result["verdict"] == "poor"
    assert result["performance_score"] == 38


def test_pagespeed_audit_fetch_error(monkeypatch):
    """httpx.HTTPError during PSI call → verdict fetch_error."""
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    client = MagicMock()
    client.__enter__ = MagicMock(return_value=client)
    client.__exit__ = MagicMock(return_value=False)
    client.get.side_effect = httpx.HTTPError("connection error")
    with patch("gsc_mcp.tools.technical.httpx.Client", return_value=client):
        result = json.loads(pagespeed_audit("https://example.com/"))
    assert result["verdict"] == "fetch_error"
    assert "error" in result


def test_pagespeed_audit_ssrf_blocked(monkeypatch):
    """validate_url_strict raises → verdict fetch_error."""
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    from gsc_mcp.url_safety import URLSafetyError
    with patch("gsc_mcp.tools.technical.validate_url_strict",
               side_effect=URLSafetyError("Blocked IP")):
        result = json.loads(pagespeed_audit("http://169.254.169.254/"))
    assert result["verdict"] == "fetch_error"


def test_pagespeed_audit_opportunities(monkeypatch):
    """Opportunities with score < 0.9 and type=opportunity are returned in top_opportunities."""
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    audits = {
        "render-blocking-resources": {
            "title": "Eliminate render-blocking resources",
            "description": "Resources are blocking the first paint of your page.",
            "score": 0.3,
            "details": {"type": "opportunity"},
        },
        "unused-css-rules": {
            "title": "Reduce unused CSS",
            "description": "Remove dead CSS.",
            "score": 0.5,
            "details": {"type": "opportunity"},
        },
    }
    with patch("gsc_mcp.tools.technical.httpx.Client",
               return_value=_mock_psi_client(0.72, audits=audits)):
        result = json.loads(pagespeed_audit("https://example.com/"))
    assert len(result["top_opportunities"]) == 2
    ids = [o["id"] for o in result["top_opportunities"]]
    assert "render-blocking-resources" in ids
    assert "unused-css-rules" in ids


def test_pagespeed_audit_meta(monkeypatch):
    """_meta block is present with correct tool and params."""
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    with patch("gsc_mcp.tools.technical.httpx.Client", return_value=_mock_psi_client(0.9)):
        result = json.loads(pagespeed_audit("https://example.com/", strategy="desktop"))
    assert result["_meta"]["tool"] == "pagespeed_audit"
    assert result["_meta"]["params"]["strategy"] == "desktop"
