# Keyword Opportunities

Three angles for finding ranking wins: pages near page one, queries that lost ground, and multiple pages competing for the same keyword. None of these require manual keyword research — Claude reads the data directly from your GSC account.

Replace `yourdomain.com` with your GSC property URL.

---

## Striking distance: pages close to page one

> Find queries where yourdomain.com ranks between positions 8 and 20. Which ones have the most impressions and the best chance of breaking into the top 5?

Claude calls `seo_striking_distance` and returns a ranked list with current position, impressions, and estimated CTR gain from moving up.

### Follow-up

> For the top 5 striking-distance queries, which pages rank for them and what would likely push them to page one — more content, better internal links, or stronger title tags?

---

## Lost queries: what stopped sending traffic

> Which queries drove traffic to yourdomain.com in the last 90 days but have since dropped significantly?

Claude calls `seo_lost_queries` and identifies queries that fell in clicks, position, or disappeared from the top 20.

### Follow-up

> For the queries with the biggest click drop, check whether the pages ranking for them have indexing issues.

---

## Cannibalization: multiple pages competing for the same query

> Check yourdomain.com for keyword cannibalization. Which queries are split across more than one page?

Claude calls `seo_cannibalization` and returns a Herfindahl-Hirschman Index (HHI) score per query. A low score means clicks are fragmented across multiple URLs instead of consolidating on one.

### Follow-up

> For the worst cannibalization cases, which page should be the primary one and what should happen to the others — merge, redirect, or rewrite?

---

## AI Overviews: CTR drop despite stable rankings

> Are Google AI Overviews hurting my click-through rate on yourdomain.com? Compare queries that show an AI Overview vs. those that don't.

Claude calls `ai_overviews_impact` and isolates the CTR delta between queries with and without AI Overview appearances at the same position range.
