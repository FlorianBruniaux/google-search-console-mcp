# Page Deep Dive

Full diagnostic for one URL using Google indexation, search performance, Core Web Vitals and on-page evidence. When Bing is configured, add its page-query and URL traffic data without turning Bing URL fields into an indexation verdict.

Replace `yourdomain.com/your-page-path` with the actual URL you want to diagnose.

---

## Start with the full diagnostic

> Give me a full diagnostic of yourdomain.com/your-page-path. Start with the indexing status, then performance, then Core Web Vitals.

The assistant calls `inspect_url`, `page_health_score`, `get_search_by_page_query` and `crux_page_vitals` in sequence and returns the available evidence with the health-score breakdown.

---

## Drill into each dimension

### Indexing

> Is Google actually indexing this page? When was it last crawled and what was the result?

### Queries

> Which queries bring visitors to this page? Are there any with high impressions but low CTR that I should rewrite the title or meta description for?

### Core Web Vitals

> How are the Core Web Vitals on this page trending over the last 25 weeks? Is LCP or INP above the threshold?

### Content gaps

> Based on the queries this page already ranks for and the ones where it gets impressions but no clicks, what topics should I cover or expand?

The assistant calls `content_brief` to combine the page's top GSC queries, detected question queries and optional GA4 engagement data. Inspect the page separately before turning those observations into content recommendations.

---

## Compare against expectations

> I think I should rank higher for [query] on this page. What position and CTR are actually observed, and how do they compare with this page's other measured queries?

The assistant uses `get_search_by_page_query` for the observed query-level values. The exposed tools do not provide a query-level expected-CTR benchmark, so any external benchmark must be named and treated as a heuristic.

## Add Bing evidence

> Bing is configured for https://yourdomain.com/. Add `bing_page_query_stats`, `bing_url_traffic` and `bing_url_info` for this exact page. Keep Bing position and freshness fields separate from Google, and mark unavailable fields as unknown.

Use `compare_search_engines` only when you want a bounded side-by-side comparison. It omits deltas when exact equal observed windows are not established.
