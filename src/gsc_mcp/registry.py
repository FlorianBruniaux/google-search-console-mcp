"""Central tool registry for gsc-mcp.

Single source of truth for all 54 tool functions. Both the MCP server (server.py)
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
from gsc_mcp.tools.technical import schema_validate, schema_generate
from gsc_mcp.tools.drift import drift_baseline, drift_compare, drift_history
from gsc_mcp.tools.content import content_quality, hreflang_audit, page_technical_audit, preload_audit


TOOLS: dict[str, Callable[..., str]] = {
    fn.__name__: fn
    for fn in (
        get_capabilities,
        list_properties,
        get_site_details,
        get_search_analytics,
        get_performance_overview,
        compare_search_periods,
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
        hreflang_audit,
        page_technical_audit,
        preload_audit,
        crux_lcp_subparts,
        indexnow_submit,
        parasite_risk,
    )
}

assert set(TOOLS) == set(_ALL_TOOLS), (
    f"Registry/properties mismatch — update registry.py or properties._ALL_TOOLS.\n"
    f"In registry only: {set(TOOLS) - set(_ALL_TOOLS)}\n"
    f"In _ALL_TOOLS only: {set(_ALL_TOOLS) - set(TOOLS)}"
)
