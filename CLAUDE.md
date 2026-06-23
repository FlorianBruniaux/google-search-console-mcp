# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Docs

- `docs/architecture.md`: full architectural reference (API clients, GA4 protobuf pattern, batch implementation, retry/quota internals, v0.5 additions)
- `docs/google-setup.md`: GCP project setup, enabling APIs, service account creation, GSC and GA4 permission configuration
- `docs/starter-prompt.md`: ready-to-use audit prompts for Claude Desktop users (full audit, quick check, single-page, reindexing, CrUX, schema)

## Commands

```bash
# Requires Python 3.11+
python3 --version  # must be 3.11 or higher

# Install (dev mode with test deps)
pip install -e ".[dev]"

# Run the MCP server
gsc-mcp
# or
python -m gsc_mcp.server

# Run all tests (222 tests, fully mocked)
pytest tests/ -v

# Run a single test file
pytest tests/test_analytics.py -v

# Run a specific test by name
pytest tests/ -k "test_submit_batch" -v
```

## Architecture

**Entry point**: `src/gsc_mcp/server.py` creates a `FastMCP("gsc-mcp")` instance and registers all 36 tools via `mcp.tool()()`. No dynamic discovery; every tool is explicitly imported and registered here.

**Auth layer** (`auth.py`): Three separate credential pairs (GSC API `searchconsole/v1`, Indexing API `indexing/v3`, GA4 `analytics.readonly`). Resolution order: if `GSC_SERVICE_ACCOUNT_PATH` is set, use service account credentials. Otherwise, fall through to OAuth with token cached as JSON (not pickle) at the OS user data dir (`~/Library/Application Support/gsc-mcp/` on macOS). Token files are written `chmod 0o600`; the directory is created with `0o700`. `get_ga4_property_id(override=None)` accepts an optional override string that bypasses `GA4_PROPERTY_ID`, enabling per-call multi-property support.

**Tools** (`src/gsc_mcp/tools/`): Ten modules, each owns a logical domain:
- `analytics.py`: 6 GSC search analytics tools
- `seo.py`: 6 SEO intelligence tools (quick wins, drops, cannibalization, anomalies)
- `inspection.py`: URL inspection + batch + issue categorization
- `indexing.py`: Indexing API (submit_url, submit_batch)
- `sitemaps.py`: sitemap management + `sitemap_audit` (defusedxml, SSRF-safe)
- `properties.py`: list/get GSC properties, `get_capabilities`
- `ga4.py`: 6 GA4 tools, all accept `hostname` and `country` filters via `_build_dimension_filter`
- `cross.py`: 2 cross-platform GSC+GA4 tools (also accept `hostname` and `country`)
- `crux.py`: 2 CrUX tools (Core Web Vitals via Chrome UX Report API)
- `technical.py`: `schema_validate` (JSON-LD extraction + validation, no auth needed)

**CrUX tools** (`crux.py`): `crux_page_vitals` and `crux_history` call the Chrome UX Report API via `httpx` (POST to `:queryRecord` / `:queryHistoryRecord`). Require `CRUX_API_KEY` (a plain Google API key, not a service account). The Chrome UX Report API must be enabled in the GCP project. A 404 from the API means not enough field data for that URL, returned as `verdict="not_enough_data"`.

**sitemap_audit** (`sitemaps.py`): fetches a sitemap via `httpx`, parses XML with `defusedxml.ElementTree` (prevents XXE and billion-laughs). Handles sitemap index files with one level of recursion; child sitemap URLs are validated against the parent's origin before fetching (`follow_redirects=False`, SSRF protection). Cross-references declared URLs against 90 days of GSC data. Returns `missing_sample` capped at 20 URLs. Verdicts: `empty` | `fetch_error` | `partial` (>20% URLs absent from GSC) | `healthy`.

**schema_validate** (`technical.py`): fetches any public URL, extracts `<script type="application/ld+json">` blocks with `html.parser` (stdlib), validates required fields per schema type (Article, LocalBusiness, FAQPage, Product, WebSite, BreadcrumbList, SoftwareApplication), and suggests missing schemas from URL path patterns (`/faq` → FAQPage, `/blog/` → BlogPosting, etc.). No auth required.

**Cross-platform pattern** (`cross.py`): `traffic_health_check` and `page_analysis` compose functions from `analytics.py` and `ga4.py`. They call those functions, parse their JSON strings with `json.loads`, then join on `_normalize_url` (strips scheme/host/query/trailing-slash so GSC absolute URLs and GA4 paths match). `engagement_rate` is derived as `engaged_sessions/sessions`.

**Output contract** (`meta.py`): Every tool wraps its response dict with `with_meta(data, tool=..., params=...)`, which appends a `_meta` block (`{"tool": "<name>", "params": {...}}`). Data keys are spread at the top level (not nested under `"data"`). Any new tool must follow this pattern.

**Retry** (`retry.py`): `@with_retry(max_retries=3, base_delay=1.0)` wraps Google API calls. Catches two families of transient errors:
- `googleapiclient.errors.HttpError` on status codes `{429, 500, 502, 503, 504}`
- `google.api_core.exceptions` subtypes: `ServiceUnavailable`, `ResourceExhausted`, `InternalServerError`, `BadGateway`, `RetryError` (GA4 gRPC errors)

Applied to `_fetch_rows` in `analytics.py` (covers all GSC analytics/SEO tools) and directly on each GA4 tool. Does not retry on other 4xx errors.

**Quota tracking** (`quota.py` + `indexing.py`): `QuotaTracker` is a module-level singleton in `indexing.py` that tracks Indexing API usage within a single process lifetime (200 req/day limit, warns at 180). It does not persist across restarts.

**Batching** (`indexing.py`): `submit_batch` uses `svc.new_batch_http_request()` chunked at 100 URLs per HTTP request. True multipart batch, not a sequential loop.

## Adding a new tool

1. Implement the function in the relevant `tools/` module (or create a new one).
2. Decorate with `@with_retry()` if the tool calls a Google API directly.
3. Return `json.dumps(with_meta(data, tool="tool_name", params={...}))`.
4. Import the function in `server.py` and register it with `mcp.tool()(my_tool)`.
5. Add the tool name to `_ALL_TOOLS` in `properties.py` and update the `get_capabilities` docstring count.
6. Write tests in `tests/test_<module>.py`, mocking all Google API calls.

For GA4 tools that filter by hostname/country, use `_build_dimension_filter(hostname, country, base_filter)` from `ga4.py`. It returns `None` when both are `None` (backward-compatible), a single `FilterExpression` when only one is set, and an AND group (`FilterExpressionList`) when both are set.

## Test conventions

All tests are fully mocked (no real Google API calls). `tests/conftest.py` defines two shared fixtures:
- `mock_gsc_service`: MagicMock wired for `sites`, `searchanalytics`, `sitemaps`, `urlInspection`
- `mock_indexing_service`: MagicMock with a working `new_batch_http_request()` implementation that fires callbacks synchronously

Tests patch `get_searchconsole_service` / `get_indexing_service` / `get_ga4_service` at the call site (e.g., `gsc_mcp.tools.analytics.get_searchconsole_service`). GA4 tests use an `autouse` fixture to set `GA4_PROPERTY_ID`.

CrUX tests mock `httpx.Client` as a context manager (`client.__enter__` returns the mock itself, `client.get.side_effect` controls responses). `sitemap_audit` tests patch `gsc_mcp.tools.sitemaps.httpx.Client` and `gsc_mcp.tools.sitemaps.get_search_analytics` (module-level import, not lazy). `schema_validate` tests patch `httpx.Client` directly (module-level in `technical.py`).

## Environment variables

| Variable | Purpose |
|---|---|
| `GSC_SERVICE_ACCOUNT_PATH` | Path to service account JSON (preferred for automation) |
| `GSC_CREDENTIALS_PATH` | Path to OAuth Desktop client JSON (interactive OAuth flow) |
| `GSC_SKIP_OAUTH` | Set to `true` to skip OAuth fallback entirely (requires SA path) |
| `GA4_PROPERTY_ID` | Numeric GA4 property ID (e.g. `123456789`). Required for GA4/cross tools, validated lazily |
| `CRUX_API_KEY` | Google API key with Chrome UX Report API enabled in GCP. Required for `crux_page_vitals` and `crux_history`. Distinct from GSC/GA4 auth |
