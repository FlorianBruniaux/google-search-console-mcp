"""Central tool registry for gsc-mcp.

Single source of truth for all registered tool functions. Both the MCP server (server.py)
and the CLI (cli.py) import from here, so no more three-way manual sync between
server.py imports, mcp.tool() calls, and _ALL_TOOLS in properties.py.

The assert at module load time locks the invariant: if a tool is added to
properties._ALL_TOOLS but not here (or vice versa), the import fails loudly.
"""

from typing import Callable

from gsc_mcp.tools.properties import (
    get_capabilities,
    list_properties,
    get_site_details,
    _ALL_TOOLS,
)
from gsc_mcp.tools.analytics import (
    get_search_analytics,
    get_performance_overview,
    compare_search_periods,
    get_search_by_page_query,
    get_advanced_search_analytics,
    analytics_anomalies,
    discover_performance,
    news_performance,
    search_type_breakdown,
    ai_overviews_impact,
)
from gsc_mcp.tools.seo import (
    quick_wins,
    traffic_drops,
    check_alerts,
    seo_striking_distance,
    seo_cannibalization,
    seo_lost_queries,
    parasite_risk,
    prune_candidates,
)
from gsc_mcp.tools.inspection import inspect_url, batch_url_inspection, check_indexing_issues
from gsc_mcp.tools.indexing import submit_url, submit_batch, indexnow_submit
from gsc_mcp.tools.sitemaps import (
    list_sitemaps,
    submit_sitemap,
    sitemaps_delete,
    sitemaps_get,
    sitemap_audit,
)
from gsc_mcp.tools.ga4 import (
    ga4_ai_referrals,
    ga4_organic_landing_pages,
    ga4_traffic_sources,
    ga4_page_performance,
    ga4_realtime,
    ga4_user_behavior,
    ga4_conversion_funnel,
    ga4_funnel,
)
from gsc_mcp.tools.cross import traffic_health_check, page_analysis, page_health_score, content_brief
from gsc_mcp.tools.crux import crux_page_vitals, crux_history, crux_lcp_subparts
from gsc_mcp.tools.technical import (
    schema_validate,
    schema_generate,
    ai_visibility_audit,
    gbp_deprecation_lint,
    pagespeed_audit,
)
from gsc_mcp.tools.drift import drift_baseline, drift_compare, drift_history
from gsc_mcp.tools.content import (
    content_quality,
    hreflang_audit,
    page_technical_audit,
    preload_audit,
    heading_audit,
)
from gsc_mcp.tools.editorial import editorial_audit
from gsc_mcp.tools.rewrite import rewrite_fidelity_check
from gsc_mcp.tools.change_impact import seo_change_impact
from gsc_mcp.tools.links import internal_links_audit, link_equity_map
from gsc_mcp.tools.link_targets import link_targets_audit
from gsc_mcp.tools.bing_analytics import (
    bing_link_counts,
    bing_page_query_stats,
    bing_page_stats,
    bing_query_stats,
    bing_rank_traffic_stats,
    bing_url_links,
)
from gsc_mcp.tools.bing_webmaster import (
    bing_crawl_issues,
    bing_crawl_settings_get,
    bing_crawl_stats,
    bing_feed_details,
    bing_feed_remove,
    bing_feed_submit,
    bing_feeds_list,
    bing_sites_list,
    bing_url_info,
    bing_url_submission_quota,
    bing_url_submit,
    bing_url_traffic,
    bing_urls_submit_batch,
)
from gsc_mcp.tools.search_compare import compare_search_engines
from gsc_mcp.tools.search_breakdown import search_change_breakdown


TOOLS: dict[str, Callable[..., str]] = {
    fn.__name__: fn
    for fn in (
        get_capabilities,
        list_properties,
        get_site_details,
        get_search_analytics,
        get_performance_overview,
        compare_search_periods,
        search_change_breakdown,
        seo_change_impact,
        get_search_by_page_query,
        get_advanced_search_analytics,
        analytics_anomalies,
        quick_wins,
        traffic_drops,
        check_alerts,
        seo_striking_distance,
        seo_cannibalization,
        seo_lost_queries,
        inspect_url,
        batch_url_inspection,
        check_indexing_issues,
        submit_url,
        submit_batch,
        list_sitemaps,
        submit_sitemap,
        sitemaps_delete,
        sitemaps_get,
        sitemap_audit,
        ga4_organic_landing_pages,
        ga4_ai_referrals,
        ga4_traffic_sources,
        ga4_page_performance,
        ga4_realtime,
        ga4_user_behavior,
        ga4_conversion_funnel,
        traffic_health_check,
        page_analysis,
        crux_page_vitals,
        crux_history,
        schema_validate,
        schema_generate,
        drift_baseline,
        drift_compare,
        drift_history,
        discover_performance,
        news_performance,
        search_type_breakdown,
        ai_overviews_impact,
        page_health_score,
        content_brief,
        ga4_funnel,
        content_quality,
        editorial_audit,
        rewrite_fidelity_check,
        hreflang_audit,
        page_technical_audit,
        preload_audit,
        crux_lcp_subparts,
        indexnow_submit,
        parasite_risk,
        ai_visibility_audit,
        gbp_deprecation_lint,
        pagespeed_audit,
        heading_audit,
        internal_links_audit,
        link_targets_audit,
        link_equity_map,
        prune_candidates,
        bing_sites_list,
        bing_query_stats,
        bing_page_stats,
        bing_page_query_stats,
        bing_rank_traffic_stats,
        bing_crawl_stats,
        bing_crawl_issues,
        bing_crawl_settings_get,
        bing_url_info,
        bing_url_traffic,
        bing_feeds_list,
        bing_feed_details,
        bing_url_submission_quota,
        bing_link_counts,
        bing_url_links,
        bing_url_submit,
        bing_urls_submit_batch,
        bing_feed_submit,
        bing_feed_remove,
        compare_search_engines,
    )
}

assert set(TOOLS) == set(_ALL_TOOLS), (
    f"Registry/properties mismatch — update registry.py or properties._ALL_TOOLS.\n"
    f"In registry only: {set(TOOLS) - set(_ALL_TOOLS)}\n"
    f"In _ALL_TOOLS only: {set(_ALL_TOOLS) - set(TOOLS)}"
)
