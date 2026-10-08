"""Cross-platform tools combining GSC and GA4 data.

Both tools call high-level functions from analytics.py and ga4.py, parse their
JSON output, then join on normalised URL paths. GSC returns absolute URLs;
GA4 returns paths (sometimes with query strings). _normalize_url strips both
down to bare paths so the join is reliable.

traffic_health_check aligns the requested calendar dates to the GSC window.
Source time boundaries and the GSC-to-GA4 property mapping remain unverified.
Other combined reports still use independent source windows.
"""

import json
import math
from datetime import date
from urllib.parse import urlsplit

from gsc_mcp.tools.analytics import _date_range, get_search_analytics
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


def _report_sources(site: str, ga4_response: dict) -> dict:
    """Carry the child's source identity; absent provenance remains unknown."""
    ga4_source = ga4_response.get("_meta", {}).get("sources", {}).get("ga4")
    return {
        "gsc": {"site": site},
        "ga4": ga4_source if ga4_source is not None else {"property": None},
    }


def _traffic_measurement(data: dict, rows_key: str, metric: str) -> tuple[str, int | float | None]:
    """An empty or malformed report is not a measured zero."""
    rows = data.get(rows_key)
    if not isinstance(rows, list):
        return "unknown", None
    if not rows:
        return "empty", None
    values = [row.get(metric) if isinstance(row, dict) else None for row in rows]
    if any(isinstance(value, bool) or not isinstance(value, (int, float))
           or not math.isfinite(value) or value < 0 for value in values):
        return "unknown", None
    return "measured", sum(values)


def _traffic_error(exc: Exception) -> dict:
    # Auth helpers use RuntimeError for missing credentials/configuration.
    configuration_error = isinstance(exc, RuntimeError) and str(exc).startswith(
        ("No GSC config", "No GA4 config", "No credentials:", "OAuth browser flow disabled")
    )
    return {"availability": "unavailable", "reason": "configuration_error"
            if configuration_error else "upstream_error", "error_type": type(exc).__name__}


def _traffic_window(window: object) -> dict | None:
    """Accept ordered concrete ISO dates, never GA4 relative date strings."""
    if not isinstance(window, dict):
        return None
    start, end = window.get("start"), window.get("end")
    if not isinstance(start, str) or not isinstance(end, str):
        return None
    try:
        if (date.fromisoformat(start).isoformat() == start
                and date.fromisoformat(end).isoformat() == end and start <= end):
            return {"start": start, "end": end}
    except ValueError:
        pass
    return None


def traffic_health_check(
    site: str,
    days: int = 28,
    property_id: str | None = None,
    hostname: str | None = None,
    country: str | None = None,
) -> str:
    """Compare Google clicks and GA4 organic sessions over matching calendar dates.

    Ratios are heuristics, not proof of a tracking fault: sessions and clicks differ,
    GA4 organic traffic can include other search engines, and source time boundaries
    and property mapping are unverified. Empty reports yield null totals; explicit
    zero rows remain zero. Missing sources, differing windows, incompatible filters,
    or unverified/incomplete GA4 coverage prevent a numeric comparison.
    """
    if isinstance(days, bool) or not isinstance(days, int) or days < 1:
        raise ValueError("days must be a positive integer")
    start, end = _date_range(days)
    date_range = {"start": start, "end": end}
    gsc_data, ga_data = {}, {}
    gsc_state = {"site": site, "reported_site": None, "filters": {}, "time_zone": None,
                 "observed_window": None, "reported_window": None, "coverage": None}
    ga_state = {"property": None, "filters": {"hostname": hostname, "country": country, "session_medium": "organic"},
                "time_zone": None, "observed_window": None, "reported_window": None, "coverage": None}
    total_gsc_clicks = total_ga4_sessions = None
    try:
        gsc_data = json.loads(get_search_analytics(site, days, dimensions=[]))
        reported = gsc_data.get("date_range")
        resolved_window = _traffic_window(reported)
        if resolved_window:
            date_range = resolved_window
        gsc_state["reported_window"] = reported
        gsc_state["reported_site"] = gsc_data.get("site")
        gsc_state["availability"], total_gsc_clicks = _traffic_measurement(gsc_data, "rows", "clicks")
        # dimensions=[] requests a single aggregate, not a page/query sample.
        rows = gsc_data.get("rows")
        gsc_state["coverage"] = {"complete": isinstance(rows, list) and len(rows) == 1}
    except Exception as exc:
        gsc_state.update(_traffic_error(exc))
    gsc_state["requested_window"] = date_range
    ga_state["requested_window"] = date_range
    try:
        ga_data = json.loads(ga4_organic_landing_pages(
            start_date=date_range["start"],
            end_date=date_range["end"],
            limit=10000,
            property_id=property_id,
            hostname=hostname,
            country=country,
        ))
        ga_state["reported_window"] = {"start": ga_data.get("start_date"), "end": ga_data.get("end_date")}
        ga_state["availability"], total_ga4_sessions = _traffic_measurement(ga_data, "pages", "sessions")
        ga_state["coverage"] = ga_data.get("coverage")
        ga_state["time_zone"] = ga_data.get("time_zone")
        ga_state["property"] = _report_sources(site, ga_data)["ga4"].get("property")
    except Exception as exc:
        ga_state.update(_traffic_error(exc))

    reasons = []
    ratio = None
    if any(state["availability"] == "unavailable" for state in (gsc_state, ga_state)):
        status = "source_unavailable"
        reasons.append("source_unavailable")
    elif any(state["availability"] != "measured" for state in (gsc_state, ga_state)):
        status = "insufficient_data"
        reasons.append("empty_or_unknown_source")
    elif gsc_state.get("reported_window") != date_range or ga_state.get("reported_window") != date_range:
        status = "window_mismatch"
        reasons.append("reported_windows_differ_or_unknown")
    elif gsc_state["reported_site"] != site or country or (hostname and (site.startswith("sc-domain:") or urlsplit(site).hostname != hostname
                                  or urlsplit(site).path not in ("", "/"))):
        status = "incompatible_scope"
        reasons.append("ga4_filters_do_not_match_unfiltered_gsc_scope")
    elif (gsc_state["coverage"]["complete"] is not True
          or not isinstance(ga_state.get("coverage"), dict)
          or ga_state["coverage"].get("complete") is not True
          or ga_state["coverage"].get("metric_restrictions") != []
          or any(ga_state["coverage"].get(flag) is not False
                 for flag in ("data_loss_from_other_row", "sampling", "subject_to_thresholding"))):
        status = "incomplete_coverage"
        reasons.append("source_coverage_incomplete_or_unknown")
    elif total_gsc_clicks == 0:
        status = "no_gsc_data"
        reasons.append("zero_gsc_clicks")
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
                "source_data": {"gsc": gsc_state, "ga4": ga_state},
                "comparison": {"comparable": ratio is not None, "reasons": reasons,
                               "calendar_alignment": "unknown", "property_mapping": "unverified"},
                "note": "Requested dates are aligned to GSC's lagged window. Source time boundaries and property mapping are unverified. Google clicks and all-engine organic sessions differ; ratio statuses are heuristics, not tracking diagnoses.",
            },
            tool="traffic_health_check",
            params={"site": site, "days": days, "property_id": property_id, "hostname": hostname, "country": country},
            sources=_report_sources(site, ga_data),
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
            sources=_report_sources(site, ga_data),
        )
    )


def content_brief(
    site: str,
    page_url: str,
    days: int = 90,
    property_id: str | None = None,
) -> str:
    """Gather SEO content intelligence for a single page: top queries, question queries, and GA4 engagement.

    Step 1 — GSC: fetches search analytics with dimensions ["query", "page"], filters rows
    to the target page (via _normalize_url), sorts by clicks descending, and returns the top 20.

    Step 2 — GA4: calls ga4_page_performance for the same page to get active_users and
    engagement_rate. Wrapped in try/except RuntimeError; returns None if GA4 credentials
    are missing or the property is not configured.

    Question classification: queries whose first word (lowercased) is one of
    who/what/when/where/why/how.

    Useful for brief-writing, content refreshes, and intent analysis.
    """
    gsc_data = json.loads(get_search_analytics(site, days, dimensions=["query", "page"]))
    norm_target = _normalize_url(page_url)

    filtered = [
        row for row in gsc_data.get("rows", [])
        if _normalize_url(row["page"]) == norm_target
    ]
    filtered.sort(key=lambda r: r["clicks"], reverse=True)
    top_queries = [
        {
            "query": row["query"],
            "clicks": row["clicks"],
            "impressions": row["impressions"],
            "position": row["position"],
        }
        for row in filtered[:20]
    ]

    # English question intent is carried by a single leading word; French needs both
    # a first-token set and multi-word prefixes ("est-ce que"). Accent-less variants
    # are included because search queries are routinely typed without accents.
    question_words = {
        "who", "what", "when", "where", "why", "how", "which",
        "comment", "pourquoi", "quand", "où", "ou", "qui", "quoi",
        "quel", "quelle", "quels", "quelles", "combien",
    }
    question_prefixes = ("est-ce que", "est ce que", "qu'est-ce", "qu est ce")
    question_queries = []
    for row in filtered:
        q_lower = row["query"].lower()
        words = q_lower.split()
        if (words and words[0] in question_words) or q_lower.startswith(question_prefixes):
            question_queries.append({"query": row["query"], "clicks": row["clicks"]})

    ga4_result = None
    ga4_raw = {}
    try:
        ga4_raw = json.loads(
            ga4_page_performance(
                start_date=f"{days}daysAgo",
                end_date="today",
                property_id=property_id,
                page_path=norm_target,
            )
        )
        pages = ga4_raw.get("pages", [])
        if pages:
            first = pages[0]
            ga4_result = {
                "active_users": first.get("active_users"),
                "engagement_rate": first.get("engagement_rate"),
            }
    except RuntimeError:
        ga4_result = None

    return json.dumps(
        with_meta(
            {
                "page_url": page_url,
                "days": days,
                "current_focus": top_queries[0]["query"] if top_queries else None,
                "top_queries": top_queries,
                "question_queries": question_queries,
                "ga4": ga4_result,
            },
            tool="content_brief",
            params={"site": site, "page_url": page_url, "days": days, "property_id": property_id},
            sources=_report_sources(site, ga4_raw),
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
    ga4_raw = {}
    try:
        ga4_raw = json.loads(
            ga4_page_performance(
                start_date="30daysAgo",
                end_date="today",
                property_id=property_id,
                page_path=_normalize_url(url),
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
        schemas_found = schema_raw.get("schemas_detected")
        if (schema_raw.get("verdict") in ("challenge_page", "fetch_error")
                or type(schemas_found) is not int or schemas_found < 0 or not isinstance(schemas, list)):
            schema_available = False
        elif schemas_found > 0:
            schema_pts += 10
            errors = [f for s in schemas for f in s.get("missing_required_fields", [])]
            if len(errors) == 0:
                schema_pts += 10
    except RuntimeError:
        schema_available = False

    # --- Renormalization ---
    max_available = (30 if gsc_available else 0) + (25 if ga4_available else 0) + (25 if crux_available else 0) + (20 if schema_available else 0)
    earned = (gsc_pts if gsc_available else 0) + (ga4_pts if ga4_available else 0) + (crux_pts if crux_available else 0) + (schema_pts if schema_available else 0)

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
            params={"site": site, "url": url, "property_id": property_id, "hostname": hostname, "country": country},
            sources=_report_sources(site, ga4_raw),
        )
    )
