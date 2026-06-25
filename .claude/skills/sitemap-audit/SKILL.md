---
name: sitemap-audit
description: Audit sitemap health and coverage across all submitted sitemaps. Use
  when asked about sitemap issues, submitted vs. indexed counts, or sitemap errors.
---

# Sitemap Audit

Audit all submitted sitemaps for a property and identify coverage gaps and errors.

## Steps

1. Call `list_properties` to confirm the exact `site_url`.
2. Call `list_sitemaps` to get all submitted sitemaps with their last download date, submitted URL count, and indexed URL count.
3. Call `sitemap_audit` for a detailed health report on each sitemap.
4. Call `check_indexing_issues` to compare sitemap submissions against actual indexed page counts across the property.
5. Flag any sitemap where the gap between submitted and indexed exceeds 20% as a priority issue.

## Output format

**Sitemap inventory table**: Sitemap URL | Type | Submitted | Indexed | Gap % | Last downloaded | Status

**Issues list** sorted by severity:
- Critical: sitemaps returning 404, parse errors, or not loading
- High: submitted/indexed ratio below 80%
- Medium: last downloaded more than 7 days ago (Google not re-fetching)
- Low: sitemaps with low coverage but low traffic impact

**Recommendations**: for each issue, one concrete action (re-submit, fix the URL, split the sitemap into smaller files, remove orphan URLs).
