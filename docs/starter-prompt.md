# Starter prompts for Search Console MCP

Copy one prompt into Claude, Codex or another MCP-compatible client. Replace the example properties and keep only the providers configured with the [installation guide](installation.md).

| Goal | Prompt |
|---|---|
| Compare Google and Bing | [Google and Bing audit](#google-and-bing-audit) |
| Get a short cross-engine snapshot | [Google and Bing quick comparison](#google-and-bing-quick-comparison) |
| Audit Google with optional GA4 | [Google and GA4 audit](#google-and-ga4-audit) |
| Investigate one URL | [Single-page audit](#single-page-audit) |
| Submit an eligible page | [Google Indexing API workflow](#google-indexing-api-workflow) |

## Google and Bing audit

Use this when both providers are configured. The Bing API key belongs in `BING_WEBMASTER_API_KEY`, not in the prompt. One user-level key covers the verified sites visible to that Bing account; the prompt still names the site passed to every call.

```
You have access to the gsc-mcp Google Search Console and Bing Webmaster tools.
My Google property is: sc-domain:example.com
My Bing site is: https://example.com/

Work in this order:

1. Call get_capabilities, list_properties and bing_sites_list. Report only declared
   credentials and observed site access. Do not claim authentication from an env flag.

2. Read query, page and daily performance from both engines for 28 days. For each
   result, preserve the requested and observed windows. Mark clicks and impressions
   as measured, CTR as derived, and keep Google and Bing position semantics separate.

3. Run quick_wins, seo_striking_distance and prune_candidates once per engine.
   Pass engine="bing" for Bing. A page with measured clicks or impressions is protected
   from pruning. Check crawl and indexation separately before recommending removal.

4. Call compare_search_engines for query and page dimensions. Show click and
   impression deltas only if the tool reports equal exact observed windows. Never
   subtract positions across engines and do not infer causality from a difference.

5. Read Bing crawl, URL, feed and backlink data where relevant. Treat quota semantics,
   data freshness, non-empty crawl issue shapes, nested backlink rows and RemoveFeed
   runtime behavior as UNKNOWN or UNVERIFIED_RUNTIME when the tool says so. Do not use
   Bing keyword-research endpoints; they are not registered after HTTP 400 canaries.

6. Separate the report into measured facts, derived metrics and recommendations.
   Prioritize corrections with a named URL or query and the supporting metric.

7. If a correction changes a page or feed, stop before any mutation. State the exact
   tool, target and number of affected URLs or feeds, then request explicit confirmation.
   Do not call a write tool until that confirmation names the action.

8. After confirmation, call the selected write tool once. Report its returned status.
   An accepted request, HTTP 200 or last crawl date proves neither crawl nor indexation.

9. Define the later comparable window needed to measure the result. Do not attribute
   a change to the submission without comparable observed data.

Explicit Bing refusals are expected: traffic_drops and seo_lost_queries need exact
adjacent periods; check_alerts and seo_cannibalization need bulk page-query data.
Report the refusal reason rather than replacing it with guessed or N+1 data.
```

This prompt requires `gsc-mcp-tools>=1.2.0` or a current source checkout because earlier published versions do not expose the Bing tools.

## Google and Bing quick comparison

Use this when you want a bounded cross-engine snapshot rather than a full audit:

```
Compare Google and Bing performance for example.com over the last 28 days.

Google property: sc-domain:example.com
Bing site: https://example.com/

1. Confirm observed access with list_properties and bing_sites_list.
2. Call compare_search_engines for query and page dimensions.
3. Return the top 10 queries and pages per engine by impressions.
4. Show clicks, impressions and derived CTR. Keep positions side by side.
5. Show deltas only when the tool confirms equal exact observed windows.
6. List three engine-specific opportunities, each backed by a query or URL.
7. Separate observed facts, derived values and recommendations.
8. Do not call a write tool.
```

## Google and GA4 audit

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

4. Top quick wins: pages ranked 4-15 with high impressions and CTR below the benchmark.
   Give me the top 10, ordered by opportunity score.

5. Queries in striking distance (positions 6-15). Which pages could realistically
   reach the top 5 with targeted improvements?

6. Traffic drop diagnosis for the last 28 days vs. the prior period.
   Classify drops as: ranking_loss, ctr_collapse, or demand_decline.

7. Cannibalization check: identify queries where multiple pages compete and
   split click share.

8. Lost queries: queries that had clicks 90 days ago but have dropped to near
   zero in the last 28 days.

9. Indexing issues: inspect a named sample of up to 10 priority URLs and group
   only their returned verdicts by reason. Keep every uninspected URL unknown.

10. Sitemap audit: use sitemap_audit to check my main sitemap. How many URLs
    are declared vs. have Search Analytics page rows? Report visibility_verdict
    and without_search_data_sample. Do not infer indexation from this comparison.

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

16. Produce a prioritized action plan based on evidence and scope:
    - P0: active blocks or severe regressions with a named affected URL
    - P1: high-impact measured opportunities or invalid structured data
    - P2: lower-impact improvements and hypotheses that need more evidence
    For each item, name the evidence, affected scope, owner type and validation check.

Return all results as structured data. For each finding, include the specific
page or query, the metric value, and a one-sentence recommendation.
```

## Short Google audit

Use this when you want a fast summary without the full analysis:

```
Run a quick SEO health check for https://example.com:

1. Performance overview for 28 days (clicks, impressions, CTR, position).
2. Top 5 page-level quick wins (positions 4-15 with high impressions and CTR below benchmark).
3. Any active high-severity alerts.
4. Indexing verdicts for a named sample of up to 10 priority URLs, grouped by reason.
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

## Google Indexing API workflow

Google limits the Indexing API to pages containing `JobPosting` or `BroadcastEvent` embedded in a `VideoObject`. For other page types, do not call `submit_url` or `submit_batch`; use URL Inspection for diagnosis and normal discovery paths such as sitemaps and internal links. See [Google's official eligibility policy](https://developers.google.com/search/apis/indexing-api/v3/quickstart).

Use this prompt only after fixing an eligible page:

```
I just fixed this eligible JobPosting or livestream page:
https://example.com/my-page

1. Inspect the current indexing status.
2. Validate that the page contains eligible JobPosting or BroadcastEvent markup.
3. If the verdict is not PASS or eligibility is not demonstrated, stop and explain why.
4. If ready, state the exact URL, tool and notification type, then ask for confirmation.
5. Call submit_url once only after I explicitly confirm that action.
6. Report the returned status without claiming crawl or indexation. `submit_url` does not report a locally tracked quota value.
7. Define when URL Inspection should be checked again for a later observation.
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
3. List investigation areas for poor ratings (LCP = image/server, INP = JavaScript,
   CLS = layout shift, TTFB = server response time) and label them as hypotheses.
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

Use when you want to compare a sitemap with Search Analytics visibility:

```
Audit my sitemap at https://example.com/sitemap.xml for the property sc-domain:example.com.

Use sitemap_audit and report:
1. Is this a sitemap index or a regular urlset?
2. How many URLs are declared in the sitemap?
3. How many of those URLs appear in GSC search data (last 90 days)?
4. What is visibility_verdict? This measures search data, not indexation.
5. If partial_search_visibility, show without_search_data_sample for URL inspection.
```
