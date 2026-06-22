# Changelog

## [0.2.0] - 2026-06-22

Phase 1: 6 new tools, no new dependencies.

### Added

- `seo_striking_distance(site, days, min_impressions)`: queries in positions 8-15 sorted by impressions desc. Separate band from `quick_wins` (4-15), intended for queries one push away from page 1
- `seo_cannibalization(site, days, min_impressions)`: detects queries split across multiple pages using an HHI conflict score (`1 - sum(share²)`). Zero-click groups use uniform `1/n` fallback to avoid division by zero. Filters on per-query total impressions, not per-page
- `seo_lost_queries(site, days)`: flags queries with a click drop ≥ 80% vs the previous period, requiring at least 5 previous clicks. Iterates over the previous period to catch fully-vanished queries. Same two-window no-lag pattern as `traffic_drops`
- `analytics_anomalies(site, days, threshold)`: Z-score anomaly detection on daily clicks via `statistics.pstdev`. Returns `anomalies = []` when std is zero (constant or all-zero series) to handle low-traffic sites safely
- `sitemaps_delete(site, sitemap_url)`: deletes a sitemap with a safety check before any API call (URL must end with `.xml` or contain `/sitemap`, raises `ValueError` otherwise)
- `sitemaps_get(site, sitemap_url)`: fetches a single sitemap resource and normalises it to the same flat shape as `list_sitemaps` (warnings and errors coerced to int)
- 62 new tests (35 SEO, 15 sitemaps, 9 analytics anomalies): all mocked, no API calls

### Changed

- Tool count: 18 → 24

## [0.1.0] - 2026-06-20

Initial release.

### Added

- 18 MCP tools across 6 categories: meta, properties, analytics, SEO, inspection, indexing, sitemaps
- `submit_batch` using true HTTP multipart batch via `new_batch_http_request()`, chunked at 100 URLs per request. Avoids the late-binding closure bug with a `_make_callback(url)` factory pattern
- Dual OAuth scope architecture: separate clients for GSC (`auth/webmasters`) and Indexing API (`auth/indexing`), because the Indexing API rejects webmasters tokens
- OAuth flow with token stored as JSON (`google.oauth2.credentials.Credentials.to_json()`) instead of pickle
- Service Account support as an alternative to OAuth (set `GSC_SERVICE_ACCOUNT_PATH`)
- Exponential backoff retry on HTTP 429/500/502/503/504 via `with_retry()` decorator, no retry on 404
- In-memory quota tracker (`QuotaTracker`) with configurable limit and warn threshold (warns at 180/200 by default)
- `with_meta()` wrapper on all tool outputs: every response includes a `_meta` block with tool name and call parameters, so Claude has full context on what was fetched
- `quick_wins` tool scoring CTR opportunity vs benchmark by SERP position
- `check_indexing_issues` categorizing URLs into `not_indexed`, `robots_blocked`, `fetch_error`, `canonical_issue`, `indexed`
- `traffic_drops` diagnosing drops as `ranking_loss`, `ctr_collapse`, or `demand_decline`
- Full test suite: 52 tests, fully mocked, no Google API calls required
