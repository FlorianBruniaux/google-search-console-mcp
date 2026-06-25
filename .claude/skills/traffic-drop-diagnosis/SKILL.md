---
name: traffic-drop-diagnosis
description: Diagnose sudden or sustained traffic drops by finding the affected period,
  lost queries, and most likely root cause. Use when asked why traffic fell, what
  changed, or whether a Google algorithm update had an impact.
---

# Traffic Drop Diagnosis

Systematically diagnose the root cause of a traffic decline.

## Steps

1. Call `list_properties` to confirm the exact `site_url`.
2. Call `traffic_drops` to identify the time range and magnitude of the drop. Note the start date and affected segments (queries, pages, device types).
3. Call `check_alerts` to check for manual actions, security issues, or GSC notifications around the drop date.
4. Call `analytics_anomalies` to detect statistical anomalies and corroborate the drop timing with data.
5. Call `seo_lost_queries` to find the specific queries that lost clicks or impressions. Note the top 20 by click loss.
6. Call `compare_search_periods` for the 28 days before vs. the 28 days after the drop, using `dimensions=query` and `limit=50`. Flag any query with more than 30% click decline.
7. Cross-reference the drop timing against known Google algorithm update dates. Ask the user for the approximate drop date if not yet provided.

## Output format

Present a structured diagnosis in four sections:

**Drop summary**: date range, magnitude (clicks and impressions % change), overall health status from step 2.

**Root cause candidates** (ranked by likelihood based on the data):
1. Manual action or penalty (from `check_alerts`)
2. Algorithm update impact (correlated with timing)
3. Specific query losses (from `seo_lost_queries`)
4. Technical issues (crawl or index problems)

**Most affected queries**: table with Query | Clicks before | Clicks after | % change

**Next steps**: specific actions ordered by priority, one per root cause candidate identified.
