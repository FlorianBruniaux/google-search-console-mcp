---
name: cannibalization-check
description: Detect keyword cannibalization, meaning queries where multiple pages compete
  for the same rankings. Use when asked about competing pages, keyword overlap, or
  cannibalization.
---

# Keyword Cannibalization Check

Identify queries where multiple pages on the same site are competing for rankings.

## Steps

1. Call `list_properties` to confirm the exact `site_url`.
2. Call `seo_cannibalization` to get a dedicated cannibalization report. This tool groups query+page combinations and surfaces the most severe conflicts directly, without manual filtering.
3. If `seo_cannibalization` returns limited results, supplement with `get_advanced_search_analytics` using `dimensions=query,page`, `sort_by=impressions`, `row_limit=1000`. Group rows by `query`: those with two or more distinct pages are candidates.
4. For each cannibalizing query, collect both page URLs with their individual clicks, impressions, CTR, and position.
5. Sort candidates by total impressions (most valuable conflicts first).
6. Limit the output to the top 20 most severe cases.

## Output format

For each cannibalization case:
- **Query**: the competing keyword
- **Pages**: list each URL with its metrics (clicks / impressions / CTR / position)
- **Severity**: High / Medium / Low based on impressions at stake
- **Recommendation**: which page to consolidate to (pick the one with better position or CTR), and whether to use a canonical, redirect, or content merge

Present as a markdown table followed by a prioritized action list.
