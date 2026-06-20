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
)
from gsc_mcp.tools.seo import quick_wins, traffic_drops, check_alerts
from gsc_mcp.tools.inspection import inspect_url, batch_url_inspection, check_indexing_issues
from gsc_mcp.tools.indexing import submit_url, submit_batch
from gsc_mcp.tools.sitemaps import list_sitemaps, submit_sitemap

mcp = FastMCP("gsc-mcp")

mcp.tool()(get_capabilities)
mcp.tool()(list_properties)
mcp.tool()(get_site_details)
mcp.tool()(get_search_analytics)
mcp.tool()(get_performance_overview)
mcp.tool()(compare_search_periods)
mcp.tool()(get_search_by_page_query)
mcp.tool()(get_advanced_search_analytics)
mcp.tool()(quick_wins)
mcp.tool()(traffic_drops)
mcp.tool()(check_alerts)
mcp.tool()(inspect_url)
mcp.tool()(batch_url_inspection)
mcp.tool()(check_indexing_issues)
mcp.tool()(submit_url)
mcp.tool()(submit_batch)
mcp.tool()(list_sitemaps)
mcp.tool()(submit_sitemap)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
