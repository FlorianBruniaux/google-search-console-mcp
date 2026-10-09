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
search_change_breakdown seo_change_impact rewrite_fidelity_check inspect_url batch_url_inspection check_indexing_issues analytics_anomalies
quick_wins traffic_drops seo_striking_distance seo_cannibalization seo_lost_queries
check_alerts parasite_risk prune_candidates traffic_health_check page_analysis ai_overviews_impact
content_brief page_health_score compare_search_engines crux_page_vitals crux_history
crux_lcp_subparts pagespeed_audit schema_validate content_quality editorial_audit hreflang_audit
page_technical_audit preload_audit heading_audit ai_visibility_audit gbp_deprecation_lint
internal_links_audit link_targets_audit link_equity_map sitemap_audit drift_compare drift_history
bing_feeds_list bing_feed_details bing_crawl_issues bing_url_info ga4_ai_referrals
bing_query_stats bing_page_stats bing_page_query_stats bing_rank_traffic_stats
""", "fields", "Explicit observation, calculation or local conclusion paths; scope is per field")
_inventory("ga4_funnel", "error_only", "Funnel metrics have no quality verdict; INVALID_STEPS is unavailable")
_inventory("""
submit_url submit_batch submit_sitemap sitemaps_delete schema_generate drift_baseline
bing_url_submit bing_urls_submit_batch bing_feed_submit bing_feed_remove indexnow_submit
""", "operational", "Protocol/generation/persistence status is not SEO success or permission to act")
_inventory("""
get_capabilities list_properties get_site_details get_search_analytics get_performance_overview
compare_search_periods get_search_by_page_query get_advanced_search_analytics discover_performance
news_performance search_type_breakdown list_sitemaps sitemaps_get
ga4_organic_landing_pages ga4_traffic_sources ga4_page_performance ga4_realtime ga4_user_behavior
ga4_conversion_funnel bing_sites_list bing_crawl_stats bing_crawl_settings_get bing_url_traffic
bing_url_submission_quota bing_link_counts bing_url_links
""", "data_only", "Metrics/configuration/provider operational snapshots; no quality verdict or score")


def _add(tool: str, basis: str | None, scope: str, *paths: str) -> None:
    for path in paths:
        _PATHS[tool].append((path, basis, scope))


# Generic appearance discovery never identifies AI exposure or causal effect.
_add("ai_overviews_impact", "measured", "Google returned generic Web search-appearance label/metric for the requested window; not an AI-specific observation",
     "/rows/*/searchAppearance", "/rows/*/clicks", "/rows/*/impressions", "/rows/*/ctr", "/rows/*/position", "/http_status")
_add("ai_overviews_impact", "derived", "Count of displayed generic appearance rows after impression sorting and limit; not a count of AI-exposed queries", "/count")
_add("ai_overviews_impact", "derived", "Counts of retrieved rows and partial rows; not complete provider coverage", "/coverage/retrieved_rows", "/coverage/partial_rows")
_add("ai_overviews_impact", "rule", "Explicit source field validation or disclosure of requested scope; no AI mapping or coverage guarantee",
     "/metric_origin", "/coverage/display_truncated", "/coverage/all_source_rows_guaranteed", "/rows/*/dimension_status", "/rows/*/unavailable_metrics/*")
_add("ai_overviews_impact", None, "No dated coverage probe establishes an observed window", "/coverage/observed_window")
_add("ai_overviews_impact", "rule", "Local generic source-result classification: observed/empty response, invalid or unsupported request (400), access denied (403); no property AI capability inference", "/source_status", "/error_meaning")
_add("ai_overviews_impact", None, "AI exposure has no verified provider appearance mapping or live observation; generic traffic cannot identify AI presence, absence or causal effect", "/ai_exposure/status", "/ai_exposure/verification")

# Search breakdown: collections describe selection only; metrics are explicit leaves.
for prefix in ("/baseline_totals/*/metrics", "/breakdowns/*/matched/*/baseline",
               "/breakdowns/*/matched/*/comparison", "/breakdowns/*/baseline_only/*/baseline",
               "/breakdowns/*/comparison_only/*/comparison"):
    _add("search_change_breakdown", "measured", "Google provider row/aggregate metric for requested filtered window only; position is raw provider row average",
         *(f"{prefix}/{metric}" for metric in ("clicks", "impressions", "position")))
    _add("search_change_breakdown", "derived", "CTR=clicks/impressions for present counts and positive impressions; no provider CTR fallback", f"{prefix}/ctr")
_add("search_change_breakdown", "derived", "Comparison minus baseline on same known aggregation; CTR change in percentage points; retrieved rows only",
     "/baseline_delta/*", "/breakdowns/*/matched/*/delta/*", "/breakdowns/*/matched_delta/*")
_add("search_change_breakdown", "derived", "Sum over retrieved valid per-period rows; not property totals; null when rows are empty or any required metric is missing",
     "/breakdowns/*/observed_sums/*/*")
_add("search_change_breakdown", "derived", "Reported period aggregate minus retrieved period row sum, only on compatible known aggregation; descriptive residual, not a cause",
     "/breakdowns/*/reconciliation/baseline_residual/*", "/breakdowns/*/reconciliation/comparison_residual/*")
_add("search_change_breakdown", "derived", "Reported total change minus summed matched-row changes, only on compatible known aggregation; descriptive residual, not a cause",
     "/breakdowns/*/reconciliation/total_delta_minus_matched_delta/*")
_add("search_change_breakdown", "rule", "Observed selection, source compatibility and bounded fetch/display gates; no causal attribution or complete source guarantee",
     "/baseline_comparison/comparable", "/baseline_comparison/reason", "/breakdowns/*/comparison/comparable", "/breakdowns/*/comparison/reason",
     "/breakdowns/*/reconciliation/comparable", "/breakdowns/*/reconciliation/reason", "/breakdowns/*/reconciliation/overcoverage",
     "/breakdowns/*/matched", "/breakdowns/*/baseline_only", "/breakdowns/*/comparison_only",
     "/breakdowns/*/baseline_coverage/*", "/breakdowns/*/comparison_coverage/*", "/breakdowns/*/display_truncated",
     "/baseline_totals/*/availability", "/periods/*/coverage_probe_status", "/periods/*/incompleteness_status")
_add("search_change_breakdown", "derived", "Counts over retrieved observations only; missing dates are set difference against requested dates, not zero traffic",
     "/breakdowns/*/matched_count", "/breakdowns/*/baseline_only_count", "/breakdowns/*/comparison_only_count",
     "/breakdowns/*/displayed_counts/*", "/periods/*/missing_requested_dates", "/periods/*/observed_day_count", "/request_budget/*")
_add("search_change_breakdown", "derived", "Counts of returned rows and successfully fetched API pages; not whole source coverage",
     "/breakdowns/*/baseline_coverage/rows_returned", "/breakdowns/*/comparison_coverage/rows_returned",
     "/breakdowns/*/baseline_coverage/pages_fetched", "/breakdowns/*/comparison_coverage/pages_fetched")
_add("search_change_breakdown", "rule", "Configured request ceiling and comparison of counted attempts against that ceiling",
     "/request_budget/max_requests", "/request_budget/exhausted")
_add("search_change_breakdown", "measured", "Google returned aggregation/date metadata and returned date keys for the requested filtered window only",
     "/baseline_totals/*/response_aggregation_type", "/periods/*/observed_dates", "/periods/*/observed_start", "/periods/*/observed_end",
     "/periods/*/first_incomplete_date", "/periods/*/response_aggregation_type",
     "/breakdowns/*/baseline_coverage/response_aggregation_type", "/breakdowns/*/comparison_coverage/response_aggregation_type",
     "/breakdowns/*/baseline_coverage/response_aggregation_types", "/breakdowns/*/comparison_coverage/response_aggregation_types")
_add("search_change_breakdown", None, "No observation for this period; missing API rows are censored/unknown, not zero",
     "/breakdowns/*/baseline_only/*/comparison", "/breakdowns/*/baseline_only/*/delta",
     "/breakdowns/*/comparison_only/*/baseline", "/breakdowns/*/comparison_only/*/delta",
     "/baseline_totals/*/fetch_error", "/periods/*/fetch_error")

# Narrow evidence-first pilot: identities and references never imply causality.
_add("search_change_breakdown", "derived", "Deterministic SHA-256 of exact property/target/rule identity or sanitized retrieved observation; not storage or a provider identifier",
     "/report_contract/snapshot_id", "/report_contract/findings/*/finding_id")
_add("search_change_breakdown", "derived", "JSON-pointer selection over displayed nonnull provider metrics, calculated metrics or explicitly unavailable values; destination evidence retains its own basis",
     "/report_contract/findings/*/facts", "/report_contract/findings/*/calculations", "/report_contract/findings/*/unavailable")
_add("search_change_breakdown", "rule", "Versioned descriptive comparison contract and display selection; no cause hypothesis is generated",
     "/report_contract/rule_version", "/report_contract/findings/*/hypotheses", "/report_contract/verification/complete_source_coverage")
_add("search_change_breakdown", None, "Causal effect and calibrated probabilistic precision were not verified; method tiers are not probabilities",
     "/report_contract/verification/causal_effect", "/report_contract/verification/probabilistic_precision")
_add("search_change_breakdown", "derived", "UTF-8 bytes of the actual complete serialized envelope including metadata, or counted omission of displayed records; not tokens or source coverage",
     "/response_budget/serialized_bytes", "/response_budget/full_response_bytes", "/response_budget/omitted_rows/*/*",
     "/response_budget/omitted_findings", "/response_budget/omitted_unavailable_metrics/*/*")
_add("search_change_breakdown", "rule", "Optional caller byte ceiling and local complete-envelope budget classification; exceeded is an explicit error, not a successful report",
     "/response_budget/max_bytes", "/response_budget/status", "/error/code")

# Destination statuses belong only to received responses, never unrequested hops.
for prefix in ("/source_observation", "/targets/*"):
    _add("link_targets_audit", "measured", "Received terminal/last HTTP status or received hop status only; not Google indexation, rendered availability or ranking impact",
         f"{prefix}/status_code", f"{prefix}/last_observed_status", f"{prefix}/hops/*/status_code")
    _add("link_targets_audit", "measured", "Local collection timestamps and monotonic elapsed duration for this observation only; no hard deadline guarantee",
         f"{prefix}/started_at", f"{prefix}/completed_at", f"{prefix}/elapsed_ms",
         f"{prefix}/hops/*/observed_at", f"{prefix}/hops/*/elapsed_ms")
    _add("link_targets_audit", "measured", "Whether a physical GET was started for this chain; DNS-only refusal does not start a request",
         f"{prefix}/attempted")
    _add("link_targets_audit", "rule", "Local terminal/stop classification over received statuses and safety/budget gates; no inferred healthy status",
         f"{prefix}/outcome", f"{prefix}/availability_reason")
_add("link_targets_audit", "measured", "Observed bounded source identity-body completion; false means extraction cannot establish target coverage",
     "/source_body_complete", "/source_observation/body_complete")
_add("link_targets_audit", "measured", "Local collection timestamp, counted physical GET starts/DNS refusals and monotonic duration; not exact socket traffic",
     "/collected_at", "/budgets/requests_started", "/budgets/dns_refusals", "/budgets/elapsed_ms")
_add("link_targets_audit", "derived", "Counts over the completed bounded source parser input and destination observations only; no whole-site coverage",
     "/total_anchors", "/distinct_in_scope_targets", "/targets_attempted", "/targets_completed", "/targets_skipped", "/excluded_reasons/*")
_add("link_targets_audit", "rule", "Local same-site/port eligibility, collection-completeness and HTTP/redirect finding rules; findings do not establish SEO impact",
     "/scope_policy", "/coverage", "/targets/*/findings")
_add("link_targets_audit", "rule", "Configured finite bounds or comparison against cooperative scheduling deadline; does not cancel in-flight synchronous DNS/socket work",
     "/budgets/max_targets", "/budgets/max_requests", "/budgets/max_redirects", "/budgets/request_timeout_seconds",
     "/budgets/scheduling_deadline_seconds", "/budgets/source_max_body_bytes", "/budgets/target_max_body_bytes", "/budgets/deadline_overrun")


# Caller events are declarations; performance leaves retain the provider basis.
_add("seo_change_impact", "rule", "Caller-declared event/mapping provenance only; does not verify deployment or canonical identity", "/event/provenance", "/page_mapping/provenance")
_add("seo_change_impact", "rule", "Local date, weekday, conservative lag and compatible observed-coverage gates; lag alone does not prove provider finalization", "/comparison/status", "/comparison/reasons", "/maturity_policy/lag_days", "/maturity_policy/latest_eligible_date", "/maturity_policy/provider_finalization_verified", "/windows/weekday_aligned")
for prefix in ("/comparison/before", "/comparison/after"):
    _add("seo_change_impact", "measured", "Google reported aggregate over the declared filtered page window; date/row coverage remains in search_evidence", f"{prefix}/clicks", f"{prefix}/impressions")
    _add("seo_change_impact", "derived", "CTR from the reported counts when impressions are positive; not causal impact", f"{prefix}/ctr")
_add("seo_change_impact", "derived", "Comparison minus baseline on compatible observed windows only; descriptive, not causal", "/comparison/descriptive_delta/*")
_add("seo_change_impact", "measured", "Local report collection timestamps, not deployment timestamps", "/collection/*")
_add("seo_change_impact", None, "Causal effect is not identified by a before/after comparison", "/attribution/causal_effect", "/attribution/status")
_add("seo_change_impact", None, "Provider evidence is unavailable when the collection is absent", "/search_evidence")
_add("rewrite_fidelity_check", "rule", "Bounded mechanical literal/qualifier extraction and lexical alignment only; findings require context review and do not certify facts or semantic fidelity", "/verdict", "/assessment", "/findings", "/findings/*/category", "/findings/*/operation", "/findings/*/context_review_required", "/findings_truncated", "/analysis_truncated")
_add("rewrite_fidelity_check", "derived", "Counts over bounded extracted occurrences and local matches only", "/counts/*")
_add("rewrite_fidelity_check", None, "Mechanical comparison does not assess semantic fidelity, factual truth, scope or causality", "/semantic_assessment/*")
_add("editorial_audit", "rule", "Caller input provenance, supported-format parser selection and exclusion limits only; original source spans are codepoint coordinates, not rendered positions", "/source/origin", "/method/coverage", "/input_limits/*", "/input_truncated", "/method/location_basis")


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
_add("traffic_drops", "rule", "Negative-click selection; candidates require observed positive-impression pairs: position worsened>2, CTR fell>30%, or impressions fell. Multiple candidates may match; not causes; windows exclude GSC reporting lag",
     "/drops", "/drops/*/diagnosis", "/drops/*/diagnosis_status", "/drops/*/diagnosis_candidates")
_add("traffic_drops", "derived", "Current minus previous metric for queries in both returned periods", "/drops/*/clicks_delta", "/drops/*/impressions_delta")
for prefix in ("/drops/*/metrics_previous", "/drops/*/metrics_current", "/unavailable_queries/*/metrics_previous"):
    _add("traffic_drops", "measured", "Retained Google provider query metrics for the reported period; provider CTR/position retained only with positive impressions; missing current query is not observed zero",
         *(f"{prefix}/{metric}" for metric in ("clicks", "impressions", "ctr", "position")))
_add("traffic_drops", "measured", "Retained Google provider average position for this query and period; null with no impression evidence", "/drops/*/position_current", "/drops/*/position_previous")
_add("traffic_drops", "rule", "Prior query absent from returned current rows; availability gate, not proof of zero traffic or a cause", "/unavailable_queries", "/unavailable_queries/*/reason")
_add("traffic_drops", None, "Current query observation unavailable; no diagnostic candidate or measured current zero inferred",
     "/unavailable_queries/*/diagnosis", "/unavailable_queries/*/diagnosis_status", "/unavailable_queries/*/diagnosis_candidates", "/unavailable_queries/*/metrics_current")
_add("quick_wins", "derived", "Count of returned rows with unavailable CTR that pass the position/impression eligibility gates; no whole-source coverage", "/skipped_metric_rows/ctr_unavailable")
_add("seo_striking_distance", "rule", "Membership only: position 8..15 and impression floor; ordered by impressions", "/queries")
_add("seo_cannibalization", "rule", "Membership only: multiple returned pages, impression floor and conflict score>0.1; not proof of harmful cannibalization", "/conflicts")
_add("seo_cannibalization", "derived", "1-sum((page_clicks/total_clicks)^2) over returned query-page rows", "/conflicts/*/conflict_score")
_add("seo_cannibalization", "derived", "Count of distinct returned query keys excluded by local search-operator syntax policy; not harmful cannibalization", "/excluded_search_operator_queries")
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
_add("compare_search_engines", "derived", "Bing minus Google only for matching exact windows, present pairs, and available corresponding count inputs", "/totals/click_delta", "/totals/impression_delta", "/rows/*/click_delta", "/rows/*/impression_delta")
for engine in ("google", "bing"):
    _add("compare_search_engines", "derived", "Local sum of returned normalized dimension counts; not property totals or equivalent provider measurement semantics",
         *(f"/rows/*/{engine}/{metric}" for metric in ("clicks", "impressions")),
         *(f"/totals/{engine}/{metric}" for metric in ("clicks", "impressions")))
    _add("compare_search_engines", "derived", "Impression-weighted position over available returned normalized rows, side by side only", f"/rows/*/{engine}/position")
    _add("compare_search_engines", "derived", "Ratio of summed returned counts; unavailable on source anomaly, zero denominator, or absent dimension", f"/rows/*/{engine}/ctr", f"/totals/{engine}/ctr")
    _add("compare_search_engines", "rule", "Normalized dimension membership in retrieved provider rows; missing values are retained placeholders", f"/rows/*/{engine}/present")

for tool in ("bing_query_stats", "bing_page_stats", "bing_page_query_stats", "bing_rank_traffic_stats"):
    _add(tool, "measured", "Retained dated Bing provider count; default query mode is resolved separately as a local sum", "/rows/*/clicks", "/rows/*/impressions")
    if tool != "bing_rank_traffic_stats":
        _add(tool, "measured", "Retained Bing provider average position; default query mode is resolved separately as a local weighted calculation",
             *(f"/rows/*/{metric}" for metric in ("position", "avg_click_position", "avg_impression_position")))
    _add(tool, "derived", "Click/impression ratio of returned counts; source anomaly or zero denominator cannot establish CTR", "/rows/*/ctr")
    _add(tool, "derived", "Count of locally returned rows after date filtering and any display limit; not provider completeness", "/count")
    _add(tool, "rule", "Bounded names of unavailable source count inputs or dependent calculations; retained parser-default zeros are not observations", "/rows/*/unavailable_metrics")

_add("compare_search_engines", "rule", "Bounded unavailable input/dependent-calculation names propagated from provider rows before local sums; not whole-source completeness",
     "/rows/*/google/unavailable_metrics", "/rows/*/bing/unavailable_metrics", "/totals/google/unavailable_metrics", "/totals/bing/unavailable_metrics")

_add("bing_query_stats", "rule", "Explicit daily versus exact-query local aggregation mode; no provider completeness guarantee", "/aggregation_scope")
_add("bing_query_stats", "rule", "Local output row count exceeds requested limit after chosen aggregation", "/local_truncated")
_add("bing_query_stats", "derived", "Counts over locally retrieved rows, selected dates, and chosen aggregation only; provider completeness unknown",
     "/row_count", "/source_row_count", "/date_filtering/invalid_date_row_count", "/date_filtering/out_of_window_row_count")

for tool, prefixes in (
    ("bing_query_stats", ("/rows/*/metric_diagnostics/*", "/metric_diagnostics/*")),
    ("bing_page_stats", ("/rows/*/metric_diagnostics/*",)),
    ("bing_page_query_stats", ("/rows/*/metric_diagnostics/*",)),
    ("bing_rank_traffic_stats", ("/rows/*/metric_diagnostics/*",)),
    ("compare_search_engines", ("/rows/*/google/metric_diagnostics/*", "/rows/*/bing/metric_diagnostics/*", "/totals/google/metric_diagnostics/*", "/totals/bing/metric_diagnostics/*")),
):
    for prefix in prefixes:
        _add(tool, "rule", "Local contradictory-count classification; exposes data inconsistency without establishing its cause", f"{prefix}/reason")
        _add(tool, "derived", "Unclamped source click/impression ratio; null when denominator is zero, not a valid CTR", f"{prefix}/raw_ratio")
        _add(tool, "measured", "Original contradictory provider source counts retained before local aggregation; not corrected, clamped or discarded", f"{prefix}/clicks", f"{prefix}/impressions")
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
_add("editorial_audit", "rule", "Versioned FR/EN house-style patterns; warnings need editorial judgment, never establish AI authorship or search impact", "/verdict", "/assessment", "/findings", "/findings/*/rule_id", "/findings/*/requires_context_review")
_add("editorial_audit", "derived", "Counts and truncation over eligible parsed HTML or supported draft segments and local pattern matches only", "/metrics/*", "/findings_truncated")
_add("editorial_audit", "measured", "Received HTTP response code only, not rendered page visibility", "/http_status")
_add("editorial_audit", "rule", "Conservative known-provider challenge-page patterns; requested editorial content unavailable", "/challenge")
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
for tool in ("page_technical_audit", "heading_audit", "internal_links_audit", "link_targets_audit", "schema_validate", "editorial_audit"):
    _add(tool, "rule", "Narrow deterministic FR/EN instruction patterns in untrusted HTML; may miss or falsely flag prose; absence never establishes trust", "/untrusted_content/flagged", "/untrusted_content/signals", "/untrusted_content/signals/*")

# Error paths are explicit; successful operational statuses stay unannotated.
for tool in INVENTORY:
    _add(tool, None, "Tool error prevents an evidence interpretation; original error value is retained", "/error")
for tool in ("traffic_drops", "seo_cannibalization", "seo_lost_queries", "check_alerts", "crux_page_vitals", "crux_history", "drift_compare", "drift_history", "drift_baseline", "schema_generate"):
    _add(tool, None, "Unavailable/unsupported/error result; no successful SEO verdict is attributed here", "/verdict")
for tool in ("bing_url_submit", "bing_urls_submit_batch", "bing_feed_submit", "bing_feed_remove"):
    _add(tool, None, "Notification acceptance does not verify indexing; retained unverified sentinel", "/indexed")


# The weekday wrapper retains the child report, including its unavailable paths.
_inventory("search_weekday_reference", "fields", "Same descriptive Google observations plus bounded calendar and coverage gates")
_PATHS["search_weekday_reference"] = list(_PATHS["search_change_breakdown"])
_add("search_weekday_reference", "derived", "Calendar calculation in Pacific time; lag is a request policy, not confirmed provider completeness",
     "/weekday_reference/shift_days", "/weekday_reference/eligible_end",
     "/weekday_reference/effective_windows/*/*", "/weekday_reference/delta/*")
_add("search_weekday_reference", "rule", "Local coverage/source compatibility gate and configured three-day lag; no causal attribution",
     "/weekday_reference/status", "/weekday_reference/reasons", "/weekday_reference/report_lag_days",
     "/weekday_reference/method", "/weekday_reference/timezone", "/weekday_reference/causal_interpretation")
_add("search_weekday_reference", "derived", "Disclosed calendar alignment, observed-history robust arithmetic or omitted-day accounting; no causal model",
     "/weekday_reference/alignment/*", "/robust_reference/support_by_weekday/*/*/*",
     "/robust_reference/expected_counts/*", "/robust_reference/delta/*",
     "/robust_reference/requested_window/*", "/robust_reference/omitted_days", "/robust_reference/omitted_dates",
     "/context_preflight/records/*/date_overlap")
_add("search_weekday_reference", "measured", "Dates returned by the bounded historical Google date query; completeness is not guaranteed",
     "/robust_reference/observed_dates")
_add("search_weekday_reference", "rule", "Versioned local reference/support policy and sign comparison; agreement is not causal evidence",
     "/reference_strategy", "/assessment", "/causal_interpretation", "/robust_reference/method",
     "/robust_reference/status", "/robust_reference/reasons", "/robust_reference/minimum_support_per_weekday",
     "/robust_reference/timezone", "/robust_reference/data_state", "/robust_reference/formula",
     "/robust_reference/causal_interpretation", "/context_preflight/version", "/context_preflight/stale_after_days",
     "/context_preflight/collection_registry_status", "/context_preflight/causal_interpretation",
     "/context_preflight/records/*/origin", "/context_preflight/records/*/family",
     "/context_preflight/records/*/causal_interpretation")
_add("search_weekday_reference", "measured", "Caller-declared context, not independently verified collection incidents or business facts",
     "/context_preflight/retrieved_at", "/context_preflight/records/*/id", "/context_preflight/records/*/provider",
     "/context_preflight/records/*/report_type", "/context_preflight/records/*/source_url",
     "/context_preflight/records/*/start", "/context_preflight/records/*/end",
     "/context_preflight/records/*/uncertainty", "/context_preflight/records/*/kind")
_add("search_weekday_reference", None, "No independently verified incident registry, cause or relevance assessment is supplied",
     "/context_preflight/collection_health", "/context_preflight/authority_verification",
     "/context_preflight/records/*/relevance", "/robust_reference/fetch_error")


_inventory("crawl_log_audit", "fields", "Local access-log observations; site association is caller-declared, identity and indexing remain bounded")
_add("crawl_log_audit", "measured", "Timestamp offsets/statuses returned by parsed local log records, or source file/registry observations; no authenticated historical identity",
     "/observed_window/start", "/observed_window/end", "/source/file_bytes_at_open", "/source/stable_during_read",
     "/verification/retrieved_at", "/verification/creation_time_as_declared")
_add("crawl_log_audit", "derived", "Counts and digest over actually consumed local bytes/parsed rows; path/UA classifications do not prove bot identity",
     "/coverage/*", "/status_counts/*", "/declared_ua_counts/*", "/identity_counts/*",
     "/paths/*/requests", "/paths/*/status_counts/*", "/paths/*/path_hash", "/source/sha256_consumed_bytes",
     "/observed_window/source_offsets/*", "/verification/prefix_count", "/verification/sha256")
_add("crawl_log_audit", "rule", "Explicit local profile, scope, normalization, privacy and optional current-IP membership policy; no indexing inference",
     "/status", "/site", "/profile", "/source/site_association", "/observed_window/timezone",
     "/verification/status", "/verification/method", "/verification/source_url", "/normalization",
     "/coverage/limits_hit", "/untrusted_content/*")
_add("crawl_log_audit", "measured", "Caller-enabled log path/origin strings after query stripping; untrusted and not authenticated site inventory",
     "/paths/*/path", "/paths/*/origin")
_add("crawl_log_audit", None, "Historical bot identity and indexing are unverified; registry/file errors retain their unavailability",
     "/verification/historical_identity", "/verification/error", "/error", "/indexing_status")

_inventory("crawl_import_preview", "fields", "Imported producer observations plus local input validation; not independently measured website or indexing")
_add("crawl_import_preview", "measured", "Observed in the caller-supplied SiteOne report; collector accuracy and website state were not independently verified",
     "/source/declared_name", "/source/version", "/source/executed_at", "/scope/initial_url", "/scope/options/*",
     "/rows/*/raw_url", "/rows/*/status", "/rows/*/elapsedTime", "/rows/*/size", "/rows/*/type",
     "/rows/*/cacheTypeFlags", "/rows/*/cacheLifetime", "/source_stats/*", "/source_errors/*", "/source_notices/*")
_add("crawl_import_preview", "derived", "Local hash, input/sample counts or withheld-field accounting; counts describe only this supplied export",
     "/source/sha256", "/source/bytes", "/source/config_sha256", "/snapshot_id", "/counts/*",
     "/rows/*/row_index", "/rows/*/extras_field_count", "/unsupported_fields/count", "/unsupported_fields/omitted",
     "/rejected_messages/counts/*", "/rejected_messages/omitted")
_add("crawl_import_preview", "rule", "Local adapter/schema gate, supported input limits or imported third-party rule score; not measured ranking impact",
     "/status", "/adapter", "/errors/*/code", "/rejected_rows/*/reason", "/limits/*",
     "/rejected_messages/sample/*/reason",
     "/source_scores/value/overall/score", "/source_scores/value/categories/*/score", "/source_scores/ranking_signal",
     "/untrusted_content/authority")
_add("crawl_import_preview", None, "Producer selection or execution timezone is not independently known from this import",
     "/scope/selection", "/source/executed_at_timezone", "/missing_metadata")


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
    if tool == 'crawl_log_audit' and data.get('status') == 'unavailable' and path[0] in {'status', 'coverage'}:
        return None, 'Local log assessment unavailable; count placeholders do not establish an empty or healthy log'
    if tool == "ai_overviews_impact" and path[0] == "rows" and key in {"clicks", "impressions", "ctr", "position"} and value == 0 and data.get('metric_origin') != 'explicit_provider_fields':
        return None, "Legacy parser zero may be a provider zero or a missing metric default; provider origin is unavailable"
    if tool == "traffic_drops" and path[0] == "drops" and key in {"diagnosis", "diagnosis_status", "diagnosis_candidates"}:
        if parent.get("diagnosis") == "unknown" or parent.get("diagnosis_status") == "insufficient_evidence":
            return None, "Observed metric pair supports no diagnostic candidate; unknown is unavailable, not a successful cause attribution"
    if tool in {"bing_query_stats", "bing_page_stats", "bing_page_query_stats", "bing_rank_traffic_stats", "compare_search_engines"}:
        if key in parent.get("unavailable_metrics", []):
            return None, "Required provider source input unavailable; retained parser-default or partial aggregate value is not an established observation/calculation"
        if tool == "compare_search_engines" and parent.get("present") is False and key in {"clicks", "impressions", "ctr", "position"}:
            return None, "Dimension absent from provider rows; retained zero values are placeholders, not observations"
        if key == "ctr" and parent.get("impressions") == 0:
            return None, "Zero impressions cannot establish CTR; any retained legacy zero is a placeholder"
        if tool == "bing_query_stats" and len(path) == 3 and path[0] == "rows" and key in {"clicks", "impressions", "position", "avg_click_position", "avg_impression_position"}:
            if data.get("aggregation_scope") == "query":
                return "derived", "Local sum of dated requested-window counts or click/impression-weighted available positions by exact query key; provider completeness unknown"
            if data.get("aggregation_scope") != "daily":
                return None, "Query aggregation scope unavailable; provider versus local metric provenance cannot be established"
    if tool == "link_targets_audit" and data.get("coverage") == "unavailable" and path[0] in {
            "total_anchors", "distinct_in_scope_targets", "targets_attempted", "targets_completed", "targets_skipped", "excluded_reasons"}:
        return None, "Incomplete/unavailable source prevents target extraction; retained zeros are placeholders"
    if tool in {"inspect_url", "batch_url_inspection", "check_indexing_issues"}:
        if key in _INSPECTION and not _inspection_substantive(value):
            return None, "Google inspection state is missing/unknown/unspecified"
        if key == "category" and (value == "unknown" or not any(
                _inspection_substantive(parent.get(k)) for k in (*_INSPECTION, "google_canonical", "user_canonical"))):
            return None, "Local category fallback has no substantive provider input"
    elif key == "verdict" and value in {"error", "fetch_error", "ssrf_blocked", "missing_key", "unsupported", "not_enough_data", "no_baseline", "no_data"}:
        return None, "Unavailable, unsupported or tool error result; original verdict retained"
    if tool in {"search_change_breakdown", "search_weekday_reference"} and ((key == "availability" and value != "observed") or (key == "incompleteness_status" and value == "unknown")):
        return None, "Provider observation/coverage unavailable or unknown; no successful measurement inferred"
    if tool == "search_weekday_reference" and path in {("weekday_reference", "status"), ("robust_reference", "status")} and value != "observed":
        return None, "Required reference coverage or compatible aggregate is unavailable; no seasonal conclusion established"
    if tool == "crawl_import_preview" and path == ("status",) and value == "rejected":
        return None, "Rejected input supplies no supported crawl observation; validation failure is not an empty or healthy crawl"
    if tool == "seo_change_impact" and path == ("comparison", "status") and value != "observed":
        return None, "The required before/after observations are unavailable or incompatible"
    if tool == "rewrite_fidelity_check" and data.get("assessment") == "not_assessed" and path[0] in {"verdict", "assessment", "findings", "counts", "findings_truncated", "analysis_truncated"}:
        return None, "Invalid input prevented mechanical assessment; placeholders are not zero findings"
    if tool == "editorial_audit" and data.get("assessment") != "house_style_review" and path[0] in {"verdict", "assessment", "findings", "metrics", "findings_truncated"}:
        return None, "Editorial content was not assessed; placeholders never mean no warnings"
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
    if tool == "seo_change_impact" and isinstance(data.get("search_evidence"), dict):
        fields.pop("/search_evidence", None)
        nested = evidence_for(data["search_evidence"], "search_change_breakdown")
        fields.update({"/search_evidence" + pointer: record for pointer, record in nested["fields"].items()})
    if tool == "search_weekday_reference" and isinstance(data.get("references"), dict):
        for strategy, report in data['references'].items():
            nested = evidence_for(report, tool)
            fields.update({"/references/" + strategy + pointer: record for pointer, record in nested['fields'].items()})
    return {"version": 1, "fields": fields}
