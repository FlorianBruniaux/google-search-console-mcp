# Page Deep Dive

Full diagnostic for a single URL: indexing status, search performance, Core Web Vitals, and the queries driving traffic to it. Use this when a page is underperforming, not ranking where it should, or not appearing in Google at all.

Replace `yourdomain.com/your-page-path` with the actual URL you want to diagnose.

---

## Start with the full diagnostic

> Give me a full diagnostic of yourdomain.com/your-page-path. Start with the indexing status, then performance, then Core Web Vitals.

Claude calls `inspect_url`, `page_health_score`, `get_search_by_page_query`, and `crux_page_vitals` in sequence and returns a score out of 100 with a breakdown by category.

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

Claude calls `content_brief` to cross-reference query data with on-page signals and suggest content angles.

---

## Compare against expectations

> I think I should rank higher for [query] on this page. What position am I actually at, what's my CTR, and how does that compare to the expected CTR for that position?

Claude pulls the query-level data and benchmarks it against position-based CTR curves to tell you whether the gap is a ranking problem or a click appeal problem.
