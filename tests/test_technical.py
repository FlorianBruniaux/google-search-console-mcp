"""Tests for schema_validate tool (Phase 4, v0.5.0)."""

import json
from unittest.mock import MagicMock, patch

import httpx
import pytest

from gsc_mcp.tools.technical import schema_validate, _JsonLdExtractor


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
{"@type": "LocalBusiness", "name": "Bel-Etage", "@context": "https://schema.org"}
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
