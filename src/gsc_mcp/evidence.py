"""Reviewed field-level provenance. Tiers describe methods, not probabilities.

Only declared paths are visited. A collection descriptor covers membership,
never implicitly the metrics or arbitrary content below that collection.
"""

from __future__ import annotations

TIERS = {"measured": "observed", "derived": "calculated", "rule": "heuristic", None: "unavailable"}


def validate_descriptor(record: dict) -> None:
    """Reserve model attribution until a calibrated backend contract is defined."""
    basis = record.get("basis")
    if basis == "model":
        raise ValueError("model evidence requires a supported backend/version and calibration contract")
    if basis not in TIERS or record.get("confidence_tier") != TIERS[basis]:
        raise ValueError("Invalid evidence basis/tier pair")
    if not record.get("scope") or "confidence" in record:
        raise ValueError("Evidence needs scope and cannot manufacture numeric confidence")


# Every registered tool is reviewed explicitly; additions fail the registry test.
INVENTORY: dict[str, dict] = {}
_PATHS: dict[str, list[tuple[str, str | None, str]]] = {}


def _inventory(names: str, applicability: str, reason: str) -> None:
    for name in names.split():
        if name in INVENTORY:
            raise ValueError(f"Duplicate evidence inventory entry: {name}")
        INVENTORY[name] = {"applicability": applicability, "reason": reason}
        _PATHS[name] = []


_inventory("""
inspect_url batch_url_inspection check_indexing_issues analytics_anomalies
quick_wins traffic_drops seo_striking_distance seo_cannibalization seo_lost_queries
check_alerts parasite_risk prune_candidates traffic_health_check page_analysis
content_brief page_health_score compare_search_engines crux_page_vitals crux_history
crux_lcp_subparts pagespeed_audit schema_validate content_quality hreflang_audit
page_technical_audit preload_audit heading_audit ai_visibility_audit gbp_deprecation_lint
internal_links_audit link_equity_map sitemap_audit drift_compare drift_history
bing_feeds_list bing_feed_details bing_crawl_issues bing_url_info ga4_ai_referrals
""", "fields", "Explicit observation, calculation or local conclusion paths; scope is per field")
_inventory("ga4_funnel", "error_only", "Funnel metrics have no quality verdict; INVALID_STEPS is unavailable")
_inventory("""
submit_url submit_batch submit_sitemap sitemaps_delete schema_generate drift_baseline
bing_url_submit bing_urls_submit_batch bing_feed_submit bing_feed_remove indexnow_submit
""", "operational", "Protocol/generation/persistence status is not SEO success or permission to act")
_inventory("""
get_capabilities list_properties get_site_details get_search_analytics get_performance_overview
compare_search_periods get_search_by_page_query get_advanced_search_analytics discover_performance
news_performance search_type_breakdown ai_overviews_impact list_sitemaps sitemaps_get
ga4_organic_landing_pages ga4_traffic_sources ga4_page_performance ga4_realtime ga4_user_behavior
ga4_conversion_funnel bing_sites_list bing_query_stats bing_page_stats bing_page_query_stats
bing_rank_traffic_stats bing_crawl_stats bing_crawl_settings_get bing_url_traffic
bing_url_submission_quota bing_link_counts bing_url_links
""", "data_only", "Metrics/configuration/provider operational snapshots; no quality verdict or score")


def _add(tool: str, basis: str | None, scope: str, *paths: str) -> None:
    for path in paths:
        _PATHS[tool].append((path, basis, scope))


_INSPECTION = ("verdict", "robots_txt_state", "indexing_state", "page_fetch_state", "coverage_state")
for tool, prefix in (("inspect_url", ""), ("batch_url_inspection", "/results/*"), ("check_indexing_issues", "/issues/*")):
    _add(tool, "measured", "Google URL Inspection provider observation for this URL, not all-engine/current-live truth",
         *(f"{prefix}/{key}" for key in _INSPECTION))
    _add(tool, "rule", "Local PASS/robots/fetch/canonical category rules over returned inspection fields",
         f"{prefix}/category")
_add("check_indexing_issues", "derived", "Counts of local categories over only the supplied URL sample", "/summary")
_add("analytics_anomalies", "derived", "Population mean/stddev over returned days; z=(clicks-mean)/stddev rounded to 2 decimals",
     "/mean_daily_clicks", "/std_daily_clicks", "/anomalies/*/z_score")
_add("analytics_anomalies", "rule", "Selection abs(z)>caller threshold; type from sign, no probability or causal inference",
     "/anomalies", "/anomalies/*/type")
_add("quick_wins", "rule", "Local CTR benchmark by clamped rounded position 4..15 and impression floor; expected=round(benchmark*impressions), score=round((benchmark-CTR)*impressions); assumed opportunity, not measured gain",
     "/opportunities", "/opportunities/*/benchmark_ctr", "/opportunities/*/expected_clicks_at_benchmark", "/opportunities/*/opportunity_score")
_add("traffic_drops", "rule", "Negative-click selection; position delta>2 then ranking_loss, CTR<previous*0.7 then ctr_collapse, else demand_decline fallback; not proof of causality; windows have no reporting lag",
     "/drops", "/drops/*/diagnosis")
_add("traffic_drops", "derived", "Current minus previous metric for queries in both returned periods", "/drops/*/clicks_delta", "/drops/*/impressions_delta")
_add("seo_striking_distance", "rule", "Membership only: position 8..15 and impression floor; ordered by impressions", "/queries")
_add("seo_cannibalization", "rule", "Membership only: multiple returned pages, impression floor and conflict score>0.1; not proof of harmful cannibalization", "/conflicts")
_add("seo_cannibalization", "derived", "1-sum((page_clicks/total_clicks)^2) over returned query-page rows", "/conflicts/*/conflict_score")
_add("seo_lost_queries", "rule", "Membership only: prior clicks>=5 and drop>=80%; absent current rows are zero-filled, not observed zeros", "/lost_queries")
_add("seo_lost_queries", "derived", "(previous-current)/previous; absent current rows zero-filled; windows have no reporting lag", "/lost_queries/*/drop_pct")
_add("check_alerts", "rule", "Membership/classification/recommendation: clicks share>0.5 or position>10 and impressions>5000 over returned rows",
     "/alerts", "/alerts/*/type", "/alerts/*/severity", "/alerts/*/message")
_add("parasite_risk", "rule", "URL path/query regex rules and maximum matched risk; no fetched content or measured policy violation", "/results/*/risk", "/site_risk", "/verdict")
_add("prune_candidates", "rule", "Returned rows only, bounded by max_pages: clicks>0, else impressions>=10, else impressions>0, else zero; actions never authorize deletion",
     "/verdict", "/guard_rail", *(f"/{key}{suffix}" for key in ("has_traffic", "impressions_no_clicks", "low_impressions", "zero_impressions") for suffix in ("", "/*/action")))
_add("traffic_health_check", "derived", "Sum of metrics in returned source rows; empty/unknown reports are not measured zeros", "/total_gsc_clicks", "/total_ga4_sessions")
_add("traffic_health_check", "derived", "GA4 organic sessions/GSC clicks over eligible aligned reported calendar dates; sessions and clicks differ; source time boundaries and property mapping unverified", "/ratio")
_add("traffic_health_check", "rule", "Local ratio thresholds <0.6 tracking_gap, >1.3 filter_issue, else healthy; not a tracking diagnosis", "/status")
_add("traffic_health_check", "rule", "Local source availability/window/filter/coverage gates; does not establish property mapping or source time-zone equality", "/comparison/comparable", "/source_data/*/availability")
_add("page_analysis", "rule", "Priority weighting log10(impressions+1)*10 + engagement_rate*100 + log10(conversions+1)*20; not measured impact", "/pages/*/opportunity_score")
_add("content_brief", "rule", "First query of clicks-descending returned rows; question membership from fixed EN/FR leading tokens/prefixes", "/current_focus", "/question_queries")
_add("page_health_score", "rule", "Local GSC 20+10, GA4 15+10, CrUX 10+8+7, schema 10+10; round(earned/max_available*100), renormalized over available components only, not complete health", "/score", "/components/*/score")
_add("compare_search_engines", "rule", "Both provider windows exact and same nonmissing observed start/end; does not equate provider measurement semantics", "/windows_comparable", "/totals/windows_comparable", "/rows/*/windows_comparable")
_add("compare_search_engines", "derived", "Bing minus Google only for matching exact windows and present pairs", "/totals/click_delta", "/totals/impression_delta", "/rows/*/click_delta", "/rows/*/impression_delta")
_add("crux_page_vitals", "measured", "CrUX provider p75 field observation for this URL/form factor and collection window", "/metrics/*/p75")
_add("crux_page_vitals", "rule", "Local metric-specific good/poor threshold comparisons, not provider scoring", "/metrics/*/rating")
_add("crux_history", "measured", "Historical CrUX provider p75 for each returned collection period", "/history/*/p75")
_add("crux_lcp_subparts", "measured", "CrUX provider p75 for requested URL/form factor and collection window", "/lcp_p75_ms", "/subparts/ttfb_ms", "/subparts/resource_load_delay_ms", "/subparts/resource_load_duration_ms", "/subparts/render_delay_ms")
_add("crux_lcp_subparts", "derived", "Argmax of available subpart p75 values; not an observed root cause", "/subparts/dominant_phase")
_add("crux_lcp_subparts", "rule", "Local LCP good/poor thresholds 2500/4000 ms", "/lcp_rating", "/verdict")
_add("pagespeed_audit", "rule", "Lighthouse provider scoring algorithm; performance score rescaled/rounded to percent, not a physical measurement or field p75", "/performance_score", "/cwv/*/score", "/top_opportunities/*/score")
_add("pagespeed_audit", "measured", "Lighthouse reported lab audit numeric value for this run, not CrUX field p75", "/cwv/*/numeric_value")
_add("pagespeed_audit", "rule", "Local 90/50 performance thresholds; opportunity membership score<0.9, sorted ascending, first 3", "/verdict", "/top_opportunities")
_add("schema_validate", "rule", "Local required/recommended field-presence/deprecation maps and URL-pattern recommendations; not full Schema.org validity or Google eligibility; null deprecation means no local map match",
     "/verdict", "/schemas", "/schemas/*/valid", "/schemas/*/missing_required_fields", "/schemas/*/missing_recommended_fields", "/schemas/*/deprecated_rich_result", "/recommendations", "/validation_scope")
_add("schema_validate", None, "Google rich-result eligibility is explicitly not assessed", "/google_rich_result_eligibility")
_add("schema_validate", "rule", "Known SiteGround resource path plus human-verification prompt; heuristic interstitial detection, requested page unavailable", "/challenge")
_add("schema_validate", "measured", "Received HTTP response code only, not requested-page accessibility", "/http_status")
_add("content_quality", "rule", "Fixed phrase-list filler, regex entity/number density proxy, local weighting .35/.35/.20/.10 and clipping; thin<300 tokens else good>=60; not measured quality or AI authorship", "/filler_score", "/information_density", "/overall_quality", "/flags", "/verdict")
_add("content_quality", "derived", "round(100*distinct repeated bigrams/distinct bigrams), short-text fallback zero; quality interpretation remains heuristic", "/repetition_score")
_AUDITS = {
    "hreflang_audit": "Static lang-code, self-reference/x-default and cluster checks; no_hreflang is a local observation-based conclusion",
    "page_technical_audit": "Local title/description length, canonical/robots/security-header rules, redirect status membership and stdlib robots parser; no browser runtime validation",
    "preload_audit": "Local speculation/preload/cache-control rules; not_implemented is a valid local verdict; no browser runtime bfcache validation",
    "heading_audit": "H1/hierarchy, empty-heading vocabulary and word/H2 thresholds; descriptive ratio uses this rule vocabulary",
    "internal_links_audit": "Membership/classification only: local link-zone/anchor rules over one fetched page; not proof of lost search equity",
    "link_equity_map": "Membership/classification only: returned GSC rows and bounded crawl; positions 11..20/no body inbound, impressions>0/no body inbound, hubs by outbound count; not whole-site orphan guarantee",
    "gbp_deprecation_lint": "Local regex deprecation catalogue over fetched HTML, not live verification of third-party service status",
}
for tool, scope in _AUDITS.items():
    _add(tool, "rule", scope, "/verdict", "/issues", "/issues/*/severity")
_add("page_technical_audit", "rule", _AUDITS["page_technical_audit"], "/findings/redirected", "/findings/robots_txt_blocks_googlebot")
_add("page_technical_audit", "measured", "HTTP response status code received for this request", "/findings/status_code")
_add("preload_audit", "rule", _AUDITS["preload_audit"], "/prerender_deprecated", "/bfcache_no_store")
_add("heading_audit", "rule", _AUDITS["heading_audit"], "/empty_headings", "/descriptive_ratio")
_add("heading_audit", "derived", "Token Jaccard/title-H1 normalized equality, word count/H2 count, and heading level differences over extracted HTML", "/title_h1_overlap", "/words_per_h2", "/title_h1_identical", "/hierarchy_jumps")
_add("internal_links_audit", "rule", _AUDITS["internal_links_audit"], "/generic_anchors", "/empty_anchors", "/nofollow_internal", "/footer_only_targets")
_add("link_equity_map", "rule", _AUDITS["link_equity_map"], "/underlinked_striking_distance", "/orphan_candidates", "/footer_only_targets", "/hub_pages")
_add("ai_visibility_audit", "rule", "Stdlib RobotFileParser per crawler and aggregate allowed counts; no proof of AI citations or actual access", "/crawlers/*/allowed", "/verdict")
_add("sitemap_audit", "rule", "Parsed XML empty or returned-row missing ratio>0.2; 90-day search visibility only, never indexing; partial child-fetch coverage is incomplete", "/verdict", "/visibility_verdict")
_add("sitemap_audit", "derived", "URL-normalized intersection/difference of parsed sitemap URLs and returned GSC search rows; partial child-fetch coverage may be incomplete", "/urls_with_search_data", "/urls_without_search_data", "/urls_in_gsc", "/urls_missing_from_gsc")
_add("drift_compare", "rule", "17 local comparison rules over observed baseline/current snapshots; severity/messages do not prove predicted ranking effects", *(f"/{collection}/*/{key}" for collection in ("triggered_findings", "all_findings") for key in ("severity", "triggered", "message")))
_add("drift_compare", "derived", "Counts of returned local comparison-rule results, not measured impact", "/summary/*")
_add("drift_history", "derived", "Persisted counts of historical rule severities, not fresh checks", "/comparisons/*/critical", "/comparisons/*/warning", "/comparisons/*/info")
for tool in ("bing_feeds_list", "bing_feed_details"):
    _add(tool, "measured", "Bing provider feed status, not URL indexing", "/feeds/*/status")
_add("bing_crawl_issues", "rule", "Local bitmask flag-to-name mapping; unverified runtime contract remains unchanged", "/issues/*/issue_types")
_add("bing_crawl_issues", "derived", "Bitmask remainder after known flags; unverified runtime contract remains unchanged", "/issues/*/unknown_issue_bits")
_add("bing_url_info", "measured", "Bing reported HTTP status; parser-default zero is unavailable", "/http_status")
_add("bing_url_info", None, "Parser cannot distinguish absent IsPage from false; ambiguous provider provenance", "/is_page")
_add("ga4_ai_referrals", "rule", "Exact dated source-label catalogue and candidate matching rules; classification does not authenticate an AI client or establish causal citation", "/rows/*/classification", "/availability")
_add("ga4_ai_referrals", "derived", "Share of returned confirmed source-label sessions only when report coverage is complete and unfiltered by loss/sampling/thresholding", "/ai_session_share")
_add("ga4_ai_referrals", None, "Comparison is explicitly not requested", "/comparison/availability")
_add("indexnow_submit", "measured", "Received IndexNow HTTP code, not indexing or crawling", "/status_code")
_add("indexnow_submit", "rule", "HTTP protocol mapping only: 200 received/key verified, 202 received/key pending; no indexing proof or write authorization", "/status", "/verdict", "/key_validation")
for tool in ("page_technical_audit", "heading_audit", "internal_links_audit", "schema_validate"):
    _add(tool, "rule", "Narrow deterministic FR/EN instruction patterns in untrusted HTML; may miss or falsely flag prose; absence never establishes trust", "/untrusted_content/flagged", "/untrusted_content/signals", "/untrusted_content/signals/*")

# Error paths are explicit; successful operational statuses stay unannotated.
for tool in INVENTORY:
    _add(tool, None, "Tool error prevents an evidence interpretation; original error value is retained", "/error")
for tool in ("traffic_drops", "seo_cannibalization", "seo_lost_queries", "check_alerts", "crux_page_vitals", "crux_history", "drift_compare", "drift_history", "drift_baseline", "schema_generate"):
    _add(tool, None, "Unavailable/unsupported/error result; no successful SEO verdict is attributed here", "/verdict")
for tool in ("bing_url_submit", "bing_urls_submit_batch", "bing_feed_submit", "bing_feed_remove"):
    _add(tool, None, "Notification acceptance does not verify indexing; retained unverified sentinel", "/indexed")


def _expand(value, parts: list[str], path: tuple[str, ...] = (), parent=None):
    if not parts:
        yield path, value, parent
        return
    key, *tail = parts
    if key == "*":
        items = value.items() if isinstance(value, dict) else enumerate(value) if isinstance(value, list) else ()
        for child_key, child in items:
            yield from _expand(child, tail, (*path, str(child_key)), value)
    elif isinstance(value, dict) and key in value:
        yield from _expand(value[key], tail, (*path, key), value)


def _inspection_substantive(value) -> bool:
    return bool(value) and value != "UNKNOWN" and "UNSPECIFIED" not in str(value)


def _resolve(tool: str, path: tuple[str, ...], value, parent, data: dict, basis, scope):
    key = path[-1]
    null_is_rule = tool == "schema_validate" and key == "deprecated_rich_result"
    if value is None and not null_is_rule:
        return None, "Required evidence/value is null; original value retained"
    if tool in {"inspect_url", "batch_url_inspection", "check_indexing_issues"}:
        if key in _INSPECTION and not _inspection_substantive(value):
            return None, "Google inspection state is missing/unknown/unspecified"
        if key == "category" and (value == "unknown" or not any(
                _inspection_substantive(parent.get(k)) for k in (*_INSPECTION, "google_canonical", "user_canonical"))):
            return None, "Local category fallback has no substantive provider input"
    elif key == "verdict" and value in {"error", "fetch_error", "ssrf_blocked", "missing_key", "unsupported", "not_enough_data", "no_baseline", "no_data"}:
        return None, "Unavailable, unsupported or tool error result; original verdict retained"
    if tool == "seo_cannibalization" and key == "conflict_score" and parent.get("total_clicks") == 0:
        return "rule", "Zero-click fallback assumes uniform 1/n page shares; not measured click concentration"
    if tool == "page_health_score":
        if key == "score" and ((len(path) > 1 and parent.get("available") is not True)
                                or (len(path) == 1 and not any(c.get("available") is True for c in data.get("components", {}).values()))):
            return None, "Unavailable component/all components unavailable; legacy zero is not measured health"
    if tool in {"crux_page_vitals", "crux_lcp_subparts"} and key in {"rating", "lcp_rating"} and value == "unknown":
        return None, "No available p75 or applicable rating threshold"
    if tool == "ai_visibility_audit" and data.get("robots_txt_found") is not True:
        return None, "robots.txt unavailable; legacy allowed/open values are fallback assumptions"
    if tool == "bing_url_info" and key == "http_status" and value == 0:
        return None, "Parser-default zero cannot establish provider HTTP status"
    if tool == "schema_validate" and key == "validation_scope" and value == "not_assessed":
        return None, "Requested page schema assessment unavailable on challenge response"
    if tool == "sitemap_audit" and data.get("verdict") == "fetch_error":
        return None, "Root sitemap fetch unavailable; retained count zeros are placeholders"
    if tool == "traffic_health_check" and key == "status" and data.get("ratio") is None:
        return None, "Comparison unavailable due to source/window/filter/coverage/zero denominator gate"
    if tool == "traffic_health_check" and key == "availability" and value != "measured":
        return None, "Source measurements are empty, unknown or unavailable"
    if tool == "ga4_ai_referrals" and key == "availability" and value in {"unavailable", "unknown", "empty"}:
        return None, "Source report lacks usable attributed observations"
    if tool == "drift_compare" and key in {"severity", "triggered", "message"}:
        rule, old, new = parent.get("rule"), parent.get("old_value"), parent.get("new_value")
        skipped = (rule == "perf_score_dropped"
                   or (rule == "h1_changed" and (not old or not new))
                   or (rule == "status_code_error" and (old is None or new is None)))
        if rule == "cwv_regressed":
            skipped = not (isinstance(old, dict) and isinstance(new, dict) and any(
                old.get(metric) is not None and new.get(metric) is not None and old[metric] > 0
                for metric in ("lcp_p75", "inp_p75", "cls_p75")))
        if skipped:
            return None, "Comparison rule skipped because required comparable inputs are unavailable"
    if tool == "indexnow_submit" and key != "error" and data.get("status_code") is None:
        return None, "No received protocol response; timeout/transport/no-valid-URLs is unavailable"
    return basis, scope


def evidence_for(data: dict, tool: str) -> dict:
    """Return an additive envelope without mutating data or traversing _meta."""
    if tool not in INVENTORY:
        return {"version": 1, "fields": {}, "inventory_status": "unregistered"}
    fields = {}
    for pattern, basis, scope in _PATHS[tool]:
        for path, value, parent in _expand(data, pattern.split("/")[1:]):
            if tool == "schema_generate" and path == ("verdict",) and value == "generated":
                continue
            resolved_basis, resolved_scope = _resolve(tool, path, value, parent, data, basis, scope)
            record = {"basis": resolved_basis, "confidence_tier": TIERS.get(resolved_basis), "scope": resolved_scope}
            validate_descriptor(record)
            pointer = "/" + "/".join(key.replace("~", "~0").replace("/", "~1") for key in path)
            fields[pointer] = record
    return {"version": 1, "fields": fields}
