# Starter prompt for gsc-mcp

Copy this prompt into Claude Desktop (or any MCP-compatible client) to run a full first audit of your site. Replace the two placeholders and go.

```
You have access to a Google Search Console + GA4 MCP server.
My site is: https://example.com
My GA4 property ID is: 123456789   (leave blank or remove this line if you don't use GA4)

Run a complete SEO audit in this order:

1. List my GSC properties to confirm the site is accessible.

2. Check active alerts (last 30 days). If severity "high" alerts exist,
   surface them immediately before continuing.

3. Performance overview for the last 28 days and 90 days. Highlight:
   - Total clicks and impressions
   - Average CTR and position
   - Notable trend between the two periods

4. Top quick wins: queries ranked 4-15 with high impressions and low CTR.
   Give me the top 10, ordered by opportunity score.

5. Queries in striking distance (positions 6-15). Which pages could realistically
   reach the top 5 with targeted improvements?

6. Traffic drop diagnosis for the last 28 days vs. the prior period.
   Classify drops as: ranking_loss, ctr_collapse, or demand_decline.

7. Cannibalization check: identify queries where multiple pages compete and
   split click share.

8. Lost queries: queries that had clicks 90 days ago but have dropped to near
   zero in the last 28 days.

9. Indexing issues: group all non-indexed pages by reason
   (not_indexed, robots_blocked, fetch_error, canonical_issue).
   How many pages fall into each category?

10. Sitemap audit: use sitemap_audit to check my main sitemap. How many URLs
    are declared vs. found in GSC? Report the verdict and the missing_sample.

11. Page-level deep dive on the top 3 pages by clicks:
    - Search analytics (queries, CTR, position)
    - Indexing status via URL inspection

12. If GA4 property ID was provided:
    - Organic landing page performance (sessions, bounce rate, conversions)
    - Traffic sources breakdown
    - User behavior by device and country

13. Cross-platform analysis (GSC + GA4) for the top 5 organic landing pages:
    combine GSC click data with GA4 engagement metrics to surface pages
    where traffic is high but engagement is poor.

14. Core Web Vitals: use crux_page_vitals on the top 3 pages by clicks.
    Report the verdict for LCP, INP, and CLS. Flag any "poor" ratings.

15. Schema validation: use schema_validate on the homepage and the top 2 pages
    by clicks. List detected schema types, invalid fields, and any recommendations.

16. Produce a prioritized action plan:
    - Critical (fix this week): indexing blocks, high-severity alerts, CWV "poor" ratings
    - High (fix this month): quick wins, cannibalization, lost queries, invalid schemas
    - Medium (next quarter): striking distance pages, GA4 engagement gaps, sitemap gaps
    - Low: nice-to-have optimizations

Return all results as structured data. For each finding, include the specific
page or query, the metric value, and a one-sentence recommendation.
```

## Shorter version (5-minute audit)

Use this when you want a fast summary without the full analysis:

```
Run a quick SEO health check for https://example.com:

1. Performance overview for 28 days (clicks, impressions, CTR, position).
2. Top 5 quick wins (queries ranked 4-15 with high impressions).
3. Any active high-severity alerts.
4. Count of non-indexed pages by reason.
5. Three-sentence summary with the single most important action to take now.
```

## Single-page audit

Use when you want to investigate one URL specifically:

```
Audit this page in depth: https://example.com/my-page

1. Inspect the URL: indexing status, last crawl date, canonical, verdict.
2. Search analytics for this page: top 10 queries, clicks, impressions, CTR, position.
3. If it is not indexed, diagnose the reason and suggest the fix.
4. If it is indexed, identify the top opportunity query to optimize for.
5. Check if this page cannibalizes any other page on the same queries.
6. Validate the JSON-LD schema on this page with schema_validate.
7. Check Core Web Vitals with crux_page_vitals (desktop and mobile).
```

## Reindexing workflow

Use after fixing a page that was previously not indexed:

```
I just fixed https://example.com/my-page and want it reindexed.

1. Inspect the current indexing status.
2. If verdict is not PASS, explain what still needs fixing before submitting.
3. If ready, submit the URL to Google's Indexing API.
4. Confirm the submission and note the quota remaining for today.
```

## Core Web Vitals audit

Use to investigate CWV performance across key pages:

```
Run a Core Web Vitals audit for https://example.com using crux_page_vitals.

Check these pages: /, /blog, /contact   (replace with your key pages)
Check both PHONE and DESKTOP form factors.

For each page and device:
1. Report LCP, INP, CLS, FCP, TTFB with their rating (good/needs_improvement/poor).
2. Flag any metric rated "poor" as a priority fix.
3. Suggest the most likely cause for poor ratings based on the metric (LCP = image/server,
   INP = JavaScript, CLS = layout shift, TTFB = server response time).
4. Produce a summary table: page x metric x rating.
```

## Schema validation audit

Use to check structured data coverage across the site:

```
Run a schema validation audit on these pages:
- https://example.com/          (homepage)
- https://example.com/faq       (FAQ page)
- https://example.com/blog/my-post  (a blog post)

For each page, use schema_validate and report:
1. Which schema types were detected.
2. Which required fields are missing (and why they matter for Google).
3. Which schema types are recommended based on the URL pattern but not present.
4. Overall verdict: healthy, missing_schemas, invalid_schemas, or fetch_error.
5. Priority fixes ordered by SEO impact.
```

## GA4-only audit

Use when you want to focus on analytics without GSC data:

```
Run a GA4 performance audit for property ID 123456789, last 28 days:

1. Organic landing pages: top 10 by sessions, with bounce rate and conversions.
2. Traffic sources: sessions by channel group (Organic, Direct, Referral, etc.).
3. User behavior: sessions and engagement rate by device and by country (top 10).
4. Conversion funnel: which pages generated conversions? Which events fired most?
5. Realtime: how many active users right now, and on which pages?
```

## Sitemap audit

Use when you want to check sitemap coverage against GSC:

```
Audit my sitemap at https://example.com/sitemap.xml for the property sc-domain:example.com.

Use sitemap_audit and report:
1. Is this a sitemap index or a regular urlset?
2. How many URLs are declared in the sitemap?
3. How many of those URLs appear in GSC search data (last 90 days)?
4. Verdict: healthy, partial, empty, or fetch_error?
5. If partial, show the missing_sample so I can investigate which pages are absent.
```
