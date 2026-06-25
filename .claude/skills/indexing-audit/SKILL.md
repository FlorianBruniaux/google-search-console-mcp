---
name: indexing-audit
description: Audit indexing status with a site-wide overview first, then per-page
  deep-dive on top pages. Use when asked about crawling, indexing issues, or whether
  pages are indexed by Google.
---

# Indexing Audit

Audit the indexing health of a Google Search Console property: start with a site-wide count, then drill into the most-visible pages.

## Steps

1. Call `list_properties` to confirm the exact `site_url`.
2. Call `check_indexing_issues` to get a site-wide breakdown of valid pages, errors, and warnings. Note any coverage categories with high error counts (this surfaces systemic issues before the per-URL drill-down).
3. Call `get_search_analytics` with `dimensions=page`, `sort_by=impressions`, `row_limit=20` to identify the 20 most-visible pages.
4. Extract the page URLs from step 3.
5. Call `batch_url_inspection` with up to 10 URLs at a time (API limit). Run twice if needed to cover all 20 pages.
6. Categorize each URL by verdict:
   - ✅ **Indexed** (PASS)
   - ⚠️ **Soft 404 / Excluded**
   - ❌ **Not indexed / Blocked**
   - 🔍 **Canonical mismatch** (Google chose a different canonical)
7. For each issue, record the specific `coverageState`, `pageFetchState`, or `robotsTxtState` from the inspection.

## Output format

Start with a **site-wide summary** from step 2: total valid / total errors / total warnings.

Then present a prioritized action list for the top pages:

1. **Critical**: not indexed pages that have impressions (visibility being lost)
2. **High**: canonical mismatches on high-traffic pages
3. **Medium**: robots.txt or fetch blocks
4. **Low**: soft exclusions on low-traffic pages

Include a summary table: Page URL | Verdict | Issue | Recommended action.
