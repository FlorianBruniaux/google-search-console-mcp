import sys

if sys.version_info < (3, 11):
    raise RuntimeError("gsc-mcp requires Python 3.11+")

from mcp.server.fastmcp import FastMCP

from gsc_mcp.tools.properties import get_capabilities, list_properties, get_site_details
from gsc_mcp.tools.analytics import (
    get_search_analytics,
    get_performance_overview,
    compare_search_periods,
    get_search_by_page_query,
    get_advanced_search_analytics,
    analytics_anomalies,
)
from gsc_mcp.tools.seo import (
    quick_wins,
    traffic_drops,
    check_alerts,
    seo_striking_distance,
    seo_cannibalization,
    seo_lost_queries,
)
from gsc_mcp.tools.inspection import inspect_url, batch_url_inspection, check_indexing_issues
from gsc_mcp.tools.indexing import submit_url, submit_batch
from gsc_mcp.tools.sitemaps import list_sitemaps, submit_sitemap, sitemaps_delete, sitemaps_get
from gsc_mcp.tools.ga4 import (
    ga4_organic_landing_pages,
    ga4_traffic_sources,
    ga4_page_performance,
    ga4_realtime,
    ga4_user_behavior,
    ga4_conversion_funnel,
)

mcp = FastMCP("gsc-mcp")

mcp.tool()(get_capabilities)
mcp.tool()(list_properties)
mcp.tool()(get_site_details)
mcp.tool()(get_search_analytics)
mcp.tool()(get_performance_overview)
mcp.tool()(compare_search_periods)
mcp.tool()(get_search_by_page_query)
mcp.tool()(get_advanced_search_analytics)
mcp.tool()(analytics_anomalies)
mcp.tool()(quick_wins)
mcp.tool()(traffic_drops)
mcp.tool()(check_alerts)
mcp.tool()(seo_striking_distance)
mcp.tool()(seo_cannibalization)
mcp.tool()(seo_lost_queries)
mcp.tool()(inspect_url)
mcp.tool()(batch_url_inspection)
mcp.tool()(check_indexing_issues)
mcp.tool()(submit_url)
mcp.tool()(submit_batch)
mcp.tool()(list_sitemaps)
mcp.tool()(submit_sitemap)
mcp.tool()(sitemaps_delete)
mcp.tool()(sitemaps_get)
mcp.tool()(ga4_organic_landing_pages)
mcp.tool()(ga4_traffic_sources)
mcp.tool()(ga4_page_performance)
mcp.tool()(ga4_realtime)
mcp.tool()(ga4_user_behavior)
mcp.tool()(ga4_conversion_funnel)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
