import json
from gsc_mcp.auth import get_searchconsole_service
from gsc_mcp.meta import with_meta

_ALL_TOOLS = [
    "get_capabilities",
    "list_properties",
    "get_site_details",
    "get_search_analytics",
    "get_performance_overview",
    "compare_search_periods",
    "get_search_by_page_query",
    "get_advanced_search_analytics",
    "quick_wins",
    "traffic_drops",
    "check_alerts",
    "inspect_url",
    "batch_url_inspection",
    "check_indexing_issues",
    "submit_url",
    "submit_batch",
    "list_sitemaps",
    "submit_sitemap",
]


def get_capabilities() -> str:
    return json.dumps(with_meta(
        {"total": len(_ALL_TOOLS), "tools": _ALL_TOOLS},
        tool="get_capabilities",
        params={},
    ))


def list_properties() -> str:
    svc = get_searchconsole_service()
    response = svc.sites().list().execute()
    entries = response.get("siteEntry", [])
    properties = [
        {"url": e["siteUrl"], "permission": e.get("permissionLevel", "unknown")}
        for e in entries
    ]
    return json.dumps(with_meta(
        {"count": len(properties), "properties": properties},
        tool="list_properties",
        params={},
    ))


def get_site_details(site_url: str) -> str:
    svc = get_searchconsole_service()
    response = svc.sites().get(siteUrl=site_url).execute()
    return json.dumps(with_meta(
        {
            "url": response.get("siteUrl", site_url),
            "permission": response.get("permissionLevel", "unknown"),
        },
        tool="get_site_details",
        params={"site_url": site_url},
    ))
