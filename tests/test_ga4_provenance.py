"""Source identities must describe the API request that produced each report."""

import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from gsc_mcp.meta import with_meta
from gsc_mcp.tools import cross, ga4


GA4_CASES = [
    ("ga4_organic_landing_pages", {}, "run_report"),
    ("ga4_traffic_sources", {}, "run_report"),
    ("ga4_page_performance", {}, "run_report"),
    ("ga4_realtime", {}, "run_realtime_report"),
    ("ga4_user_behavior", {}, "batch_run_reports"),
    ("ga4_conversion_funnel", {}, "run_report"),
    ("ga4_funnel", {
        "steps": [{"name": "Visit", "event": "page_view"}, {"name": "Buy", "event": "purchase"}],
        "start_date": "28daysAgo", "end_date": "today",
    }, "run_funnel_report"),
]

CROSS_CASES = [
    ("traffic_health_check", {}, "ga4_organic_landing_pages"),
    ("page_analysis", {}, "ga4_organic_landing_pages"),
    ("content_brief", {"page_url": "https://example.com/blog"}, "ga4_page_performance"),
    ("page_health_score", {"url": "https://example.com/blog"}, "ga4_page_performance"),
]


@pytest.fixture
def clients(monkeypatch, mock_ga4_service):
    monkeypatch.setenv("GA4_PROPERTY_ID", "123456789")
    monkeypatch.setattr(ga4, "get_ga4_service", lambda: mock_ga4_service)
    alpha = MagicMock()
    alpha.run_funnel_report.return_value = SimpleNamespace(funnel_table=SimpleNamespace(rows=[]))
    monkeypatch.setattr(ga4, "get_alpha_ga4_service", lambda: alpha)
    return mock_ga4_service, alpha


@pytest.fixture
def cross_clients(monkeypatch, clients):
    # Keep the real GA4 tools, property resolution and JSON composition.
    monkeypatch.setattr(cross, "get_search_analytics", lambda site, *args, **kwargs: json.dumps({
        "site": site, "rows": [], "date_range": {"start": "2026-09-01", "end": "2026-09-28"},
    }))
    monkeypatch.setattr(cross, "inspect_url", lambda **kwargs: json.dumps({
        "indexing_state": "INDEXING_ALLOWED", "verdict": "PASS",
    }))
    monkeypatch.setattr(cross, "crux_page_vitals", lambda **kwargs: json.dumps({"metrics": {}}))
    monkeypatch.setattr(cross, "schema_validate", lambda **kwargs: json.dumps({
        "schemas_detected": 0, "schemas": [],
    }))
    return clients


@pytest.mark.parametrize("name,kwargs,method", GA4_CASES)
@pytest.mark.parametrize("supplied,expected", [
    (None, "properties/123456789"),
    ("987654321", "properties/987654321"),
    ("properties/987654321", "properties/987654321"),
    (" properties/987654321 ", "properties/987654321"),
])
def test_ga4_provenance_matches_request_property_on_empty_results(clients, name, kwargs, method, supplied, expected):
    beta, alpha = clients
    client = alpha if method == "run_funnel_report" else beta
    result = json.loads(getattr(ga4, name)(**kwargs, property_id=supplied))
    requests = getattr(client, method).call_args_list
    assert requests
    assert all(call.args[0].property == expected for call in requests)
    assert result["_meta"]["sources"] == {"ga4": {"property": expected}}
    assert result["_meta"]["params"]["property_id"] == supplied


@pytest.mark.parametrize("name,kwargs,method", GA4_CASES)
def test_ga4_provenance_does_not_reresolve_default_after_request_setup(monkeypatch, clients, name, kwargs, method):
    beta, alpha = clients
    def changed_config(client):
        monkeypatch.setenv("GA4_PROPERTY_ID", "777777777")
        return client
    monkeypatch.setattr(ga4, "get_ga4_service", lambda: changed_config(beta))
    monkeypatch.setattr(ga4, "get_alpha_ga4_service", lambda: changed_config(alpha))
    result = json.loads(getattr(ga4, name)(**kwargs))
    client = alpha if method == "run_funnel_report" else beta
    assert all(call.args[0].property == "properties/123456789" for call in getattr(client, method).call_args_list)
    assert result["_meta"]["sources"]["ga4"]["property"] == "properties/123456789"


@pytest.mark.parametrize("name,kwargs,child", CROSS_CASES)
def test_cross_provenance_survives_real_child_tool(cross_clients, name, kwargs, child):
    result = json.loads(getattr(cross, name)(site="sc-domain:example.com", **kwargs))
    assert result["_meta"]["sources"] == {
        "gsc": {"site": "sc-domain:example.com"},
        "ga4": {"property": "properties/123456789"},
    }
    assert result["_meta"]["params"]["property_id"] is None


@pytest.mark.parametrize("name,kwargs,child", CROSS_CASES)
@pytest.mark.parametrize("source", [None, {"property": "properties/555555555"}])
def test_cross_uses_child_provenance_instead_of_resolving_config_again(monkeypatch, cross_clients, name, kwargs, child, source):
    child_result = {"pages": [], "_meta": {"tool": child, "params": {}}}
    if source is not None:
        child_result["_meta"]["sources"] = {"ga4": source}
    monkeypatch.setattr(cross, child, lambda **kwargs: json.dumps(child_result))
    result = json.loads(getattr(cross, name)(site="https://example.com/", property_id="987654321", **kwargs))
    assert result["_meta"]["sources"] == {
        "gsc": {"site": "https://example.com/"},
        "ga4": source if source is not None else {"property": None},
    }


@pytest.mark.parametrize("name,kwargs,child", CROSS_CASES[2:])
def test_degraded_cross_report_does_not_claim_a_configured_source(monkeypatch, cross_clients, name, kwargs, child):
    def unavailable(**kwargs):
        raise RuntimeError("No GA4 config")
    monkeypatch.setattr(cross, child, unavailable)
    result = json.loads(getattr(cross, name)(site="sc-domain:example.com", **kwargs))
    assert result["_meta"]["sources"]["ga4"] == {"property": None}
    if name == "content_brief":
        assert result["ga4"] is None
    else:
        assert result["components"]["ga4"]["available"] is False


@pytest.mark.parametrize("name,kwargs,child", CROSS_CASES)
def test_multiple_sites_do_not_reuse_previous_source_identity(monkeypatch, cross_clients, name, kwargs, child):
    scenarios = [
        ("123456789", None, "sc-domain:example.com", "properties/123456789"),
        ("123456789", "987654321", "https://other.example/", "properties/987654321"),
        ("555555555", None, "sc-domain:third.example", "properties/555555555"),
    ]
    results = []
    for default, supplied, site, expected in scenarios:
        monkeypatch.setenv("GA4_PROPERTY_ID", default)
        result = json.loads(getattr(cross, name)(site=site, property_id=supplied, **kwargs))
        assert result["_meta"]["sources"] == {"gsc": {"site": site}, "ga4": {"property": expected}}
        results.append(result)
    assert results[0]["_meta"]["sources"]["ga4"]["property"] == "properties/123456789"


def test_funnel_validation_does_not_resolve_a_property(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Invalid steps must return before credentials or property resolution")
    monkeypatch.delenv("GA4_PROPERTY_ID", raising=False)
    monkeypatch.setattr(ga4, "get_ga4_property_id", forbidden)
    monkeypatch.setattr(ga4, "get_alpha_ga4_service", forbidden)
    result = json.loads(ga4.ga4_funnel([], "28daysAgo", "today"))
    assert result["error"] == "INVALID_STEPS"
    assert result["_meta"].get("sources", {}).get("ga4", {}).get("property") is None


def test_metadata_sources_are_optional_and_leave_requested_params_unchanged():
    params = {"property_id": None}
    original = with_meta({"rows": []}, "example", params)
    assert original["_meta"].pop("evidence") == {"version": 1, "fields": {}, "inventory_status": "unregistered"}
    assert original == {
        "rows": [], "_meta": {"tool": "example", "params": params},
    }
    result = with_meta({"rows": []}, "example", params, sources={"ga4": {"property": "properties/123456789"}})
    assert result["_meta"]["params"] == {"property_id": None}
    assert result["_meta"]["sources"]["ga4"]["property"] == "properties/123456789"
