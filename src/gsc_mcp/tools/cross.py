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
from gsc_mcp.tools.ga4 import ga4_organic_landing_pages, ga4_page_performance
from gsc_mcp.tools.inspection import inspect_url
from gsc_mcp.tools.crux import crux_page_vitals
from gsc_mcp.tools.technical import schema_validate
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


def traffic_health_check(
    site: str,
    days: int = 28,
    property_id: str | None = None,
    hostname: str | None = None,
    country: str | None = None,
) -> str:
    """Compare total GSC clicks with total GA4 organic sessions to detect tracking gaps.

    Fetches aggregate GSC clicks (no page dimension) and sums all organic sessions
    from GA4. The ratio ga4_sessions / gsc_clicks indicates tracking health:

    - "no_gsc_data"  : zero GSC clicks (ratio is None, nothing to compare)
    - "tracking_gap" : ratio < 0.6 (GA4 records far fewer sessions than GSC clicks)
    - "filter_issue" : ratio > 1.3 (GA4 records more sessions than GSC clicks)
    - "healthy"      : 0.6 <= ratio <= 1.3

    Boundaries 0.6 and 1.3 are inclusive of the healthy range (strict < and >).
    GA4 is queried with limit=10000 to avoid under-counting sessions on large sites.
    hostname and country narrow the GA4 query to a specific host or country.
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
            hostname=hostname,
            country=country,
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
            params={"site": site, "days": days, "property_id": property_id, "hostname": hostname, "country": country},
        )
    )


def page_analysis(
    site: str,
    days: int = 28,
    limit: int = 100,
    property_id: str | None = None,
    hostname: str | None = None,
    country: str | None = None,
) -> str:
    """Join GSC and GA4 data at the page level and rank by opportunity score.

    GSC rows are fetched with dimensions=["page"] (already aggregated per page).
    GA4 organic landing pages are fetched with a high limit to avoid truncation.
    Pages are joined on _normalize_url. Pages that appear in only one source get
    None for the missing fields.

    opportunity_score = log10(impressions+1)*10 + engagement_rate*100 + log10(conversions+1)*20

    engagement_rate is derived as engaged_sessions/sessions (GA4 native formula)
    because ga4_organic_landing_pages does not expose it directly.

    Results are sorted by opportunity_score descending, truncated to `limit`.
    hostname and country narrow the GA4 query to a specific host or country.
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
            hostname=hostname,
            country=country,
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
            params={"site": site, "days": days, "limit": limit, "property_id": property_id, "hostname": hostname, "country": country},
        )
    )


def page_health_score(
    site: str,
    url: str,
    property_id: str | None = None,
    hostname: str | None = None,
    country: str | None = None,
) -> str:
    """Compute a 0-100 health score for a single page by combining GSC, GA4, CrUX, and schema data.

    Each component contributes a portion of the total score (100 pts):
    - GSC (30 pts): indexing_state == "INDEXING_ALLOWED" -> 20 pts; verdict == "PASS" -> 10 pts
    - GA4 (25 pts): active_users > 0 -> 15 pts; engagement_rate > 0.4 -> 10 pts
    - CrUX (25 pts): LCP good -> 10 pts; INP good -> 8 pts; CLS good -> 7 pts
    - Schema (20 pts): schemas found -> 10 pts; no validation errors -> 10 pts

    GA4, CrUX, and Schema components are each wrapped in try/except RuntimeError so that
    missing credentials or insufficient data degrade the score gracefully. The final score
    is renormalized over available components: score = round((earned / max_available) * 100).
    If all components fail, returns score=0.

    property_id overrides GA4_PROPERTY_ID for multi-property setups.
    hostname and country are forwarded to GA4 for scoped queries.
    """
    # --- GSC component (always attempted, no credential guard needed beyond initial call) ---
    gsc_pts = 0
    gsc_available = True
    try:
        gsc_raw = json.loads(inspect_url(url=url, site=site))
        if gsc_raw.get("indexing_state") == "INDEXING_ALLOWED":
            gsc_pts += 20
        if gsc_raw.get("verdict") == "PASS":
            gsc_pts += 10
    except RuntimeError:
        gsc_available = False

    # --- GA4 component ---
    ga4_pts = 0
    ga4_available = True
    try:
        ga4_raw = json.loads(
            ga4_page_performance(
                start_date="30daysAgo",
                end_date="today",
                property_id=property_id,
                page_path=url,
                hostname=hostname,
                country=country,
            )
        )
        pages = ga4_raw.get("pages", [])
        total_active_users = sum(p.get("active_users", 0) for p in pages)
        avg_engagement_rate = (
            sum(p.get("engagement_rate", 0.0) for p in pages) / len(pages)
            if pages else 0.0
        )
        if total_active_users > 0:
            ga4_pts += 15
        if avg_engagement_rate > 0.4:
            ga4_pts += 10
    except RuntimeError:
        ga4_available = False

    # --- CrUX component ---
    crux_pts = 0
    crux_available = True
    try:
        crux_raw = json.loads(crux_page_vitals(url=url))
        if crux_raw.get("verdict") == "not_enough_data":
            crux_available = False
        else:
            metrics = crux_raw.get("metrics", {})
            lcp = metrics.get("largest_contentful_paint", {})
            inp = metrics.get("interaction_to_next_paint", {})
            cls = metrics.get("cumulative_layout_shift", {})
            if lcp.get("rating") == "good":
                crux_pts += 10
            if inp.get("rating") == "good":
                crux_pts += 8
            if cls.get("rating") == "good":
                crux_pts += 7
    except RuntimeError:
        crux_available = False

    # --- Schema component ---
    schema_pts = 0
    schema_available = True
    try:
        schema_raw = json.loads(schema_validate(url=url))
        schemas = schema_raw.get("schemas", [])
        schemas_found = schema_raw.get("schemas_detected", 0)
        if schemas_found > 0:
            schema_pts += 10
        errors = [f for s in schemas for f in s.get("missing_required_fields", [])]
        if len(errors) == 0:
            schema_pts += 10
    except RuntimeError:
        schema_available = False

    # --- Renormalization ---
    _MAX = {"gsc": 30, "ga4": 25, "crux": 25, "schema": 20}
    _available = {
        "gsc": gsc_available,
        "ga4": ga4_available,
        "crux": crux_available,
        "schema": schema_available,
    }
    _earned = {
        "gsc": gsc_pts,
        "ga4": ga4_pts,
        "crux": crux_pts,
        "schema": schema_pts,
    }

    max_available = sum(v for k, v in _MAX.items() if _available[k])
    earned = sum(v for k, v in _earned.items() if _available[k])

    if max_available == 0:
        score = 0
    else:
        score = round((earned / max_available) * 100)

    return json.dumps(
        with_meta(
            {
                "url": url,
                "score": score,
                "components": {
                    "gsc": {"score": gsc_pts, "max": 30, "available": gsc_available},
                    "ga4": {"score": ga4_pts, "max": 25, "available": ga4_available},
                    "crux": {"score": crux_pts, "max": 25, "available": crux_available},
                    "schema": {"score": schema_pts, "max": 20, "available": schema_available},
                },
            },
            tool="page_health_score",
            params={"site": site, "url": url, "property_id": property_id},
        )
    )
