import json
import os
from gsc_mcp.auth import get_searchconsole_service
from gsc_mcp.meta import with_meta
from gsc_mcp.retry import with_retry

_ALL_TOOLS = [
    "get_capabilities",
    "list_properties",
    "get_site_details",
    "get_search_analytics",
    "get_performance_overview",
    "compare_search_periods",
    "get_search_by_page_query",
    "get_advanced_search_analytics",
    "analytics_anomalies",
    "quick_wins",
    "traffic_drops",
    "check_alerts",
    "seo_striking_distance",
    "seo_cannibalization",
    "seo_lost_queries",
    "inspect_url",
    "batch_url_inspection",
    "check_indexing_issues",
    "submit_url",
    "submit_batch",
    "list_sitemaps",
    "submit_sitemap",
    "sitemaps_delete",
    "sitemaps_get",
    "ga4_organic_landing_pages",
    "ga4_ai_referrals",
    "ga4_traffic_sources",
    "ga4_page_performance",
    "ga4_realtime",
    "ga4_user_behavior",
    "ga4_conversion_funnel",
    "traffic_health_check",
    "page_analysis",
    "crux_page_vitals",
    "crux_history",
    "sitemap_audit",
    "schema_validate",
    "schema_generate",
    "drift_baseline",
    "drift_compare",
    "drift_history",
    "discover_performance",
    "news_performance",
    "search_type_breakdown",
    "ai_overviews_impact",
    "page_health_score",
    "content_brief",
    "ga4_funnel",
    "content_quality",
    "hreflang_audit",
    "page_technical_audit",
    "preload_audit",
    "crux_lcp_subparts",
    "indexnow_submit",
    "parasite_risk",
    "ai_visibility_audit",
    "gbp_deprecation_lint",
    "pagespeed_audit",
    "heading_audit",
    "internal_links_audit",
    "link_equity_map",
    "prune_candidates",
    "bing_sites_list",
    "bing_query_stats",
    "bing_page_stats",
    "bing_page_query_stats",
    "bing_rank_traffic_stats",
    "bing_crawl_stats",
    "bing_crawl_issues",
    "bing_crawl_settings_get",
    "bing_url_info",
    "bing_url_traffic",
    "bing_feeds_list",
    "bing_feed_details",
    "bing_url_submission_quota",
    "bing_link_counts",
    "bing_url_links",
    "bing_url_submit",
    "bing_urls_submit_batch",
    "bing_feed_submit",
    "bing_feed_remove",
    "compare_search_engines",
]


def get_capabilities() -> str:
    """List all available tools and declared search-engine credentials."""
    return json.dumps(with_meta(
        {
            "total": len(_ALL_TOOLS),
            "tools": _ALL_TOOLS,
            "engines": {
                "google": {
                    "credential_env_declared": bool(
                        os.environ.get("GSC_SERVICE_ACCOUNT_PATH")
                        or os.environ.get("GSC_CREDENTIALS_PATH")
                    ),
                },
                "bing": {
                    "credential_env_declared": bool(
                        os.environ.get("BING_WEBMASTER_API_KEY")
                    ),
                    "tools": sorted(
                        name for name in _ALL_TOOLS if name.startswith("bing_")
                    ),
                },
                "indexnow": {"tools": ["indexnow_submit"]},
            },
        },
        tool="get_capabilities",
        params={},
    ))


@with_retry()
def list_properties() -> str:
    """List all GSC properties the authenticated account can access, with their permission levels."""
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


@with_retry()
def get_site_details(site_url: str) -> str:
    """Get the permission level for a specific GSC property URL."""
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
