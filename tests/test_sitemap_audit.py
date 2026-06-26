"""Tests for sitemap_audit tool (Phase 3, v0.5.0)."""

import json
from unittest.mock import patch, MagicMock

import httpx
import pytest

from gsc_mcp.tools.sitemaps import sitemap_audit


@pytest.fixture(autouse=True)
def _mock_dns(monkeypatch):
    """Return a public IP for any hostname -- prevents real DNS calls.

    validate_url_strict (called inside _fetch_xml) resolves the hostname before
    opening any socket. Without this fixture the tests make real DNS calls to
    example.com and would fail in offline / CI environments.
    """
    monkeypatch.setattr(
        "gsc_mcp.url_safety.socket.getaddrinfo",
        lambda *args, **kwargs: [(None, None, None, None, ("93.184.216.34", 0))],
    )

SITE = "sc-domain:example.com"
SITEMAP_URL = "https://example.com/sitemap.xml"

# GSC rows fixture — pages already indexed
GSC_ROWS_3_PAGES = [
    {"page": "https://example.com/page1"},
    {"page": "https://example.com/page2"},
    {"page": "https://example.com/page3"},
]
GSC_JSON_3 = json.dumps({"rows": GSC_ROWS_3_PAGES, "site": SITE, "date_range": {}})

URLSET_3 = b"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://example.com/page1</loc></url>
  <url><loc>https://example.com/page2</loc></url>
  <url><loc>https://example.com/page3</loc></url>
</urlset>"""

URLSET_5 = b"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://example.com/page1</loc></url>
  <url><loc>https://example.com/page2</loc></url>
  <url><loc>https://example.com/page3</loc></url>
  <url><loc>https://example.com/page4</loc></url>
  <url><loc>https://example.com/page5</loc></url>
</urlset>"""

URLSET_EMPTY = b"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></urlset>"""

SITEMAP_INDEX = b"""<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <sitemap><loc>https://example.com/sitemap-posts.xml</loc></sitemap>
  <sitemap><loc>https://example.com/sitemap-pages.xml</loc></sitemap>
</sitemapindex>"""


def _mock_http_response(content: bytes, status: int = 200):
    resp = MagicMock()
    resp.status_code = status
    resp.content = content
    resp.raise_for_status = MagicMock()
    return resp


def _make_httpx_client(responses: list):
    """Build a mock httpx.Client that returns responses in sequence for get() calls."""
    client = MagicMock()
    client.__enter__ = MagicMock(return_value=client)
    client.__exit__ = MagicMock(return_value=False)
    client.get.side_effect = responses
    return client


# ---------------------------------------------------------------------------
# Basic cases
# ---------------------------------------------------------------------------

def test_sitemap_audit_empty_urlset():
    """Sitemap with 0 <url> entries returns verdict=empty."""
    http_client = _make_httpx_client([_mock_http_response(URLSET_EMPTY)])
    with patch("gsc_mcp.tools.sitemaps.httpx.Client", return_value=http_client), \
         patch("gsc_mcp.tools.sitemaps.get_search_analytics", return_value=GSC_JSON_3):
        result = json.loads(sitemap_audit(SITE, SITEMAP_URL))
    assert result["verdict"] == "empty"
    assert result["urls_declared"] == 0


def test_sitemap_audit_healthy():
    """3 URLs in sitemap, all 3 in GSC → verdict=healthy."""
    http_client = _make_httpx_client([_mock_http_response(URLSET_3)])
    with patch("gsc_mcp.tools.sitemaps.httpx.Client", return_value=http_client), \
         patch("gsc_mcp.tools.sitemaps.get_search_analytics", return_value=GSC_JSON_3):
        result = json.loads(sitemap_audit(SITE, SITEMAP_URL))
    assert result["verdict"] == "healthy"
    assert result["urls_declared"] == 3
    assert result["urls_in_gsc"] == 3
    assert result["urls_missing_from_gsc"] == 0


def test_sitemap_audit_partial():
    """5 URLs in sitemap, 4 missing from GSC (80% missing > 20% threshold) → verdict=partial."""
    gsc_json = json.dumps({"rows": [{"page": "https://example.com/page1"}], "site": SITE, "date_range": {}})
    http_client = _make_httpx_client([_mock_http_response(URLSET_5)])
    with patch("gsc_mcp.tools.sitemaps.httpx.Client", return_value=http_client), \
         patch("gsc_mcp.tools.sitemaps.get_search_analytics", return_value=gsc_json):
        result = json.loads(sitemap_audit(SITE, SITEMAP_URL))
    assert result["verdict"] == "partial"
    assert result["urls_declared"] == 5
    assert result["urls_missing_from_gsc"] == 4


def test_sitemap_audit_fetch_error():
    """If the sitemap URL is not reachable, verdict=fetch_error."""
    http_client = MagicMock()
    http_client.__enter__ = MagicMock(return_value=http_client)
    http_client.__exit__ = MagicMock(return_value=False)
    http_client.get.side_effect = httpx.ConnectError("connection refused")
    with patch("gsc_mcp.tools.sitemaps.httpx.Client", return_value=http_client), \
         patch("gsc_mcp.tools.sitemaps.get_search_analytics", return_value=GSC_JSON_3):
        result = json.loads(sitemap_audit(SITE, SITEMAP_URL))
    assert result["verdict"] == "fetch_error"
    assert result["urls_declared"] == 0


# ---------------------------------------------------------------------------
# Sitemap index
# ---------------------------------------------------------------------------

def test_sitemap_audit_sitemap_index():
    """Sitemap index recurses into child sitemaps and aggregates URLs."""
    child_sitemap = b"""<?xml version="1.0" encoding="UTF-8"?>
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
      <url><loc>https://example.com/post-a</loc></url>
      <url><loc>https://example.com/post-b</loc></url>
    </urlset>"""

    http_client = _make_httpx_client([
        _mock_http_response(SITEMAP_INDEX),    # index fetch
        _mock_http_response(child_sitemap),    # sitemap-posts.xml
        _mock_http_response(child_sitemap),    # sitemap-pages.xml (same content for test)
    ])
    gsc_json = json.dumps({"rows": [], "site": SITE, "date_range": {}})
    with patch("gsc_mcp.tools.sitemaps.httpx.Client", return_value=http_client), \
         patch("gsc_mcp.tools.sitemaps.get_search_analytics", return_value=gsc_json):
        result = json.loads(sitemap_audit(SITE, SITEMAP_URL))
    assert result["is_index"] is True
    assert result["urls_declared"] == 4


# ---------------------------------------------------------------------------
# Meta
# ---------------------------------------------------------------------------

def test_sitemap_audit_meta():
    http_client = _make_httpx_client([_mock_http_response(URLSET_3)])
    with patch("gsc_mcp.tools.sitemaps.httpx.Client", return_value=http_client), \
         patch("gsc_mcp.tools.sitemaps.get_search_analytics", return_value=GSC_JSON_3):
        result = json.loads(sitemap_audit(SITE, SITEMAP_URL))
    assert result["_meta"]["tool"] == "sitemap_audit"
    assert result["_meta"]["params"]["site"] == SITE
    assert result["_meta"]["params"]["sitemap_url"] == SITEMAP_URL


def test_sitemap_audit_missing_sample_capped_at_20():
    """missing_sample contains at most 20 URLs."""
    urls = b"<?xml version='1.0'?><urlset xmlns='http://www.sitemaps.org/schemas/sitemap/0.9'>" + \
           b"".join(f"<url><loc>https://example.com/p{i}</loc></url>".encode() for i in range(25)) + \
           b"</urlset>"
    gsc_json = json.dumps({"rows": [], "site": SITE, "date_range": {}})
    http_client = _make_httpx_client([_mock_http_response(urls)])
    with patch("gsc_mcp.tools.sitemaps.httpx.Client", return_value=http_client), \
         patch("gsc_mcp.tools.sitemaps.get_search_analytics", return_value=gsc_json):
        result = json.loads(sitemap_audit(SITE, SITEMAP_URL))
    assert len(result["missing_sample"]) == 20
    assert result["urls_missing_from_gsc"] == 25


# ---------------------------------------------------------------------------
# SSRF protection
# ---------------------------------------------------------------------------

def test_sitemap_audit_rejects_child_url_from_different_origin():
    """Sitemap index with one cross-origin child URL: only the same-origin child is fetched."""
    index_with_evil = b"""<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <sitemap><loc>https://evil.internal/steal-creds</loc></sitemap>
  <sitemap><loc>https://example.com/sitemap-safe.xml</loc></sitemap>
</sitemapindex>"""

    safe_child = b"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://example.com/safe-page</loc></url>
</urlset>"""

    # Only two GET calls should happen: index + safe child. The evil.internal child must be skipped.
    http_client = _make_httpx_client([
        _mock_http_response(index_with_evil),
        _mock_http_response(safe_child),
    ])
    gsc_json = json.dumps({"rows": [], "site": SITE, "date_range": {}})
    with patch("gsc_mcp.tools.sitemaps.httpx.Client", return_value=http_client), \
         patch("gsc_mcp.tools.sitemaps.get_search_analytics", return_value=gsc_json):
        result = json.loads(sitemap_audit(SITE, SITEMAP_URL))

    assert http_client.get.call_count == 2
    assert result["urls_declared"] == 1
    assert result["is_index"] is True


# ---------------------------------------------------------------------------
# Malformed XML
# ---------------------------------------------------------------------------

def test_sitemap_audit_malformed_xml_returns_fetch_error():
    """A response with unparseable XML content returns verdict=fetch_error."""
    http_client = _make_httpx_client([_mock_http_response(b"<not valid xml <<<")])
    gsc_json = json.dumps({"rows": [], "site": SITE, "date_range": {}})
    with patch("gsc_mcp.tools.sitemaps.httpx.Client", return_value=http_client), \
         patch("gsc_mcp.tools.sitemaps.get_search_analytics", return_value=gsc_json):
        result = json.loads(sitemap_audit(SITE, SITEMAP_URL))
    assert result["verdict"] == "fetch_error"
    assert result["urls_declared"] == 0
