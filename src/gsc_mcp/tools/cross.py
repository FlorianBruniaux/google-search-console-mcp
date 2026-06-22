"""Cross-platform tools combining GSC and GA4 data.

Both tools call high-level functions from analytics.py and ga4.py, parse their
JSON output, then join on normalised URL paths. GSC returns absolute URLs;
GA4 returns paths (sometimes with query strings). _normalize_url strips both
down to bare paths so the join is reliable.

Note on date alignment: GSC uses a 3-day reporting lag while GA4 can report
up to today. The windows are therefore not perfectly aligned, but both cover
~28 days, which is accurate enough for health-check ratios.
"""

import json
import math
from urllib.parse import urlsplit

from gsc_mcp.tools.analytics import get_search_analytics
from gsc_mcp.tools.ga4 import ga4_organic_landing_pages
from gsc_mcp.meta import with_meta


def _normalize_url(url: str) -> str:
    """Return the path component of url, stripping scheme, host, query and fragment.

    Trailing slashes are removed (except for the root "/"). If two URLs normalise
    to the same path (e.g. /x and /x/) the join intentionally merges them.
    """
    if not url:
        return ""
    parts = urlsplit(url)
    if parts.scheme or parts.netloc:
        path = parts.path or "/"
    else:
        path = url.split("?", 1)[0].split("#", 1)[0]
    if len(path) > 1 and path.endswith("/"):
        path = path.rstrip("/")
    return path or "/"


def traffic_health_check(site: str, days: int = 28, property_id: str = None) -> str:
    """Compare total GSC clicks with total GA4 organic sessions to detect tracking gaps.

    Fetches aggregate GSC clicks (no page dimension) and sums all organic sessions
    from GA4. The ratio ga4_sessions / gsc_clicks indicates tracking health:

    - "no_gsc_data"  : zero GSC clicks (ratio is None, nothing to compare)
    - "tracking_gap" : ratio < 0.6 (GA4 records far fewer sessions than GSC clicks)
    - "filter_issue" : ratio > 1.3 (GA4 records more sessions than GSC clicks)
    - "healthy"      : 0.6 <= ratio <= 1.3

    Boundaries 0.6 and 1.3 are inclusive of the healthy range (strict < and >).
    GA4 is queried with limit=10000 to avoid under-counting sessions on large sites.
    """
    gsc_data = json.loads(get_search_analytics(site, days, dimensions=[]))
    total_gsc_clicks = sum(r["clicks"] for r in gsc_data["rows"])
    date_range = gsc_data["date_range"]

    ga_data = json.loads(
        ga4_organic_landing_pages(
            start_date=f"{days}daysAgo",
            end_date="today",
            limit=10000,
            property_id=property_id,
        )
    )
    total_ga4_sessions = sum(p["sessions"] for p in ga_data["pages"])

    if total_gsc_clicks == 0:
        status = "no_gsc_data"
        ratio = None
    else:
        ratio = total_ga4_sessions / total_gsc_clicks
        if ratio < 0.6:
            status = "tracking_gap"
        elif ratio > 1.3:
            status = "filter_issue"
        else:
            status = "healthy"

    return json.dumps(
        with_meta(
            {
                "site": site,
                "date_range": date_range,
                "total_gsc_clicks": total_gsc_clicks,
                "total_ga4_sessions": total_ga4_sessions,
                "ratio": round(ratio, 3) if ratio is not None else None,
                "status": status,
                "note": "GSC data has a 3-day lag vs GA4. Ratios are approximate.",
            },
            tool="traffic_health_check",
            params={"site": site, "days": days, "property_id": property_id},
        )
    )


def page_analysis(site: str, days: int = 28, limit: int = 100, property_id: str = None) -> str:
    """Join GSC and GA4 data at the page level and rank by opportunity score.

    GSC rows are fetched with dimensions=["page"] (already aggregated per page).
    GA4 organic landing pages are fetched with a high limit to avoid truncation.
    Pages are joined on _normalize_url. Pages that appear in only one source get
    None for the missing fields.

    opportunity_score = log10(impressions+1)*10 + engagement_rate*100 + log10(conversions+1)*20

    engagement_rate is derived as engaged_sessions/sessions (GA4 native formula)
    because ga4_organic_landing_pages does not expose it directly.

    Results are sorted by opportunity_score descending, truncated to `limit`.
    """
    gsc_data = json.loads(
        get_search_analytics(site, days, dimensions=["page"], row_limit=1000)
    )
    date_range = gsc_data["date_range"]

    # GSC map: normalised path -> {clicks, impressions, ctr, position}
    gsc_map: dict = {}
    for row in gsc_data["rows"]:
        path = _normalize_url(row["page"])
        gsc_map[path] = {
            "clicks": row["clicks"],
            "impressions": row["impressions"],
            "ctr": row["ctr"],
            "position": row["position"],
        }

    ga_data = json.loads(
        ga4_organic_landing_pages(
            start_date=f"{days}daysAgo",
            end_date="today",
            limit=1000,
            property_id=property_id,
        )
    )

    # GA4 map: normalised path -> {sessions, engagement_rate, conversions}
    # engagement_rate derived from engaged_sessions / sessions (GA4 formula)
    ga_map: dict = {}
    for page in ga_data["pages"]:
        path = _normalize_url(page["landing_page"])
        sessions = page["sessions"]
        engaged = page["engaged_sessions"]
        engagement_rate = engaged / sessions if sessions else 0.0
        ga_map[path] = {
            "sessions": sessions,
            "engagement_rate": engagement_rate,
            "conversions": page["conversions"],
        }

    all_paths = set(gsc_map) | set(ga_map)

    pages = []
    for path in all_paths:
        gsc = gsc_map.get(path)
        ga = ga_map.get(path)

        clicks = gsc["clicks"] if gsc else None
        impressions = gsc["impressions"] if gsc else None
        ctr = gsc["ctr"] if gsc else None
        position = gsc["position"] if gsc else None
        sessions = ga["sessions"] if ga else None
        engagement_rate = ga["engagement_rate"] if ga else None
        conversions = ga["conversions"] if ga else None

        score = (
            math.log10((impressions or 0) + 1) * 10
            + (engagement_rate or 0) * 100
            + math.log10((conversions or 0) + 1) * 20
        )

        pages.append({
            "page": path,
            "clicks": clicks,
            "impressions": impressions,
            "ctr": ctr,
            "position": position,
            "sessions": sessions,
            "engagement_rate": engagement_rate,
            "conversions": conversions,
            "opportunity_score": round(score, 2),
        })

    pages.sort(key=lambda p: p["opportunity_score"], reverse=True)
    pages = pages[:limit]

    return json.dumps(
        with_meta(
            {
                "site": site,
                "date_range": date_range,
                "count": len(pages),
                "pages": pages,
                "note": "GSC data has a 3-day lag vs GA4. Ratios are approximate.",
            },
            tool="page_analysis",
            params={"site": site, "days": days, "limit": limit, "property_id": property_id},
        )
    )
