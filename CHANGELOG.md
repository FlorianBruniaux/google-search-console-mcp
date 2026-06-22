# Changelog

## [0.3.0] - 2026-06-22

Phase 2: 6 new GA4 tools, new dependency, new environment variable.

### Added

- `ga4_organic_landing_pages(start_date, end_date, limit)`: sessions, engaged sessions, bounce rate, average session duration, conversions and revenue for organic landing pages. Uses the `sessionMedium=organic` filter on `landingPagePlusQueryString`
- `ga4_traffic_sources(start_date, end_date)`: sessions and conversions broken down by channel group, source and medium
- `ga4_page_performance(start_date, end_date, page_path)`: 7 metrics per page path (page views, active users, average session duration, engagement rate, bounce rate, conversions, revenue). Optional `page_path` parameter adds a CONTAINS filter
- `ga4_realtime()`: active users right now, by screen name, country and device. No date range, uses `run_realtime_report` directly
- `ga4_user_behavior(start_date, end_date)`: single `batch_run_reports` call returning three breakdowns (by device, by country top 20, by user type new/returning)
- `ga4_conversion_funnel(start_date, end_date, event_name)`: two sequential `run_report` calls. First lists pages with conversions > 0; second lists events, optionally filtered by exact event name
- New dependency: `google-analytics-data>=0.18.0` (Google Analytics Data API v1beta, protobuf-based client)
- New environment variable: `GA4_PROPERTY_ID` (numeric property ID, e.g. `123456789`). Validated lazily on first GA4 tool call, never at startup. GSC-only users are not affected
- `get_ga4_service()` and `get_ga4_property_id()` in `auth.py`, reusing the same `_resolve_creds` path as GSC and Indexing clients

### Changed

- Tool count: 24 → 30

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
