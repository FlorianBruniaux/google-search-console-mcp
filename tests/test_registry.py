"""Tests for the central tool registry.

These tests must FAIL (RED) before registry.py exists, then pass (GREEN) after.
Run pytest tests/test_registry.py to verify.
"""

from gsc_mcp.registry import TOOLS
from gsc_mcp.tools.properties import _ALL_TOOLS


EXPECTED_BING_TOOLS = {
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
}

EXPECTED_CROSS_ENGINE_TOOLS = {"compare_search_engines"}

EXPECTED_EXISTING_TOOLS = {
    "get_capabilities",
    "list_properties",
    "get_site_details",
    "get_search_analytics",
    "get_performance_overview",
    "compare_search_periods",
    "search_change_breakdown",
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
    "sitemap_audit",
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
    "editorial_audit",
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
    "link_targets_audit",
    "link_equity_map",
    "prune_candidates",
}

EXPECTED_ALL_TOOLS = (
    EXPECTED_EXISTING_TOOLS | EXPECTED_BING_TOOLS | EXPECTED_CROSS_ENGINE_TOOLS
)


def test_registry_contains_exact_bing_surface():
    """The public Bing surface excludes the two unvalidated keyword methods."""
    registered = {name for name in TOOLS if name.startswith("bing_")}
    assert registered == EXPECTED_BING_TOOLS


def test_registry_contains_cross_engine_tools():
    assert EXPECTED_CROSS_ENGINE_TOOLS <= set(TOOLS)


def test_registry_final_count_is_derived_from_added_surface():
    assert set(TOOLS) == EXPECTED_ALL_TOOLS
    assert len(TOOLS) == len(EXPECTED_ALL_TOOLS)


def test_registry_names_match_all_tools():
    """Tool names in the registry must exactly match _ALL_TOOLS in properties.py."""
    assert set(TOOLS) == set(_ALL_TOOLS), (
        f"Registry/properties mismatch.\n"
        f"In registry only: {set(TOOLS) - set(_ALL_TOOLS)}\n"
        f"In _ALL_TOOLS only: {set(_ALL_TOOLS) - set(TOOLS)}"
    )


def test_registry_values_are_callable():
    """Every entry in TOOLS must be a callable (Python function)."""
    for name, fn in TOOLS.items():
        assert callable(fn), f"TOOLS[{name!r}] is not callable: {fn!r}"


def test_registry_keys_match_function_names():
    """Dict keys must match the actual __name__ of each function."""
    for key, fn in TOOLS.items():
        assert fn.__name__ == key, (
            f"Key mismatch: TOOLS[{key!r}] -> fn.__name__={fn.__name__!r}"
        )
