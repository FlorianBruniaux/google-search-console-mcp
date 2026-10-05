import json
from unittest.mock import MagicMock, patch

from gsc_mcp.tools.analytics import compare_search_periods, get_performance_overview
from gsc_mcp.tools.inspection import inspect_url
from gsc_mcp.tools.seo import check_alerts
from gsc_mcp.tools.sitemaps import sitemap_audit


SITE = "https://example.com/"


def test_overview_property_total_includes_anonymized_queries():
    service = MagicMock()
    property_row = {"clicks": 61, "impressions": 2108, "ctr": 61 / 2108, "position": 12}
    visible_query = {"keys": ["visible"], "clicks": 40, "impressions": 258, "ctr": 40 / 258, "position": 4}

    def query(*, siteUrl, body):
        request = MagicMock()
        request.execute.return_value = {"rows": [visible_query if "dimensions" in body else property_row]}
        return request

    service.searchanalytics.return_value.query.side_effect = query
    with patch("gsc_mcp.tools.analytics.get_searchconsole_service", return_value=service):
        result = json.loads(get_performance_overview(SITE))
    assert result["totals"]["clicks"] == 61
    assert result["totals"]["impressions"] == 2108
    assert result["top_queries"][0]["query"] == "visible"


def test_period_comparison_uses_property_totals():
    service = MagicMock()
    total = {"clicks": 61, "impressions": 2108}
    visible = {"keys": ["visible"], "clicks": 40, "impressions": 258}

    def query(*, siteUrl, body):
        request = MagicMock()
        request.execute.return_value = {"rows": [visible if "dimensions" in body else total]}
        return request

    service.searchanalytics.return_value.query.side_effect = query
    with patch("gsc_mcp.tools.analytics.get_searchconsole_service", return_value=service):
        result = json.loads(compare_search_periods(SITE))
    assert result["period_a"]["clicks"] == 61
    assert result["period_b"]["impressions"] == 2108


def test_alert_does_not_use_visible_queries_as_denominator():
    service = MagicMock()
    property_row = {"clicks": 61, "impressions": 2108}
    visible_pair = {"keys": ["https://example.com/a", "visible"], "clicks": 25, "impressions": 258, "position": 4}

    def query(*, siteUrl, body):
        request = MagicMock()
        request.execute.return_value = {"rows": [visible_pair if "dimensions" in body else property_row]}
        return request

    service.searchanalytics.return_value.query.side_effect = query
    with patch("gsc_mcp.tools.seo.get_searchconsole_service", return_value=service):
        result = json.loads(check_alerts(SITE))
    assert not any(a["type"] == "traffic_concentration" for a in result["alerts"])


def test_unknown_fetch_state_is_not_a_fetch_error():
    service = MagicMock()
    service.urlInspection.return_value.index.return_value.inspect.return_value.execute.return_value = {
        "inspectionResult": {"indexStatusResult": {
            "verdict": "NEUTRAL", "coverageState": "Discovered - currently not indexed",
            "pageFetchState": "PAGE_FETCH_STATE_UNSPECIFIED"
        }}
    }
    with patch("gsc_mcp.tools.inspection.get_searchconsole_service", return_value=service):
        result = json.loads(inspect_url("https://example.com/a", SITE))
    assert result["category"] == "unknown"
    assert result["coverage_state"] == "Discovered - currently not indexed"


def test_sitemap_reports_search_visibility_not_indexation():
    from gsc_mcp import url_safety

    sitemap = b'''<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
        <url><loc>https://example.com/a</loc></url>
        <url><loc>https://example.com/b</loc></url>
    </urlset>'''
    client = MagicMock()
    client.__enter__.return_value = client
    client.get.return_value.content = sitemap
    with patch.object(url_safety, "validate_url_strict"), \
         patch("gsc_mcp.tools.sitemaps.httpx.Client", return_value=client), \
         patch("gsc_mcp.tools.sitemaps.get_search_analytics", return_value=json.dumps({
             "rows": [{"page": "https://example.com/a"}]
         })):
        result = json.loads(sitemap_audit(SITE, "https://example.com/sitemap.xml"))
    assert result["urls_with_search_data"] == 1
    assert result["urls_without_search_data"] == 1
    assert result["verdict"] == "partial"
    assert result["visibility_verdict"] == "partial_search_visibility"
    assert result["urls_missing_from_gsc"] == result["urls_without_search_data"]
