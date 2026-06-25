---
name: seo-weekly-report
description: Generate a complete weekly SEO performance report for a site, including
  alerts, anomalies, and period-over-period comparison. Use when asked for a site
  summary, performance overview, or weekly report.
---

# SEO Weekly Report

Generate a full weekly SEO performance report for a Google Search Console property.

## Steps

1. Call `list_properties` to confirm the exact `site_url` to use.
2. Call `check_alerts` to surface any active GSC alerts or manual actions. If any are present, flag them at the top of the report before anything else.
3. Call `traffic_health_check` to get an overall site health status and detect any active anomalies.
4. Call `get_performance_overview` with `days=28` to retrieve totals (clicks, impressions, CTR, position) and the daily trend.
5. Call `analytics_anomalies` to detect statistical anomalies over the same period.
6. Call `compare_search_periods` comparing the last 28 days against the prior 28-day period, using `dimensions=query` and `limit=20`.
7. Flag any queries where clicks dropped by more than 20% between periods.
8. Call `get_search_analytics` with `dimensions=query` and `row_limit=10` to get the top 10 queries by clicks.
9. Summarize all results in a structured report.

## Output format

Present the report as a clear markdown document with these sections in order:

- **Health status** (from `check_alerts` and `traffic_health_check`): shown first, highlighted if critical
- **Overall performance snapshot**: totals + period-over-period delta
- **Anomalies** (from `analytics_anomalies`): dates or metrics with unusual patterns
- **Query alerts**: queries with more than 20% click decline, each with a one-sentence recommendation
- **Top 10 queries** by clicks
