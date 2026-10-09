---
name: traffic-drop-diagnosis
description: Diagnose a Google Search traffic decline with dated property totals, query and page changes, and explicit evidence limits. Use for a sudden or sustained click decline, a page that lost traffic, or a suspected algorithm update. Déclenché aussi par « chute de trafic », « mes clics ont baissé », « cette page a décroché » ou « mise à jour Google ».
---

# Traffic Drop Diagnosis

Describe what changed before proposing why. GSC search rows and heuristic labels do not establish a cause.

## Steps

1. Call `list_properties()` and use the exact selected Google property as `site`. Keep that property in every call and in the report. Done when the property and search surface are identified.
2. Establish the suspected change date from the user or the available dated data. For a rolling check, call `compare_search_periods(site, days=28)`; it returns two consecutive property-level windows, not query rows. Call `traffic_drops(site, days=28)` for query-level candidates and `analytics_anomalies(site, days=90)` for daily outliers. The latter's z-score is a statistical flag, not a cause. Done when actual returned windows and any incomplete or missing observations are recorded.
3. For a dated decline, choose disjoint, equal-length baseline and comparison windows around it, avoiding recent incomplete GSC days. Call `search_change_breakdown(site, baseline_start, baseline_end, comparison_start, comparison_end, dimensions=["query", "page", "device", "country"])`. Reduce dimensions if the request budget or question calls for it. Read `periods`, `baseline_comparison`, each dimension's `comparison` and coverage, and `limitations` before quoting a delta. Separate dimension views describe the same traffic and must not be added together. Done when the affected segments are tied to their requested and observed dates and coverage.
4. Optionally call `seo_lost_queries(site, days=28)` to find leads, but its current window includes recent days and a missing current query row can appear as zero in its output. Check any lead against observed rows and coverage in `search_change_breakdown` before presenting it as a loss. `check_alerts(site, days=28)` may add traffic concentration or high-impression, low-rank opportunities; it supplies no manual-action, security, or notification status. Done when each lead is either corroborated or marked uncertain.
5. Rank *hypotheses* only where evidence supports them. A contemporaneous public algorithm update is a timing clue, not attribution; verify its dated source if used. Manual actions, security incidents, crawl failures, tracking faults and indexation changes remain `UNKNOWN` until checked through an appropriate separate source. Ask for the user's dated context only when it changes the window or investigation. Done when no unsupported cause is presented as a finding.

## Report

- **Observed change:** property, Google search type, requested and observed windows, property-level clicks and impressions, comparison status and coverage. State `UNKNOWN` rather than turning missing rows or unavailable totals into zero.
- **Affected segments:** observed query/page/device/country changes, with their window and coverage. Label a calculated delta as arithmetic, and avoid a percentage when its baseline is zero or unavailable.
- **Possible causes:** evidence for and against each hypothesis, missing checks and confidence stated in words. A query-level ranking or CTR rule is a lead, not a diagnosis.
- **Next check:** the smallest read-only check that could discriminate the leading hypotheses. Do not execute indexing, sitemap or other write tools.
