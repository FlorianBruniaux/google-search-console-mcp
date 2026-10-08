# Architecture

## Overview

gsc-mcp is a FastMCP server exposing 82 source tools over the Model Context Protocol. Each tool is a plain Python function returning a JSON string. The server and CLI derive their command surface from `registry.TOOLS`; an import-time assertion keeps that registry aligned with `properties._ALL_TOOLS`.

## File structure

```
src/gsc_mcp/
├── server.py          # Entry point. Registers every function from registry.TOOLS
├── registry.py        # Single source of truth for the 82 source MCP and CLI tools
├── cli.py             # Flag-only CLI generated from registry function signatures
├── auth.py            # Google service helpers, GA4 property resolver, Bing env key reader
├── constants.py       # Scopes, quota limits, CTR benchmarks by SERP position
├── meta.py            # with_meta(data, tool, params): wraps every tool output
├── retry.py           # with_retry() decorator: exponential backoff on retryable HTTP errors
├── quota.py           # QuotaTracker: in-memory counter for Indexing API calls
├── providers/
│   ├── base.py        # SearchMetricRow/Batch and the common provider protocol
│   ├── google.py      # Google Search Console metrics adapter
│   └── bing.py        # Redacted Bing JSON/HTTP client and metrics adapter
└── tools/
    ├── properties.py  # 3 capability and GSC property tools
    ├── analytics.py   # 10 GSC analytics tools + shared fetch/date helpers
    ├── seo.py         # 8 SEO analyses; 3 support Bing and 4 refuse unsupported Bing contracts
    ├── inspection.py  # inspect_url, batch_url_inspection, check_indexing_issues
    ├── indexing.py    # submit_url, submit_batch, indexnow_submit
    ├── sitemaps.py    # list_sitemaps, submit_sitemap, sitemaps_get, sitemaps_delete, sitemap_audit
    ├── ga4.py         # 8 GA4 tools + _build_dimension_filter helper
    ├── cross.py       # 4 GSC+GA4 tools + _normalize_url helper
    ├── crux.py        # 3 Chrome UX Report tools via httpx
    ├── technical.py   # 5 schema, AI visibility, GBP and PageSpeed tools
    ├── drift.py       # 3 persisted SEO drift tools
    ├── content.py     # 5 on-page content and technical audits
    ├── links.py       # 2 internal-link tools
    ├── bing_analytics.py   # 6 Bing performance/backlink reads
    ├── bing_webmaster.py   # 9 Bing reads + 4 guarded writes
    └── search_compare.py   # 1 evidence-bounded Google/Bing comparison
```

## Google clients, Bing transport and IndexNow

The server has three independent API clients, each with its own scope and token file:

- GSC analytics and inspection: `https://www.googleapis.com/auth/webmasters` (client: `searchconsole/v1`)
- Indexing API: `https://www.googleapis.com/auth/indexing`
- GA4 (Analytics Data API): `https://www.googleapis.com/auth/analytics.readonly`

`auth.py` exposes three independent functions (`get_searchconsole_service()`, `get_indexing_service()`, `get_ga4_service()`) that each resolve credentials for their respective scope, either from a Service Account file or from a cached OAuth token stored per-scope in the OS user data directory.

The same Service Account JSON can serve all three APIs: add the SA email (`client_email` field) as a Viewer in GSC and in GA4 Property Access Management. No separate key file needed.

Bing uses a separate `BING_WEBMASTER_API_KEY` read from the process environment. This is a user-level key: one value can access every verified site visible to that Bing account, while each tool receives its target `site`. The key is added only inside `BingWebmasterClient`; it is never accepted as a tool argument or returned in metadata or errors.

`BingWebmasterClient` calls the Bing JSON/HTTP endpoint with method allowlists, no redirects, a 15-second operation deadline and bounded retry for 429/5xx. Remote errors are reduced to status, method and a sanitized code. The client does not serialize response bodies or request parameters into exceptions.

IndexNow is not Bing Webmaster auth. `indexnow_submit` receives a separate key as an argument, and that key must be verifiable on each target host or subdomain. The repository does not consume an `INDEXNOW_KEY` environment variable.

## Common search metrics contract

`providers/base.py` defines the minimal cross-engine row: date, query, page, clicks, impressions, CTR, position and `provider_metrics`. Google and Bing adapters retain their own position semantics. Bing stores `avg_click_position` and `avg_impression_position` in `provider_metrics`; date rows expose no position.

The Bing adapter supports one dimension at a time: query, page or date. It filters returned rows to the requested local bounds but sets `window_exact=False` because the API does not accept arbitrary date bounds. Country, device and bulk page-query dimensions are explicitly unsupported. Cross-engine click and impression deltas are emitted only when both providers expose equal exact observed windows. Positions remain side by side.

The redacted live canary verified 15 of 17 Bing read methods. `GetKeywordStats` and `GetRelatedKeywords` returned HTTP 400 and have no registered tools. The public Bing API also does not expose the full URL Inspection or AI Performance interface.

## GA4 pattern: protobuf objects, not dicts

Unlike the GSC client (which uses `googleapiclient.discovery` and plain Python dicts), the GA4 client (`BetaAnalyticsDataClient` from `google-analytics-data`) uses protobuf request objects. Requests are constructed with typed classes from `google.analytics.data_v1beta.types`:

```python
from google.analytics.data_v1beta.types import RunReportRequest, Dimension, Metric, DateRange

response = client.run_report(RunReportRequest(
    property="properties/123456789",
    dimensions=[Dimension(name="pagePath")],
    metrics=[Metric(name="sessions")],
    date_ranges=[DateRange(start_date="28daysAgo", end_date="today")],
))
```

Row values are accessed as `row.dimension_values[i].value` and `row.metric_values[j].value` (always strings). The helpers `_f()` and `_i()` in `ga4.py` coerce them to float/int with a safe fallback to 0.

For `ga4_user_behavior`, a single `BatchRunReportsRequest` wraps three sub-requests. The `property` field goes on the wrapper, not on each sub-request. The response exposes `response.reports[0|1|2]`.

The `GA4_PROPERTY_ID` environment variable accepts either a bare numeric ID (`123456789`) or the full resource name (`properties/123456789`). `get_ga4_property_id(override=None)` normalises it and raises `RuntimeError` if absent and no override is passed, validated lazily (first tool call, never at startup).

All 8 GA4 tools and the 4 GSC+GA4 cross tools accept an optional `property_id: str = None` parameter. When provided, it is forwarded to `get_ga4_property_id(override=property_id)` and takes precedence over the env var. This allows querying multiple GA4 properties from a single MCP instance without config changes.

Token files are JSON, not pickle. `google.oauth2.credentials.Credentials` provides `.to_json()` and `.from_authorized_user_info()` for round-tripping safely.

## True HTTP batch for the Indexing API

The key technical improvement over [Suganthan-Mohanadasan/Suganthans-GSC-MCP](https://github.com/Suganthan-Mohanadasan/Suganthans-GSC-MCP) is in `tools/indexing.py`.

Suganthan's implementation sends one HTTP request per URL in a `for` loop. For 100 URLs that is 100 separate HTTPS round trips.

`submit_batch` here uses `service.new_batch_http_request()`, which bundles up to 100 individual requests into a single `multipart/mixed` HTTP request sent to `indexing.googleapis.com/batch`. The response is a single multipart body that the client library demultiplexes, calling a per-request callback for each result.

```python
def _make_callback(results: list, url: str):
    def callback(request_id, response, exception):
        if exception:
            results.append({"url": url, "status": "error", "error": str(exception)})
        else:
            results.append({"url": url, "status": "submitted"})
    return callback
```

The `_make_callback(url)` factory is intentional. A naive closure inside a loop would capture `url` by reference, so all callbacks would record the last URL in the loop. The factory captures it by value at construction time.

For more than 100 URLs, `_submit_batch_impl` loops over 100-item chunks, creating one batch request per chunk.

## Output format

Every tool returns `json.dumps(with_meta(data, tool=..., params=...))`. The `_meta` block gives Claude the name of the tool that produced the data and the call parameters, which helps it reason about what it has already fetched and avoid redundant calls.

```json
{
  "count": 3,
  "properties": [...],
  "_meta": {
    "tool": "list_properties",
    "params": {}
  }
}
```

## Bing analysis and mutation boundaries

`quick_wins`, `seo_striking_distance` and `prune_candidates` accept `engine="bing"` and consume normalized Bing rows. A missing Bing position excludes a row only from analyses that require position. `prune_candidates` can still classify a page from measured clicks and impressions, but it never treats missing impressions as proof that the page is not indexed.

Four analyses return structured refusals without a provider call: `traffic_drops` and `seo_lost_queries` require exact adjacent periods; `check_alerts` and `seo_cannibalization` require the bulk page-query dimension. No N+1 fallback synthesizes those missing contracts.

The Bing family has 15 reads and 4 writes. Every write validates a public target URL and requires the target to share the site's origin. `bing_url_submit` and `bing_feed_submit` can report an accepted request, with `indexed=false` and `indexed_semantics="not_verified"`. `bing_urls_submit_batch` currently refuses before `SubmitUrlBatch` because `DailyQuota` and `MonthlyQuota` are observed integers whose total-versus-remaining semantics remain `UNKNOWN`. `bing_feed_remove` requires `confirm=true`, a feed-shaped URL and a pre-existing matching feed.

Live-runtime evidence remains bounded. Data freshness is unknown; a non-empty `GetCrawlIssues` item shape has not been observed; nested backlink item schemas and `RemoveFeed` remain `UNVERIFIED_RUNTIME`. No Bing write was executed against a production site during validation. HTTP 200, an accepted submission or a last crawl date does not prove current indexation or an SEO effect.

## Retry

`retry.py` provides a `with_retry(max_retries=3, base_delay=1.0)` decorator. It catches two families of transient errors and retries with exponential backoff (`base_delay * 2^attempt`):

- `googleapiclient.errors.HttpError` on status codes `{429, 500, 502, 503, 504}`: GSC and Indexing API errors
- `google.api_core.exceptions` subtypes `ServiceUnavailable`, `ResourceExhausted`, `InternalServerError`, `BadGateway`, `RetryError`: GA4 gRPC errors

It does not retry on 4xx errors other than 429 (those are client errors, not transient).

The decorator is applied at the function level rather than the tool level. `_fetch_rows` in `analytics.py` is the main call site: since all analytics and SEO tools use it as their data layer, a single `@with_retry()` there covers those tools entirely. GA4 tools each carry their own `@with_retry()` since they call `client.run_report()` / `client.batch_run_reports()` directly. Properties, inspection, and sitemap tools are also individually decorated.

## Quota tracking

`QuotaTracker` is a simple in-memory counter with a configurable limit and warn threshold. The Indexing API has a default quota of 200 requests per day. `submit_batch` calls `quota.check(n)` before sending (raises `RuntimeError` if the batch would exceed the limit) and `quota.consume(n)` after a successful batch. When `quota.should_warn()` returns true, the tool adds `"quota_warning": true` to the JSON response.

The tracker resets on server restart. For persistent quota tracking across sessions, a file-backed counter would be needed.

## Why Python

The Google API Python client (`google-api-python-client`) is the canonical, officially maintained client for these APIs. It exposes `service.new_batch_http_request()` natively, which is what makes true HTTP batching possible without implementing the `multipart/mixed` wire format by hand. The Go client library (`google.golang.org/api`) and the Rust ecosystem for Google APIs rely on unofficial or generated clients that do not provide this abstraction.

FastMCP also has first-class Python support with a decorator-based API that keeps tool registration minimal. The only real trade-off vs a compiled language is startup time (a few hundred milliseconds), which does not matter for a locally-run MCP server called interactively.

## SEO analysis patterns (v0.2)

Three algorithmic patterns introduced in Phase 1 reuse `_fetch_rows` and `_date_range` from `analytics.py` without adding dependencies.

**Two-period comparison.** `seo_lost_queries` mirrors `traffic_drops`: two adjacent windows of `days` length, both ending at `date.today()` with no GSC reporting lag. Iterating over the previous period (not the current) captures queries that disappeared entirely. The `prev_clicks >= 5` guard on the denominator prevents division by zero and filters low-signal noise.

**HHI conflict score.** `seo_cannibalization` queries with `dimensions=["query","page"]` so each row carries both keys. Rows are grouped by query; for each group with more than one page, the Herfindahl-Hirschman Index measures concentration: `hhi = sum((clicks_i / total_clicks)^2)` and `conflict_score = 1 - hhi`. A score near 0 means one page dominates (no real conflict); near 1 means clicks are split evenly. When `total_clicks == 0` the function falls back to `hhi = 1/n` (uniform share), avoiding division by zero while still surfacing impression-heavy splits. Only groups with `conflict_score > 0.1` are returned.

**Z-score anomaly detection.** `analytics_anomalies` queries with `dimensions=["date"]` to get a daily click series, then uses `statistics.pstdev` (population standard deviation, not sample) because the series is a complete known dataset rather than a sample from a larger population. The guard `if std == 0: return []` handles flat series and all-zero traffic, both common on low-traffic sites, without raising `ZeroDivisionError`.

## Cross-platform pattern (v0.2 Phase 3)

In the unreleased source checkout, `traffic_health_check` resolves concrete GSC dates and passes them to GA4. Each source reports availability, requested/reported windows, filters and coverage. The ratio requires compatible covered inputs; empty responses remain null and explicit-zero rows stay zero. Calendar boundaries and property mapping remain unverified. Other combined reports still use independent windows.

`ga4_ai_referrals` checks property-specific dimension/metric compatibility and reads at most 10,000 source/medium/landing-page rows with sessions, engaged sessions and `keyEvents`. Confirmed source rules are dated; candidate sources are excluded from confirmed totals. All-source shares require complete unrestricted coverage. The output measures attributed visits, not citations. See the [evidence contract](https://search-console.bruniaux.com/docs/evidence-and-safety/).

`with_meta` adds concrete per-field JSON Pointer evidence descriptors from a tool/path inventory. No whole-output basis is inferred for mixed reports, and no numeric confidence is fabricated. Existing metrics and source identities retain their meanings. The shared HTML trust observer does not execute or rewrite fetched instructions; a narrow challenge detector protects schema assessment only.

`cross.py` does not call the Google APIs directly. It calls the high-level tool functions from `analytics.py` and `ga4.py`, parses their JSON string output with `json.loads`, and then joins the results.

The join key is `_normalize_url(url)`, a small helper that strips scheme, host, query string and trailing slash so that a GSC absolute URL (`https://example.com/blog/`) and a GA4 landing page path (`/blog?ref=home`) resolve to the same key (`/blog`).

`ga4_organic_landing_pages` does not expose `engagement_rate` directly (it exposes `engaged_sessions` and `sessions`). The cross module derives it as `engaged_sessions / sessions`, which is the GA4 native formula. This avoids modifying the Phase 2 tool surface.

`opportunity_score` weights three signals: impressions (log-scaled, 10x), engagement rate (100x, linear), and conversions (log-scaled, 20x). The log scaling compresses high-impression pages while still surfacing low-traffic pages with strong engagement. `None` fields fall back to 0 via `(value or 0)`, so GSC-only and GA4-only pages score on the signals they have.

Tests for cross tools patch `gsc_mcp.tools.cross.get_search_analytics` and `gsc_mcp.tools.cross.ga4_organic_landing_pages` to return JSON strings, matching what the actual functions return. The GA4 protobuf fixtures from `conftest.py` are not needed.

## CrUX tools (v0.5)

`crux.py` calls the Chrome UX Report API via `httpx` (not the Google API Python client, which does not cover this API). Two endpoints: `:queryRecord` for the latest snapshot, `:queryHistoryRecord` for 25 weeks of weekly p75 series. Both require a plain Google API key (`CRUX_API_KEY`), not a service account or OAuth token. The key is read from env by `_crux_api_key()`, which raises `RuntimeError` if absent.

A 404 response means the URL has insufficient field data; `crux_page_vitals` returns `verdict="not_enough_data"` without raising. The `form_factor` parameter (default `"ALL_FORM_FACTORS"`) adds a `formFactor` key to the POST body only when not the default, matching the CrUX API contract.

CWV thresholds used for rating:

| Metric | Good | Poor |
|--------|------|------|
| LCP | <= 2500ms | > 4000ms |
| INP | <= 200ms | > 500ms |
| CLS | <= 0.1 | > 0.25 |
| FCP | <= 1800ms | > 3000ms |
| TTFB | <= 800ms | > 1800ms |

## sitemap_audit (v0.5)

`sitemap_audit` in `sitemaps.py` fetches XML via `httpx` and parses with `defusedxml.ElementTree` (not stdlib `xml.etree.ElementTree`). The stdlib parsers are vulnerable to XXE (external entity injection) and billion-laughs attacks when processing untrusted external XML. `defusedxml` is a drop-in replacement that disables those features.

For sitemap index files, child sitemap URLs are validated against the origin of the parent sitemap before fetching. This prevents SSRF: a poisoned sitemap index could otherwise point `<loc>` entries at `http://169.254.169.254/` (AWS metadata) or internal services. `follow_redirects=False` on the httpx client prevents redirect-based SSRF pivots.

The cross-reference uses `get_search_analytics` with `dimensions=["page"]` and `row_limit=5000` over 90 days. URLs are normalised with `.rstrip("/").lower()` before set intersection. Missing sample is capped at 20 items to keep the response payload bounded.

## schema_validate (v0.5)

`technical.py` uses `html.parser` (Python stdlib `HTMLParser`) to extract JSON-LD blocks, avoiding an external dependency. The `_JsonLdExtractor` subclass tracks when it's inside a `<script type="application/ld+json">` tag and accumulates text chunks, then calls `json.loads` on the joined string at the closing tag. JSON-LD blocks that contain a top-level array are expanded so each item is validated individually.

The tool makes no Google API calls and requires no auth. `httpx` is used for the page fetch with `follow_redirects=True` (legitimate redirects are expected on public URLs).

## Inspirations

- [AminForou/mcp-gsc](https://github.com/AminForou/mcp-gsc): auth architecture, SEO analytics tooling, fail-fast env var pattern
- [Suganthan-Mohanadasan/Suganthans-GSC-MCP](https://github.com/Suganthan-Mohanadasan/Suganthans-GSC-MCP): Indexing API integration, `with_meta()` anti-hallucination pattern, dual OAuth scope awareness
