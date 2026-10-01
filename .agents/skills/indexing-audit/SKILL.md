---
name: indexing-audit
description: Inspect Google URL indexing states for a bounded sample, with raw coverage and fetch evidence. Use for pages not indexed, crawl or robots blocks, unknown URL status, and canonical mismatches. Déclencheurs français : page non indexée, découverte non indexée, problème d'indexation, Google ne crawle pas cette URL.
---

# Indexing Audit

Inspect specific URLs and report the sample boundary. The available URL Inspection tools do not provide a property-wide indexation inventory.

## Steps

1. Call `list_properties` and select the exact `site` property. Done when the property identity is recorded.
2. Choose URLs from the user's list, a sitemap, or `get_search_analytics` with `dimensions=["page"]`. If using Search Analytics, request enough rows to select a sample, then sort the returned rows locally by impressions. The API can omit rows, so this is not necessarily the site's global top 20. Include URLs without search data when that is the question. Done when the sample source, selection rule, and size are stated.
3. Call `batch_url_inspection` in batches of at most 10 URLs. `check_indexing_issues` also accepts at most 10 URLs and cannot produce a site-wide count. Done when every selected URL has an inspection response or a reported API failure.
4. For each URL, preserve `verdict`, `coverage_state`, `page_fetch_state`, `robots_txt_state`, `indexing_state`, Google and user canonicals, and last crawl. Treat `PAGE_FETCH_STATE_UNSPECIFIED` as unknown, not an HTTP fetch error. A missing last crawl or canonical is missing evidence. Done when each category follows the raw fields without inference from a Search Analytics row.
5. Check public HTTP response, robots, and canonical for a URL before recommending a site change. Reinspect after a correction; Google indexing itself may remain `UNKNOWN` until a later crawl. Done when each proposed change has a concrete failure and a verification step.

## Output

Report inspected URL count and selection source before the table: URL | GSC verdict | Coverage | Fetch | Canonical | Last crawl | Action. Separate confirmed blocks and failures from unknown or merely excluded states. Do not extrapolate sample counts to the whole property.
