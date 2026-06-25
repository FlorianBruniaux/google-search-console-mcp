---
name: content-opportunities
description: Find content optimization targets across two zones: striking distance
  (positions 4-10) and page-two quick wins (positions 11-20). Use when asked for
  content ideas or optimization opportunities.
---

# Content Opportunities

Surface content optimization targets across two opportunity zones, ordered by ROI.

## Steps

### Zone 1: Striking Distance (positions 4-10, highest ROI)

1. Call `list_properties` to confirm the exact `site_url`.
2. Call `seo_striking_distance` to get queries and pages ranked 4-10. One position gained at this range has a significant traffic impact.
3. Call `quick_wins` for an overview of the fastest wins across the property.

### Zone 2: Page Two Quick Wins (positions 11-20)

4. Call `get_advanced_search_analytics` with:
   - `dimensions=query,page`
   - `sort_by=impressions`, `sort_direction=descending`
   - `row_limit=1000`
   - `start_date` = 28 days ago, `end_date` = today
5. Filter the results to keep only rows where:
   - `position` is between 11 and 20 (page 2, just below the fold)
   - `impressions` > 100 (meaningful search volume)
   - `ctr` < 0.03 (below average for these positions)
6. Sort the filtered set by `impressions` descending. Return the top 20 rows.

## Output format

**Zone 1 table**: Query | Page | Position | Impressions | CTR | Est. clicks at pos 3

**Zone 2 table**: Query | Page | Position | Impressions | CTR | Opportunity Score

Opportunity Score = `impressions × (0.05 - ctr)` (rough estimate of clicks gained if CTR reaches 5%).

Follow each table with specific recommendations:
- Title and meta description optimization
- Whether to merge with a better-ranking page
- Whether to add internal links to boost the page
- For Zone 1 specifically: whether to add more depth, FAQ schema, or structured data
