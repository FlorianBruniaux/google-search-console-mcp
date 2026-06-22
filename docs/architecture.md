# Architecture

## Overview

gsc-mcp is a FastMCP server exposing 24 tools over the Model Context Protocol. Each tool is a plain Python function returning a JSON string. The server registers all tools at startup and handles the MCP wire protocol via `mcp[cli]`.

## File structure

```
src/gsc_mcp/
├── server.py          # Entry point. Imports all tools, registers them on the FastMCP instance
├── auth.py            # get_gsc_service() and get_indexing_service() — two separate API clients
├── constants.py       # Scopes, quota limits, CTR benchmarks by SERP position
├── meta.py            # with_meta(data, tool, params) — wraps every tool output
├── retry.py           # with_retry() decorator — exponential backoff on retryable HTTP errors
├── quota.py           # QuotaTracker — in-memory counter for Indexing API calls
└── tools/
    ├── properties.py  # get_capabilities, list_properties, get_site_details
    ├── analytics.py   # 6 analytics tools + _fetch_rows / _date_range / _parse_row helpers
    ├── seo.py         # quick_wins, traffic_drops, check_alerts, seo_striking_distance, seo_cannibalization, seo_lost_queries
    ├── inspection.py  # inspect_url, batch_url_inspection, check_indexing_issues
    ├── indexing.py    # submit_url, submit_batch (via _submit_batch_impl)
    └── sitemaps.py    # list_sitemaps, submit_sitemap, sitemaps_get, sitemaps_delete
```

## Two API clients, two scopes

The most important design constraint is that the Google Search Console API and the Google Indexing API require **different OAuth scopes** and cannot share a token:

- GSC analytics and inspection: `https://www.googleapis.com/auth/webmasters`
- Indexing API: `https://www.googleapis.com/auth/indexing`

`auth.py` exposes two independent functions (`get_gsc_service()`, `get_indexing_service()`) that each resolve credentials for their respective scope, either from a Service Account file or from a cached OAuth token stored per-scope in the OS user data directory.

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

## Retry

`retry.py` provides a `with_retry(max_retries=3, base_delay=1.0)` decorator. It catches `googleapiclient.errors.HttpError` and retries on status codes `{429, 500, 502, 503, 504}` with exponential backoff (`base_delay * 2^attempt`). It does not retry on 404 (not found is not transient).

The tools do not currently apply `with_retry` automatically because the `@mcp.tool()` decorator wraps the function signature for Pydantic schema generation. Applying retry at the call site inside each tool is straightforward if needed.

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

## Inspirations

- [AminForou/mcp-gsc](https://github.com/AminForou/mcp-gsc): auth architecture, SEO analytics tooling, fail-fast env var pattern
- [Suganthan-Mohanadasan/Suganthans-GSC-MCP](https://github.com/Suganthan-Mohanadasan/Suganthans-GSC-MCP): Indexing API integration, `with_meta()` anti-hallucination pattern, dual OAuth scope awareness
