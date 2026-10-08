"""Proposed regressions; no network, credentials, or repository writes."""
import json
from unittest.mock import MagicMock, patch

import httpx
import pytest

from gsc_mcp.tools.content import heading_audit
from gsc_mcp.tools.technical import schema_validate


def audit_schema(payload, url="https://example.com/"):
    html = '<script type="application/ld+json">' + json.dumps(payload) + '</script>'
    client = MagicMock()
    client.__enter__.return_value = client
    client.get.return_value = httpx.Response(200, text=html, request=httpx.Request("GET", url))
    with patch(
        "gsc_mcp.url_safety.socket.getaddrinfo",
        return_value=[(None, None, None, None, ("93.184.216.34", 0))],
    ), patch(
        "httpx.Client", return_value=client
    ):
        return json.loads(schema_validate(url))


def test_software_recommended_fields_do_not_invalidate():
    result = audit_schema({
        "@type": "SoftwareApplication", "name": "Guide",
        "offers": {"@type": "Offer", "price": 0},
        "aggregateRating": {"@type": "AggregateRating", "ratingValue": 4.6, "ratingCount": 10},
    })
    schema = result["schemas"][0]
    assert schema["valid"] is True
    assert schema["missing_required_fields"] == []
    assert set(schema["missing_recommended_fields"]) == {"applicationCategory", "operatingSystem"}
    assert result["verdict"] == "healthy"


def test_software_name_still_required():
    result = audit_schema({
        "@type": "SoftwareApplication", "applicationCategory": "DeveloperApplication",
        "operatingSystem": "Any",
    })
    assert result["schemas"][0]["missing_required_fields"] == ["name"]
    assert result["verdict"] == "invalid_schemas"


def test_local_field_presence_does_not_claim_google_rich_result_eligibility():
    result = audit_schema({"@type": "SoftwareApplication", "name": "Guide"})
    assert result["validation_scope"] == "local_required_field_presence"
    assert result["google_rich_result_eligibility"] == "not_assessed"
    assert result["schemas"][0]["valid"] is True


def test_recommended_fields_present_are_not_reported_missing():
    result = audit_schema({
        "@type": "SoftwareApplication", "name": "Guide",
        "applicationCategory": "DeveloperApplication", "operatingSystem": "Any",
    })
    assert result["schemas"][0]["missing_recommended_fields"] == []


def test_graph_child_missing_fields_is_invalid_not_unknown_valid():
    result = audit_schema({"@context": "https://schema.org", "@graph": [
        {"@type": "Article", "headline": "A"},
    ]})
    assert result["schemas_detected"] == 1
    assert result["schemas"][0]["type"] == "Article"
    assert set(result["schemas"][0]["missing_required_fields"]) == {"author", "datePublished"}
    assert result["verdict"] == "invalid_schemas"


def test_graph_nodes_suppress_false_missing_type_recommendation():
    result = audit_schema({"@context": "https://schema.org", "@graph": [
        {"@type": "WebSite", "name": "Site", "url": "https://example.com/"},
        {"@type": "FAQPage", "mainEntity": []},
    ]}, "https://example.com/faq")
    assert result["schemas_detected"] == 2
    assert {schema["type"] for schema in result["schemas"]} == {"WebSite", "FAQPage"}
    assert "FAQPage" not in result["recommendations"]


def test_graph_inside_root_array_is_expanded():
    result = audit_schema([
        {"@type": "Organization", "name": "Org"},
        {"@graph": [{"@type": "WebSite", "name": "Site", "url": "https://example.com/"}]},
    ])
    assert result["schemas_detected"] == 2
    assert {schema["type"] for schema in result["schemas"]} == {"Organization", "WebSite"}


def test_typed_graph_container_is_preserved():
    result = audit_schema({"@type": "Organization", "name": "Org", "@graph": [
        {"@type": "WebSite", "name": "Site", "url": "https://example.com/"},
    ]})
    assert {schema["type"] for schema in result["schemas"]} == {"Organization", "WebSite"}


def test_empty_graph_is_not_counted_as_a_valid_unknown_schema():
    result = audit_schema({"@context": "https://schema.org", "@graph": []})
    assert result["schemas_detected"] == 0
    assert result["verdict"] == "missing_schemas"


@pytest.mark.parametrize("heading", ["TL;DR", " tl;dr ", "<span>TL;DR</span>"])
def test_tldr_is_not_an_empty_heading(heading):
    html = '<title>Guide reference</title><h1>Guide installation</h1><h2>' + heading + '</h2><p>Install the package.</p>'
    with patch("gsc_mcp.tools.content.safe_fetch_html", return_value=(html, 200)):
        result = json.loads(heading_audit("https://example.com/guide"))
    assert result["empty_headings"] == []
    assert result["descriptive_ratio"] == 1.0
    assert not any(issue["check"] == "empty_heading" for issue in result["issues"])
    assert result["verdict"] == "healthy"


def test_existing_generic_heading_check_is_preserved():
    html = '<title>Guide reference</title><h1>Guide installation</h1><h2>Introduction</h2>'
    with patch("gsc_mcp.tools.content.safe_fetch_html", return_value=(html, 200)):
        result = json.loads(heading_audit("https://example.com/guide"))
    assert result["empty_headings"] == ["Introduction"]
    assert any(issue["check"] == "empty_heading" for issue in result["issues"])
