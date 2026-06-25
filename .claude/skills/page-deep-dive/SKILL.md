---
name: page-deep-dive
description: Full diagnostic for a single URL combining indexing status, search performance,
  Core Web Vitals, and query breakdown. Use when asked to analyze a specific page
  or diagnose why a particular URL is underperforming.
---

# Page Deep Dive

Complete analysis of a single page: indexing, performance, Core Web Vitals, and content signals in one pass.

## Input

Requires a specific `page_url` from the user before starting.

## Steps

1. Call `list_properties` to confirm the `site_url`.
2. Call `inspect_url` with the target URL to get its indexing status, canonical URL, robots.txt compliance, and last crawl date.
3. Call `page_analysis` on the same URL for on-page content signals and quality assessment.
4. Call `page_health_score` to get a composite health score with a breakdown by category.
5. Call `crux_page_vitals` to get real-user Core Web Vitals (LCP, INP, CLS) for that URL from the Chrome User Experience Report.
6. Call `get_search_by_page_query` to get all queries driving traffic to that page, sorted by clicks over the last 28 days.

## Output format

**Indexing status**: indexed / not indexed / issues, with the specific reason if not indexed.

**Performance snapshot**: clicks, impressions, avg CTR, avg position over 28 days.

**Top queries driving traffic**: Query | Clicks | Impressions | CTR | Position

**Core Web Vitals**: LCP | INP | CLS | Overall status (Good / Needs improvement / Poor)

**Health score**: numeric score plus a breakdown by category.

**Action list** sorted by priority:
1. Critical: indexing or crawl issues to fix immediately
2. High: Core Web Vitals failing thresholds
3. Medium: content or on-page optimization opportunities from `page_analysis`
4. Low: internal linking or schema enhancements
