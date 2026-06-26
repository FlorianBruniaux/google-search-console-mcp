"""Tests for gsc_mcp.tools.drift module.

All tests are fully mocked -- no real HTTP requests, no real CrUX API calls.
SQLite uses tmp_path for isolation.
"""
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import httpx

from gsc_mcp.tools.drift import (
    _normalize_url,
    _url_hash,
    _hash_content,
    _parse_html,
    _DriftPageParser,
    drift_baseline,
    drift_compare,
    drift_history,
)
from gsc_mcp.url_safety import URLSafetyError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SIMPLE_HTML = """
<!DOCTYPE html>
<html>
<head>
  <title>Test Page</title>
  <meta name="description" content="A test page description.">
  <meta name="robots" content="index, follow">
  <link rel="canonical" href="https://example.com/test/">
  <meta property="og:title" content="Test OG Title">
  <meta property="og:description" content="OG Desc">
  <script type="application/ld+json">
  {"@context": "https://schema.org", "@type": "WebPage", "name": "Test Page"}
  </script>
</head>
<body>
  <h1>Main Heading</h1>
  <h2>Section One</h2>
  <h2>Section Two</h2>
  <h3>Sub Section</h3>
</body>
</html>
"""

NOINDEX_HTML = """
<html>
<head>
  <title>Test</title>
  <meta name="robots" content="noindex, nofollow">
</head>
<body><h1>Heading</h1></body>
</html>
"""

NO_H1_HTML = """
<html>
<head><title>No H1 Page</title></head>
<body><h2>Only H2</h2></body>
</html>
"""


def _make_mock_response(html: str, status_code: int = 200):
    """Create a mock httpx response."""
    mock = MagicMock()
    mock.text = html
    mock.status_code = status_code
    mock.raise_for_status = MagicMock()
    return mock


def _mock_fetch(html: str, status_code: int = 200):
    """Context manager patcher for safe_fetch_html."""
    return patch(
        "gsc_mcp.tools.drift.safe_fetch_html",
        return_value=(html, status_code),
    )


# ---------------------------------------------------------------------------
# URL normalization
# ---------------------------------------------------------------------------

class TestNormalizeUrl:
    def test_strips_trailing_slash(self):
        assert _normalize_url("https://example.com/page/") == "https://example.com/page"

    def test_preserves_root(self):
        assert _normalize_url("https://example.com/") == "https://example.com/"

    def test_strips_utm(self):
        url = "https://example.com/page?utm_source=test&utm_medium=cpc"
        assert "utm_source" not in _normalize_url(url)

    def test_sorts_query_params(self):
        url1 = _normalize_url("https://example.com/?b=2&a=1")
        url2 = _normalize_url("https://example.com/?a=1&b=2")
        assert url1 == url2

    def test_lowercases_scheme_and_host(self):
        result = _normalize_url("HTTPS://EXAMPLE.COM/path")
        assert result.startswith("https://example.com")

    def test_strips_default_port_443(self):
        assert "443" not in _normalize_url("https://example.com:443/page")

    def test_strips_default_port_80(self):
        assert "80" not in _normalize_url("http://example.com:80/page")


class TestUrlHash:
    def test_consistent(self):
        assert _url_hash("https://example.com/page") == _url_hash("https://example.com/page")

    def test_utm_stripped_same_hash(self):
        h1 = _url_hash("https://example.com/page?utm_source=x")
        h2 = _url_hash("https://example.com/page")
        assert h1 == h2

    def test_different_urls_different_hash(self):
        assert _url_hash("https://example.com/a") != _url_hash("https://example.com/b")


# ---------------------------------------------------------------------------
# HTML parser
# ---------------------------------------------------------------------------

class TestDriftPageParser:
    def test_extracts_title(self):
        result = _parse_html(SIMPLE_HTML)
        assert result["title"] == "Test Page"

    def test_extracts_meta_description(self):
        result = _parse_html(SIMPLE_HTML)
        assert "test page description" in result["meta_description"].lower()

    def test_extracts_meta_robots(self):
        result = _parse_html(SIMPLE_HTML)
        assert result["meta_robots"] == "index, follow"

    def test_extracts_canonical(self):
        result = _parse_html(SIMPLE_HTML)
        assert result["canonical"] == "https://example.com/test/"

    def test_extracts_h1(self):
        result = _parse_html(SIMPLE_HTML)
        assert result["h1"] == ["Main Heading"]

    def test_extracts_h2(self):
        result = _parse_html(SIMPLE_HTML)
        assert len(result["h2"]) == 2

    def test_extracts_h3(self):
        result = _parse_html(SIMPLE_HTML)
        assert len(result["h3"]) == 1

    def test_extracts_schema(self):
        result = _parse_html(SIMPLE_HTML)
        assert len(result["schema"]) == 1
        assert result["schema"][0]["@type"] == "WebPage"

    def test_extracts_og(self):
        result = _parse_html(SIMPLE_HTML)
        assert result["open_graph"]["title"] == "Test OG Title"

    def test_noindex_robots(self):
        result = _parse_html(NOINDEX_HTML)
        assert "noindex" in result["meta_robots"].lower()

    def test_no_h1(self):
        result = _parse_html(NO_H1_HTML)
        assert result["h1"] == []


# ---------------------------------------------------------------------------
# drift_baseline
# ---------------------------------------------------------------------------

class TestDriftBaseline:
    def test_baseline_stored_and_returns_ok(self, tmp_path):
        with patch("gsc_mcp.tools.drift._DB_PATH", tmp_path / "baselines.db"), \
             patch("gsc_mcp.tools.drift._DRIFT_DIR", tmp_path), \
             _mock_fetch(SIMPLE_HTML, 200), \
             patch("gsc_mcp.tools.drift._fetch_cwv", return_value=None):
            raw = drift_baseline("https://example.com/test/")

        data = json.loads(raw)
        assert data["status"] == "ok"
        assert data["baseline_id"] is not None
        assert data["title"] == "Test Page"
        assert data["h1"] == "Main Heading"
        assert data["schema_count"] == 1

    def test_ssrf_blocked_returns_error(self):
        with patch("gsc_mcp.tools.drift.safe_fetch_html", side_effect=URLSafetyError("Blocked")):
            raw = drift_baseline("http://169.254.169.254/")
        data = json.loads(raw)
        assert data["verdict"] == "ssrf_blocked"

    def test_fetch_error_returns_error(self, tmp_path):
        with patch("gsc_mcp.tools.drift.safe_fetch_html",
                   side_effect=httpx.ConnectError("timeout")):
            raw = drift_baseline("https://example.com/")
        data = json.loads(raw)
        assert data["verdict"] == "fetch_error"

    def test_meta_block_present(self, tmp_path):
        with patch("gsc_mcp.tools.drift._DB_PATH", tmp_path / "baselines.db"), \
             patch("gsc_mcp.tools.drift._DRIFT_DIR", tmp_path), \
             _mock_fetch(SIMPLE_HTML, 200), \
             patch("gsc_mcp.tools.drift._fetch_cwv", return_value=None):
            raw = drift_baseline("https://example.com/")

        data = json.loads(raw)
        assert "_meta" in data
        assert data["_meta"]["tool"] == "drift_baseline"


# ---------------------------------------------------------------------------
# drift_compare
# ---------------------------------------------------------------------------

class TestDriftCompare:
    def test_no_drift_when_page_unchanged(self, tmp_path):
        """Baseline and current are identical -- no triggered findings."""
        with patch("gsc_mcp.tools.drift._DB_PATH", tmp_path / "baselines.db"), \
             patch("gsc_mcp.tools.drift._DRIFT_DIR", tmp_path), \
             _mock_fetch(SIMPLE_HTML, 200), \
             patch("gsc_mcp.tools.drift._fetch_cwv", return_value=None):
            drift_baseline("https://example.com/test/")

        with patch("gsc_mcp.tools.drift._DB_PATH", tmp_path / "baselines.db"), \
             patch("gsc_mcp.tools.drift._DRIFT_DIR", tmp_path), \
             _mock_fetch(SIMPLE_HTML, 200), \
             patch("gsc_mcp.tools.drift._fetch_cwv", return_value=None):
            raw = drift_compare("https://example.com/test/")

        data = json.loads(raw)
        assert data["summary"]["critical"] == 0
        assert data["summary"]["warning"] == 0

    def test_h1_removal_triggers_critical(self, tmp_path):
        with patch("gsc_mcp.tools.drift._DB_PATH", tmp_path / "baselines.db"), \
             patch("gsc_mcp.tools.drift._DRIFT_DIR", tmp_path), \
             _mock_fetch(SIMPLE_HTML, 200), \
             patch("gsc_mcp.tools.drift._fetch_cwv", return_value=None):
            drift_baseline("https://example.com/test/")

        with patch("gsc_mcp.tools.drift._DB_PATH", tmp_path / "baselines.db"), \
             patch("gsc_mcp.tools.drift._DRIFT_DIR", tmp_path), \
             _mock_fetch(NO_H1_HTML, 200), \
             patch("gsc_mcp.tools.drift._fetch_cwv", return_value=None):
            raw = drift_compare("https://example.com/test/")

        data = json.loads(raw)
        assert data["summary"]["critical"] >= 1
        triggered_rules = [f["rule"] for f in data["triggered_findings"]]
        assert "h1_removed" in triggered_rules

    def test_noindex_added_triggers_critical(self, tmp_path):
        with patch("gsc_mcp.tools.drift._DB_PATH", tmp_path / "baselines.db"), \
             patch("gsc_mcp.tools.drift._DRIFT_DIR", tmp_path), \
             _mock_fetch(SIMPLE_HTML, 200), \
             patch("gsc_mcp.tools.drift._fetch_cwv", return_value=None):
            drift_baseline("https://example.com/test/")

        with patch("gsc_mcp.tools.drift._DB_PATH", tmp_path / "baselines.db"), \
             patch("gsc_mcp.tools.drift._DRIFT_DIR", tmp_path), \
             _mock_fetch(NOINDEX_HTML, 200), \
             patch("gsc_mcp.tools.drift._fetch_cwv", return_value=None):
            raw = drift_compare("https://example.com/test/")

        data = json.loads(raw)
        triggered_rules = [f["rule"] for f in data["triggered_findings"]]
        assert "noindex_added" in triggered_rules

    def test_no_baseline_returns_error(self, tmp_path):
        with patch("gsc_mcp.tools.drift._DB_PATH", tmp_path / "baselines.db"), \
             patch("gsc_mcp.tools.drift._DRIFT_DIR", tmp_path), \
             _mock_fetch(SIMPLE_HTML, 200), \
             patch("gsc_mcp.tools.drift._fetch_cwv", return_value=None):
            raw = drift_compare("https://example.com/never-baselined/")

        data = json.loads(raw)
        assert data["verdict"] == "no_baseline"

    def test_17_rules_evaluated(self, tmp_path):
        with patch("gsc_mcp.tools.drift._DB_PATH", tmp_path / "baselines.db"), \
             patch("gsc_mcp.tools.drift._DRIFT_DIR", tmp_path), \
             _mock_fetch(SIMPLE_HTML, 200), \
             patch("gsc_mcp.tools.drift._fetch_cwv", return_value=None):
            drift_baseline("https://example.com/test/")

        with patch("gsc_mcp.tools.drift._DB_PATH", tmp_path / "baselines.db"), \
             patch("gsc_mcp.tools.drift._DRIFT_DIR", tmp_path), \
             _mock_fetch(SIMPLE_HTML, 200), \
             patch("gsc_mcp.tools.drift._fetch_cwv", return_value=None):
            raw = drift_compare("https://example.com/test/")

        data = json.loads(raw)
        assert data["summary"]["total_rules"] == 17


# ---------------------------------------------------------------------------
# drift_history
# ---------------------------------------------------------------------------

class TestDriftHistory:
    def test_history_returns_comparisons(self, tmp_path):
        url = "https://example.com/history-test/"
        with patch("gsc_mcp.tools.drift._DB_PATH", tmp_path / "baselines.db"), \
             patch("gsc_mcp.tools.drift._DRIFT_DIR", tmp_path), \
             _mock_fetch(SIMPLE_HTML, 200), \
             patch("gsc_mcp.tools.drift._fetch_cwv", return_value=None):
            drift_baseline(url)
            drift_compare(url)
            drift_compare(url)

        with patch("gsc_mcp.tools.drift._DB_PATH", tmp_path / "baselines.db"), \
             patch("gsc_mcp.tools.drift._DRIFT_DIR", tmp_path):
            raw = drift_history(url)

        data = json.loads(raw)
        assert data["count"] == 2
        assert len(data["comparisons"]) == 2

    def test_history_empty_for_unknown_url(self, tmp_path):
        with patch("gsc_mcp.tools.drift._DB_PATH", tmp_path / "baselines.db"), \
             patch("gsc_mcp.tools.drift._DRIFT_DIR", tmp_path):
            raw = drift_history("https://example.com/never-seen/")

        data = json.loads(raw)
        assert data["count"] == 0

    def test_meta_block_present(self, tmp_path):
        with patch("gsc_mcp.tools.drift._DB_PATH", tmp_path / "baselines.db"), \
             patch("gsc_mcp.tools.drift._DRIFT_DIR", tmp_path):
            raw = drift_history("https://example.com/")

        data = json.loads(raw)
        assert "_meta" in data
        assert data["_meta"]["tool"] == "drift_history"
