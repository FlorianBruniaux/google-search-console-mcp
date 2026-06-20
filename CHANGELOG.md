# Changelog

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
