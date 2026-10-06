# Keyword Opportunities

Three angles for finding ranking opportunities: pages near page one, queries that lost ground, and multiple pages competing for the same keyword. The assistant reads the data directly from the configured providers.

Replace `yourdomain.com` with your GSC property URL.

Google supports every workflow below. Bing supports `quick_wins`, `seo_striking_distance` and `prune_candidates`, but not exact-period loss or bulk cannibalization analysis.

---

## Striking distance: pages close to page one

> For Google, find queries where yourdomain.com ranks between positions 8 and 15. Which ones have the most impressions? If Bing is configured, run the same analysis separately with engine="bing" and keep positions provider-specific.

The assistant calls `seo_striking_distance` and returns observed position, clicks, impressions and CTR, sorted by impressions. The tool does not forecast ranking gains or return an opportunity score.

### Follow-up

> For the top 5 striking-distance queries, which pages rank for them? Check content coverage, internal links and title tags, and label each proposed explanation as a hypothesis.

---

## Lost queries: what stopped sending traffic

> Which queries drove traffic to yourdomain.com in the last 90 days but have since dropped significantly?

The assistant calls the Google-only `seo_lost_queries` analysis. Bing is refused here because its current contract does not provide the exact adjacent windows this comparison requires.

### Follow-up

> For the queries with the biggest click drop, check whether the pages ranking for them have indexing issues.

---

## Cannibalization: multiple pages competing for the same query

> Check yourdomain.com for keyword cannibalization. Which queries are split across more than one page?

The assistant calls `seo_cannibalization` and returns a Herfindahl-Hirschman Index (HHI) score per query. A low score means clicks are fragmented across multiple URLs instead of consolidating on one.

### Follow-up

> For the worst cannibalization cases, which page has the strongest measured claim to be primary? Compare merge, redirect, rewrite and no-change options without executing them.

Before choosing a destructive action, compare traffic, intent, indexation and internal links for every affected URL. Do not recommend merge, redirect, deletion or `noindex` from cannibalization data alone.

---

## AI Overviews: inspect available Search Console rows

> Which query and searchAppearance rows are available for AI Overviews on yourdomain.com? Show their clicks, impressions, CTR and position without constructing a control cohort.

The assistant calls `ai_overviews_impact`, which returns the available GSC rows grouped by `query` and `searchAppearance`. It does not calculate a controlled CTR delta or prove an AI Overview effect.
