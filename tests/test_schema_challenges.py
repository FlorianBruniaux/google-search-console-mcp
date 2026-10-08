"""Synthetic challenge fixtures; no live provider behavior is asserted."""

import json
from unittest.mock import MagicMock, patch

import httpx
import pytest

from gsc_mcp.tools.technical import schema_validate


CHALLENGE_HTML = """<html><head><title>Verify you are human</title>
<script src="/.well-known/sgcaptcha/challenge.js"></script>
</head><body><h1>Verify you are human</h1></body></html>"""

WEBSITE_SCHEMA = """<script type="application/ld+json">
{"@type": "WebSite", "name": "Example", "url": "https://example.com/"}
</script>"""


@pytest.fixture(autouse=True)
def _mock_dns(monkeypatch):
    monkeypatch.setattr(
        "gsc_mcp.url_safety.socket.getaddrinfo",
        lambda *args, **kwargs: [(None, None, None, None, ("93.184.216.34", 0))],
    )


def _audit(html, status=202, *, redirect=False):
    requested = "https://example.com/blog/captcha"
    final = "https://www.example.com/blog/captcha" if redirect else requested

    def get(url, **kwargs):
        request = httpx.Request("GET", url)
        if redirect and url == requested:
            return httpx.Response(301, headers={"location": final}, request=request)
        return httpx.Response(status, text=html, request=request)

    client = MagicMock()
    client.__enter__.return_value = client
    client.__exit__.return_value = False
    client.get.side_effect = get
    with patch("httpx.Client", return_value=client):
        return json.loads(schema_validate(requested))


@pytest.mark.parametrize("status", [200, 202])
def test_known_siteground_challenge_is_unavailable_not_missing_schemas(status):
    result = _audit(CHALLENGE_HTML, status)
    assert result["verdict"] == "challenge_page"
    assert result["http_status"] == status
    assert result["challenge"]["provider"] == "siteground"
    assert len(result["challenge"]["reasons"]) >= 2
    assert result["schemas_detected"] is None
    assert result["schemas"] is None
    assert result["recommendations"] is None
    assert result["validation_scope"] == "not_assessed"
    assert result["google_rich_result_eligibility"] == "not_assessed"
    assert result["_meta"]["tool"] == "schema_validate"
    assert result["_meta"]["params"]["url"] == result["url"]


def test_challenge_retains_requested_and_canonical_final_url():
    result = _audit(CHALLENGE_HTML, redirect=True)
    assert result["verdict"] == "challenge_page"
    assert result["url"] == "https://example.com/blog/captcha"
    assert result["final_url"] == "https://www.example.com/blog/captcha"
    assert result["http_status"] == 202


def test_challenge_own_schema_is_not_attributed_to_target_page():
    result = _audit(CHALLENGE_HTML.replace("</head>", WEBSITE_SCHEMA + "</head>"))
    assert result["verdict"] == "challenge_page"
    assert result["schemas_detected"] is None
    assert result["schemas"] is None


@pytest.mark.parametrize("html", [
    "<html><title>Ordinary page</title>" + WEBSITE_SCHEMA + "</html>",
    "<html><title>CAPTCHA explained</title><p>Verify you are human is a common prompt.</p>"
    + WEBSITE_SCHEMA + "</html>",
    '<html><title>Verify you are human</title><script src="/captcha.js"></script>'
    + WEBSITE_SCHEMA + "</html>",
    '<html><title>SiteGround integration</title><script src="/.well-known/sgcaptcha/challenge.js"></script>'
    + WEBSITE_SCHEMA + "</html>",
    '<html><title>Verify you are human</title><code>/.well-known/sgcaptcha/challenge.js</code>'
    + WEBSITE_SCHEMA + "</html>",
    '<html><title>Verify you are human</title><script src="/assets/sgcaptcha.js"></script>'
    + WEBSITE_SCHEMA + "</html>",
])
def test_ordinary_202_or_captcha_discussion_keeps_normal_audit(html):
    result = _audit(html)
    assert result["verdict"] == "healthy"
    assert result["schemas_detected"] == 1
    assert result["schemas"][0]["type"] == "WebSite"
    assert result["validation_scope"] == "local_required_field_presence"


def test_ordinary_202_without_schema_is_still_missing_schemas():
    result = _audit("<html><title>Accepted</title><p>CAPTCHA documentation</p></html>")
    assert result["verdict"] == "missing_schemas"
    assert result["schemas_detected"] == 0


def test_siteground_form_challenge_has_provider_and_prompt_evidence():
    result = _audit('<html><h1>Verify that you are human</h1>'
                    '<form action="/.well-known/sgcaptcha/verify" method="post"></form></html>')
    assert result["verdict"] == "challenge_page"
    assert result["challenge"]["provider"] == "siteground"
