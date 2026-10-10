"""Source-only projections of repository SEO roles for both native CLI hosts.

These narrow contracts do not execute the interactive skills or enable their
tools. Missing observations remain unavailable, including ancillary HTML reads.
"""

ROLE_PROFILES = {
    'gsc-seo-reporter': {
        'tools': {'get_performance_overview', 'compare_search_periods', 'get_search_analytics',
                  'check_alerts', 'traffic_health_check', 'search_change_breakdown'},
        'instruction': 'Summarize retrieved performance and compatible windows. Alerts are heuristic signals, '
                       'not manual actions or security incidents. Missing rows are unknown. Do not create a health '
                       'score, cause, future gain or site-wide indexing total.'},
    'gsc-traffic-doctor': {
        'tools': {'compare_search_periods', 'traffic_drops', 'search_weekday_reference',
                  'traffic_health_check', 'search_change_breakdown', 'seo_lost_queries', 'check_alerts'},
        'instruction': 'Diagnose the observed traffic change descriptively using dated comparison windows. '
                       'Keep hypotheses separate; timing does not prove an algorithm cause, manual action or '
                       'security incident. State missing daily coverage and the next source check.'},
    'gsc-ai-overviews-analyst': {
        'tools': {'ai_overviews_impact', 'compare_search_periods', 'get_search_analytics'},
        'instruction': 'Review generic search observations and whether AI exposure is actually supplied. '
                       'Generic appearances, stable rank or declining CTR do not prove AI presence, absence '
                       'or causal loss. Retain unavailable exposure; do not estimate AI-attributed lost clicks.'},
    'gsc-indexing-auditor': {
        'tools': {'inspect_url', 'batch_url_inspection', 'check_indexing_issues', 'indexing_evidence_matrix'},
        'instruction': 'Review only the selected URL sample. Separate Google verdict and coverage from local '
                       'categories. Preserve UNKNOWN fields and inspection failures. State sample denominator; '
                       'do not extrapolate site-wide indexing or infer indexing from search visibility.'},
    'gsc-sitemap-auditor': {
        'tools': {'list_sitemaps', 'sitemaps_get', 'sitemap_audit', 'indexing_evidence_matrix',
                  'batch_url_inspection', 'check_indexing_issues'},
        'instruction': 'Separate submitted sitemap inventory, fetch/download evidence, URL counts, search '
                       'visibility and independent URL inspection. Missing sitemap inventory remains unavailable. '
                       'Do not compute a submitted/indexed ratio or extrapolate site-wide indexing.'},
    'gsc-schema-auditor': {
        'tools': {'schema_validate'},
        'instruction': 'Review supplied local JSON-LD validation only. Preserve challenge-page and parser '
                       'limitations. Google rich-result eligibility and ranking impact remain unverified. '
                       'Without schema observations, schema conclusions are unavailable.'},
    'gsc-cannibalization-checker': {
        'tools': {'seo_cannibalization', 'get_search_analytics', 'inspect_url', 'batch_url_inspection'},
        'instruction': 'Review same-query page overlap, not a proven harmful conflict. A conflict score or shared '
                       'query alone does not justify consolidation. Conditional canonical, redirect or merge '
                       'suggestions require known intent, 90-day page traffic and separate URL inspection '
                       'for each affected URL. Otherwise state the missing evidence and next read-only check.'},
    'gsc-content-optimizer': {
        'tools': {'seo_striking_distance', 'quick_wins', 'get_search_analytics'},
        'instruction': 'Separate observed opportunities from rule-selected candidates and hypotheses. '
                       'Use the returned striking-distance range and quick-win rules; do not promise ranking '
                       'gain, recategorize missing rows as zero or invent page content.'},
    'gsc-page-analyst': {
        'tools': {'inspect_url', 'batch_url_inspection', 'indexing_evidence_matrix', 'get_search_analytics',
                  'ga4_page_performance', 'bing_url_info', 'bing_url_traffic'},
        'instruction': 'Review only explicitly selected URLs and retain source identity and windows. '
                       'Bing URL info is not Google URL Inspection. Page HTML, schema, rendering and Core Web '
                       'Vitals remain unavailable without their sources. Do not claim a complete page audit.'},
}
