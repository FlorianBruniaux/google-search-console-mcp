# SERP Overlap Clustering Methodology

Source: adapted from claude-seo (Lutfiya Miller, MIT). This documents the algorithm
used for identifying keyword clusters via search result page overlap.

## Concept

Two keywords belong to the same cluster when they share a significant number of
URLs in their top-10 Google results. A higher overlap suggests the keywords satisfy
the same search intent and should target the same page.

## Algorithm

1. For each keyword pair (A, B), fetch their top-10 organic SERP results.
2. Compute overlap: `overlap = |top10(A) intersection top10(B)|` (count of shared URLs).
3. Apply threshold: pairs with `overlap >= 3` are considered "same cluster".
   Threshold of 3 is the default from the v1 implementation; adjust for niche
   verticals where SERPs are more concentrated.
4. Build a graph: keywords are nodes, edges exist where `overlap >= threshold`.
5. Detect connected components in the graph; each component is a cluster.

## Optimization notes

- Pairwise comparison is O(n^2). For more than 200 keywords, pre-filter by
  seed keyword or topic to avoid excessive API calls.
- Cache SERP results to avoid re-fetching; SERPs are stable for 24-48 hours.
- The overlap algorithm assumes organic results; ads and rich results are excluded.

## Limitations

- Requires a SERP data source (DataForSEO, Semrush, WebSearch API). gsc-mcp does
  not include a SERP API connection, so this clustering is not directly implemented.
  This document serves as a methodology reference for external implementation.
- Local SERPs vary by geographic location; run checks from the target market.
- Volatile queries (news, trending) produce unstable overlap; filter by query
  stability before clustering.

## Relationship to gsc-mcp tools

The `seo_cannibalization` tool in gsc-mcp detects pages that already compete for
the same queries using GSC click/impression data. SERP overlap clustering is
complementary: it identifies potential cannibalization from SERP similarity before
you have traffic data.
