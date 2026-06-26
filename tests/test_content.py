"""Tests for content quality, hreflang audit, and page technical audit tools."""

import json
from unittest.mock import MagicMock, patch

import httpx
import pytest

from gsc_mcp.tools.content import (
    content_quality,
    hreflang_audit,
    page_technical_audit,
)
from gsc_mcp.url_safety import URLSafetyError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_HEALTHY_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <title>Example Domain: Clear and Descriptive Page Title</title>
  <meta name="description" content="This is a well-crafted meta description for the page, with enough characters.">
  <link rel="canonical" href="https://example.com/">
  <meta name="viewport" content="width=device-width, initial-scale=1">
</head>
<body>
  <h1>Example heading</h1>
  <p>Content goes here with real information. The Paris Agreement was signed in 2015 by 196 parties.
  Natural language processing and machine learning techniques are applied here.
  Statistical analysis reveals patterns in large datasets spanning 10 years of research.
  John Smith at Google presented findings in San Francisco during the 2024 conference.
  Over 500 researchers contributed to the study involving 12 countries and 3 continents.</p>
</body>
</html>"""

_NOINDEX_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <title>Draft Page</title>
  <meta name="robots" content="noindex, nofollow">
  <meta name="description" content="This is a draft page not meant for search engines.">
  <link rel="canonical" href="https://example.com/draft">
  <meta name="viewport" content="width=device-width, initial-scale=1">
</head>
<body><p>Draft content.</p></body>
</html>"""

_HREFLANG_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <title>Multilingual Page</title>
  <link rel="alternate" hreflang="en" href="https://example.com/en/">
  <link rel="alternate" hreflang="fr" href="https://example.com/fr/">
  <link rel="alternate" hreflang="x-default" href="https://example.com/">
</head>
<body><p>Content</p></body>
</html>"""

_HREFLANG_NO_SELF_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <title>Page</title>
  <link rel="alternate" hreflang="en" href="https://example.com/en/">
  <link rel="alternate" hreflang="fr" href="https://example.com/fr/">
  <link rel="alternate" hreflang="x-default" href="https://example.com/">
</head>
<body><p>Content</p></body>
</html>"""

_HREFLANG_BAD_CODE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <title>Page</title>
  <link rel="alternate" hreflang="jp" href="https://example.com/jp/">
  <link rel="alternate" hreflang="x-default" href="https://example.com/">
</head>
<body><p>Content</p></body>
</html>"""

_FILLER_HTML = """<!DOCTYPE html>
<html><head><title>Filler</title></head>
<body>
<p>First and foremost, when it comes to writing, needless to say that at the end of the day,
it's important to note that without further ado, in the realm of content, last but not least,
we need to address this topic. First and foremost again, when it comes to optimization,
at the end of the day we realize that it goes without saying what matters most.</p>
</body></html>"""

_ROBOTS_ALLOW = "User-agent: *\nAllow: /\n"
_ROBOTS_BLOCK = "User-agent: Googlebot\nDisallow: /\n"


def _make_http_response(status_code, text, headers=None):
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.text = text
    mock_resp.headers = headers or {}
    return mock_resp


def _patch_page_fetch(html, status_code=200, headers=None, robots_text=_ROBOTS_ALLOW):
    """Context manager stack for page_technical_audit tests."""
    from contextlib import contextmanager

    @contextmanager
    def _ctx():
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = _make_http_response(status_code, html, headers)

        with patch("gsc_mcp.tools.content.validate_url_strict"), \
             patch("gsc_mcp.tools.content.httpx.Client", return_value=mock_client), \
             patch("gsc_mcp.tools.content.safe_fetch_html", return_value=(robots_text, 200)):
            yield mock_client

    return _ctx()


# ---------------------------------------------------------------------------
# content_quality
# ---------------------------------------------------------------------------

class TestContentQuality:
    def test_good_quality_text(self):
        long_text = ("The Paris Agreement was signed in 2015. " * 30 +
                     "John Smith researched 500 datasets across 12 countries. " * 20)
        html = f"<html><body><p>{long_text}</p></body></html>"
        with patch("gsc_mcp.tools.content.safe_fetch_html", return_value=(html, 200)):
            result = json.loads(content_quality("https://example.com/"))
        assert result["verdict"] in ("good", "needs_work")
        assert result["word_count"] > 100

    def test_thin_content_flag(self):
        html = "<html><body><p>Very short page.</p></body></html>"
        with patch("gsc_mcp.tools.content.safe_fetch_html", return_value=(html, 200)):
            result = json.loads(content_quality("https://example.com/"))
        assert result["verdict"] == "thin_content"
        assert "thin-content" in result["flags"]

    def test_filler_phrases_detected(self):
        with patch("gsc_mcp.tools.content.safe_fetch_html", return_value=(_FILLER_HTML, 200)):
            result = json.loads(content_quality("https://example.com/"))
        assert result["filler_score"] > 0
        assert len(result["filler_hits"]) > 0
        assert "first and foremost" in result["filler_hits"]

    def test_information_density_computed(self):
        html = "<html><body><p>" + ("The Paris Agreement was signed in 2015 by 196 parties. " * 50) + "</p></body></html>"
        with patch("gsc_mcp.tools.content.safe_fetch_html", return_value=(html, 200)):
            result = json.loads(content_quality("https://example.com/"))
        assert result["information_density"] > 0

    def test_fetch_error_returns_error_verdict(self):
        with patch("gsc_mcp.tools.content.safe_fetch_html",
                   side_effect=httpx.HTTPError("connection refused")):
            result = json.loads(content_quality("https://example.com/"))
        assert result["verdict"] == "fetch_error"
        assert "error" in result

    def test_ssrf_blocked_returns_error_verdict(self):
        with patch("gsc_mcp.tools.content.safe_fetch_html",
                   side_effect=URLSafetyError("SSRF blocked")):
            result = json.loads(content_quality("https://192.168.0.1/"))
        assert result["verdict"] == "fetch_error"

    def test_meta_block_present(self):
        html = "<html><body><p>" + ("Real content with data. " * 100) + "</p></body></html>"
        with patch("gsc_mcp.tools.content.safe_fetch_html", return_value=(html, 200)):
            result = json.loads(content_quality("https://example.com/"))
        assert "_meta" in result
        assert result["_meta"]["tool"] == "content_quality"

    def test_strips_script_tags_from_text(self):
        html = """<html><body>
        <script>var x = 'filler filler filler';</script>
        <p>The Paris Agreement covered 196 nations and 2015 conference proceedings.</p>
        </body></html>"""
        with patch("gsc_mcp.tools.content.safe_fetch_html", return_value=(html, 200)):
            result = json.loads(content_quality("https://example.com/"))
        assert result["word_count"] < 20

    def test_unique_tokens_counted(self):
        html = "<html><body><p>" + ("word " * 50 + "unique terms Paris 2015 ") + "</p></body></html>"
        with patch("gsc_mcp.tools.content.safe_fetch_html", return_value=(html, 200)):
            result = json.loads(content_quality("https://example.com/"))
        assert result["unique_tokens"] < result["word_count"]


# ---------------------------------------------------------------------------
# hreflang_audit
# ---------------------------------------------------------------------------

class TestHreflangAudit:
    def test_no_hreflang_tags(self):
        html = "<html><head><title>No hreflang</title></head><body><p>Content</p></body></html>"
        with patch("gsc_mcp.tools.content.safe_fetch_html", return_value=(html, 200)):
            result = json.loads(hreflang_audit("https://example.com/"))
        assert result["verdict"] == "no_hreflang"
        assert result["tags"] == []

    def test_valid_hreflang_implementation(self):
        with patch("gsc_mcp.tools.content.safe_fetch_html", return_value=(_HREFLANG_HTML, 200)):
            result = json.loads(hreflang_audit("https://example.com/"))
        assert result["verdict"] in ("valid", "issues_found")
        assert result["has_x_default"] is True
        assert result["tags_count"] == 3

    def test_missing_x_default_reported(self):
        html = """<html><head>
          <link rel="alternate" hreflang="en" href="https://example.com/en/">
          <link rel="alternate" hreflang="fr" href="https://example.com/fr/">
        </head><body></body></html>"""
        with patch("gsc_mcp.tools.content.safe_fetch_html", return_value=(html, 200)):
            result = json.loads(hreflang_audit("https://example.com/"))
        assert result["has_x_default"] is False
        assert result["verdict"] == "issues_found"
        x_default_issues = [i for i in result["issues"] if "x-default" in i["message"].lower()]
        assert len(x_default_issues) > 0

    def test_invalid_lang_code_jp_flagged(self):
        with patch("gsc_mcp.tools.content.safe_fetch_html", return_value=(_HREFLANG_BAD_CODE_HTML, 200)):
            result = json.loads(hreflang_audit("https://example.com/jp/"))
        assert result["verdict"] == "issues_found"
        msg_texts = [i["message"] for i in result["issues"]]
        assert any("jp" in m and "ja" in m for m in msg_texts)

    def test_three_letter_lang_code_flagged(self):
        html = """<html><head>
          <link rel="alternate" hreflang="eng" href="https://example.com/en/">
          <link rel="alternate" hreflang="x-default" href="https://example.com/">
        </head><body></body></html>"""
        with patch("gsc_mcp.tools.content.safe_fetch_html", return_value=(html, 200)):
            result = json.loads(hreflang_audit("https://example.com/"))
        assert result["verdict"] == "issues_found"
        assert any("eng" in i["message"] for i in result["issues"])

    def test_uk_region_code_flagged(self):
        html = """<html><head>
          <link rel="alternate" hreflang="en-UK" href="https://example.com/en/">
          <link rel="alternate" hreflang="x-default" href="https://example.com/">
        </head><body></body></html>"""
        with patch("gsc_mcp.tools.content.safe_fetch_html", return_value=(html, 200)):
            result = json.loads(hreflang_audit("https://example.com/"))
        issues = [i for i in result["issues"] if "UK" in i["message"] and "GB" in i["message"]]
        assert len(issues) > 0

    def test_mixed_protocols_flagged(self):
        html = """<html><head>
          <link rel="alternate" hreflang="en" href="https://example.com/en/">
          <link rel="alternate" hreflang="fr" href="http://example.com/fr/">
          <link rel="alternate" hreflang="x-default" href="https://example.com/">
        </head><body></body></html>"""
        with patch("gsc_mcp.tools.content.safe_fetch_html", return_value=(html, 200)):
            result = json.loads(hreflang_audit("https://example.com/"))
        proto_issues = [i for i in result["issues"] if "HTTP" in i["message"] or "https" in i["message"].lower()]
        assert len(proto_issues) > 0

    def test_fetch_error_returns_error_verdict(self):
        with patch("gsc_mcp.tools.content.safe_fetch_html",
                   side_effect=httpx.HTTPError("timeout")):
            result = json.loads(hreflang_audit("https://example.com/"))
        assert result["verdict"] == "fetch_error"

    def test_meta_block_present(self):
        with patch("gsc_mcp.tools.content.safe_fetch_html", return_value=(_HREFLANG_HTML, 200)):
            result = json.loads(hreflang_audit("https://example.com/"))
        assert "_meta" in result
        assert result["_meta"]["tool"] == "hreflang_audit"

    def test_x_default_is_always_valid(self):
        html = """<html><head>
          <link rel="alternate" hreflang="en" href="https://example.com/en/">
          <link rel="alternate" hreflang="x-default" href="https://example.com/">
        </head><body></body></html>"""
        with patch("gsc_mcp.tools.content.safe_fetch_html", return_value=(html, 200)):
            result = json.loads(hreflang_audit("https://example.com/"))
        x_default_lang_issues = [
            i for i in result["issues"]
            if "x-default" in i.get("message", "").lower() and "code" in i.get("message", "").lower()
        ]
        assert len(x_default_lang_issues) == 0


# ---------------------------------------------------------------------------
# page_technical_audit
# ---------------------------------------------------------------------------

class TestPageTechnicalAudit:
    def test_healthy_page_verdict(self):
        headers = {
            "x-frame-options": "SAMEORIGIN",
            "x-content-type-options": "nosniff",
            "referrer-policy": "strict-origin-when-cross-origin",
        }
        with _patch_page_fetch(_HEALTHY_HTML, headers=headers):
            result = json.loads(page_technical_audit("https://example.com/"))
        assert result["verdict"] == "healthy"
        assert result["critical_count"] == 0

    def test_noindex_is_critical(self):
        with _patch_page_fetch(_NOINDEX_HTML, headers={
            "x-frame-options": "SAMEORIGIN",
            "x-content-type-options": "nosniff",
            "referrer-policy": "strict-origin",
        }):
            result = json.loads(page_technical_audit("https://example.com/draft"))
        assert result["verdict"] == "issues_found"
        assert result["critical_count"] >= 1
        critical = [i for i in result["issues"] if i.get("severity") == "critical"]
        assert any("noindex" in i["message"].lower() for i in critical)

    def test_missing_title_is_high_severity(self):
        html = """<html lang="en"><head>
          <meta name="description" content="No title page with enough description here.">
          <link rel="canonical" href="https://example.com/">
          <meta name="viewport" content="width=device-width">
        </head><body><p>Content</p></body></html>"""
        with _patch_page_fetch(html):
            result = json.loads(page_technical_audit("https://example.com/"))
        title_issues = [i for i in result["issues"] if i.get("check") == "title"]
        assert len(title_issues) > 0
        assert any(i["severity"] == "high" for i in title_issues)

    def test_redirect_detected(self):
        with _patch_page_fetch(
            "", status_code=301,
            headers={"location": "https://example.com/new/"},
        ):
            result = json.loads(page_technical_audit("https://example.com/old/"))
        assert result["findings"]["redirected"] is True
        assert result["findings"]["status_code"] == 301
        redirect_issues = [i for i in result["issues"] if i.get("check") == "redirect"]
        assert len(redirect_issues) > 0

    def test_ssrf_blocked_returns_fetch_error(self):
        with patch("gsc_mcp.tools.content.validate_url_strict",
                   side_effect=URLSafetyError("SSRF blocked")):
            result = json.loads(page_technical_audit("https://192.168.0.1/"))
        assert result["verdict"] == "fetch_error"

    def test_http_error_returns_fetch_error(self):
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.side_effect = httpx.HTTPError("connection refused")
        with patch("gsc_mcp.tools.content.validate_url_strict"), \
             patch("gsc_mcp.tools.content.httpx.Client", return_value=mock_client):
            result = json.loads(page_technical_audit("https://example.com/"))
        assert result["verdict"] == "fetch_error"

    def test_robots_blocks_googlebot(self):
        with _patch_page_fetch(_HEALTHY_HTML, robots_text=_ROBOTS_BLOCK):
            result = json.loads(page_technical_audit("https://example.com/"))
        assert result["findings"]["robots_txt_blocks_googlebot"] is True
        critical = [i for i in result["issues"] if i.get("severity") == "critical"]
        assert any("robots" in i["check"] for i in critical)

    def test_security_headers_present(self):
        headers = {
            "x-frame-options": "SAMEORIGIN",
            "x-content-type-options": "nosniff",
            "referrer-policy": "strict-origin-when-cross-origin",
        }
        with _patch_page_fetch(_HEALTHY_HTML, headers=headers):
            result = json.loads(page_technical_audit("https://example.com/"))
        sec = result["findings"]["security_headers"]
        assert sec["x-frame-options"] == "SAMEORIGIN"
        assert sec["x-content-type-options"] == "nosniff"
        assert sec["referrer-policy"] == "strict-origin-when-cross-origin"

    def test_missing_security_headers_flagged(self):
        with _patch_page_fetch(_HEALTHY_HTML, headers={}):
            result = json.loads(page_technical_audit("https://example.com/"))
        sec_issues = [i for i in result["issues"] if i.get("check") == "security_headers"]
        assert len(sec_issues) == 3

    def test_title_length_reported(self):
        with _patch_page_fetch(_HEALTHY_HTML):
            result = json.loads(page_technical_audit("https://example.com/"))
        expected = "Example Domain: Clear and Descriptive Page Title"
        assert result["findings"]["title"] == expected
        assert result["findings"]["title_length"] == len(expected)

    def test_canonical_mismatch_is_high_severity(self):
        html = """<html lang="en"><head>
          <title>Mismatch canonical</title>
          <meta name="description" content="A description long enough to be valid here.">
          <link rel="canonical" href="https://example.com/other/">
          <meta name="viewport" content="width=device-width">
        </head><body><p>Content</p></body></html>"""
        with _patch_page_fetch(html):
            result = json.loads(page_technical_audit("https://example.com/"))
        canonical_issues = [i for i in result["issues"] if i.get("check") == "canonical"]
        assert any(i["severity"] == "high" for i in canonical_issues)

    def test_missing_canonical_is_medium_severity(self):
        html = """<html lang="en"><head>
          <title>No canonical</title>
          <meta name="description" content="A description long enough to be valid here.">
          <meta name="viewport" content="width=device-width">
        </head><body><p>Content</p></body></html>"""
        with _patch_page_fetch(html):
            result = json.loads(page_technical_audit("https://example.com/"))
        canonical_issues = [i for i in result["issues"] if i.get("check") == "canonical"]
        assert any(i["severity"] == "medium" for i in canonical_issues)

    def test_meta_block_present(self):
        with _patch_page_fetch(_HEALTHY_HTML):
            result = json.loads(page_technical_audit("https://example.com/"))
        assert "_meta" in result
        assert result["_meta"]["tool"] == "page_technical_audit"

    def test_title_too_long_is_low_severity(self):
        long_title = "A" * 70
        html = f"""<html lang="en"><head>
          <title>{long_title}</title>
          <meta name="description" content="Description with enough characters to be valid here.">
          <link rel="canonical" href="https://example.com/">
          <meta name="viewport" content="width=device-width">
        </head><body><p>Content</p></body></html>"""
        with _patch_page_fetch(html):
            result = json.loads(page_technical_audit("https://example.com/"))
        title_issues = [i for i in result["issues"] if i.get("check") == "title"]
        assert any(i["severity"] == "low" for i in title_issues)

    def test_http_404_returns_fetch_error(self):
        with _patch_page_fetch("Not found", status_code=404):
            result = json.loads(page_technical_audit("https://example.com/missing/"))
        assert result["verdict"] == "fetch_error"

    def test_html_lang_missing_flagged(self):
        html = """<html><head>
          <title>No lang</title>
          <meta name="description" content="Description with enough characters to be valid here.">
          <link rel="canonical" href="https://example.com/">
          <meta name="viewport" content="width=device-width">
        </head><body><p>Content</p></body></html>"""
        with _patch_page_fetch(html):
            result = json.loads(page_technical_audit("https://example.com/"))
        lang_issues = [i for i in result["issues"] if i.get("check") == "html_lang"]
        assert len(lang_issues) > 0
