---
name: schema-audit
description: Audit structured data (schema markup) across the top pages to surface
  errors blocking rich results eligibility. Use when asked about rich results, schema
  errors, or structured data health.
---

# Schema Audit

Validate structured data on the site's most-visible pages to find errors that block rich results eligibility.

## Steps

1. Call `list_properties` to confirm the `site_url`.
2. Call `get_search_analytics` with `dimensions=page`, `sort_by=impressions`, `row_limit=20` to get the top 20 pages by impression volume.
3. For each page URL, call `schema_validate` to check structured data validity.
4. Categorize results:
   - Valid: schema present and error-free
   - Warnings: schema present with non-critical issues
   - Errors: schema present but invalid (blocks rich results)
   - No schema: no structured data detected on the page
5. Prioritize errors and missing schema on pages with the highest impressions.

## Output format

**Summary line**: X valid / Y warnings / Z errors / W no-schema out of 20 pages.

**Issues table**: Page URL | Schema type | Status | Issue | Impressions

**Prioritized fixes**:
1. Critical: errors on high-traffic pages blocking rich results
2. High: missing schema on pages where rich results would apply (Article, Product, FAQ, Review)
3. Medium: warnings reducing rich result quality
4. Low: pages with no schema and low traffic

For each fix, specify which schema type to add or correct and which properties are required.
