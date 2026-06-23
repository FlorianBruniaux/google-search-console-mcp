# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

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

# Run all tests
pytest tests/ -v

# Run a single test file
pytest tests/test_analytics.py -v

# Run a specific test by name
pytest tests/ -k "test_submit_batch" -v
```

## Architecture

**Entry point**: `src/gsc_mcp/server.py` creates a `FastMCP("gsc-mcp")` instance and registers all 36 tools via `mcp.tool()()`. No dynamic discovery; every tool is explicitly imported and registered here. Adding a new tool means: implement it in the relevant `tools/` module, import it in `server.py`, and register it.

**Auth layer** (`auth.py`): Three separate credential pairs: GSC API (`searchconsole/v1`), Indexing API (`indexing/v3`), and GA4 (`analytics.readonly`). Resolution order: if `GSC_SERVICE_ACCOUNT_PATH` is set, use service account credentials. Otherwise, fall through to OAuth with token cached as JSON (not pickle) at the OS user data dir (`~/Library/Application Support/gsc-mcp/` on macOS). Token files are written with `chmod 0o600`; the directory is created with `0o700`. `get_ga4_property_id(override=None)` accepts an optional override string that bypasses `GA4_PROPERTY_ID`, enabling per-call multi-property support.

**Tools** (`src/gsc_mcp/tools/`): Ten modules, each owns a logical domain:
- `analytics.py`: 6 GSC search analytics tools
- `seo.py`: 6 SEO intelligence tools (quick wins, drops, cannibalization, anomalies)
- `inspection.py`: URL inspection + batch + issue categorization
- `indexing.py`: Indexing API (submit_url, submit_batch)
- `sitemaps.py`: sitemap management + `sitemap_audit` (defusedxml, SSRF-safe)
- `properties.py`: list/get GSC properties, `get_capabilities`
- `ga4.py`: 6 GA4 tools, all accept `hostname` and `country` filters
- `cross.py`: 2 cross-platform GSC+GA4 tools
- `crux.py`: 2 CrUX tools (Core Web Vitals via Chrome UX Report API)
- `technical.py`: `schema_validate` (JSON-LD extraction + validation, no auth needed)

Every tool function is a plain Python function registered by `server.py`. All return JSON strings via `json.dumps(with_meta(...))`.

**CrUX tools** (`crux.py`): `crux_page_vitals` and `crux_history` call the Chrome UX Report API via `httpx` (POST to `:queryRecord` / `:queryHistoryRecord`). They require `CRUX_API_KEY` (a plain Google API key, not a service account). The Chrome UX Report API must be enabled in the GCP project. A 404 from the API means not enough field data for that URL, returned as `verdict="not_enough_data"`.

**sitemap_audit** (`sitemaps.py`): fetches a sitemap via `httpx`, parses XML with `defusedxml.ElementTree` (prevents XXE and billion-laughs attacks). Handles sitemap index files with one level of recursion; child sitemap URLs are validated against the parent's origin before fetching (`follow_redirects=False`). Cross-references declared URLs against 90 days of GSC data.

**schema_validate** (`technical.py`): fetches any public URL, extracts `<script type="application/ld+json">` blocks with `html.parser` (stdlib), validates required fields per schema type, and suggests missing schemas from URL path patterns. No auth required.

**Cross-platform pattern** (`cross.py`): `traffic_health_check` and `page_analysis` compose functions from `analytics.py` and `ga4.py`. They call those functions, parse their JSON strings with `json.loads`, then join on `_normalize_url` (strips scheme/host/query/trailing-slash so GSC absolute URLs and GA4 paths match). `engagement_rate` is derived as `engaged_sessions/sessions`.

**Output contract** (`meta.py`): Every tool wraps its response dict with `with_meta(data, tool=..., params=...)`, which appends a `_meta` block (`{"tool": "<name>", "params": {...}}`). Data keys are spread at the top level (not nested under `"data"`). Any new tool must follow this pattern.

**Retry** (`retry.py`): `@with_retry(max_retries=3, base_delay=1.0)` wraps Google API calls. Catches two families of transient errors:
- `googleapiclient.errors.HttpError` on status codes `{429, 500, 502, 503, 504}`
- `google.api_core.exceptions` subtypes: `ServiceUnavailable`, `ResourceExhausted`, `InternalServerError`, `BadGateway`, `RetryError` (covers GA4 gRPC errors)

Applied to `_fetch_rows` in `analytics.py` (covers all GSC analytics/SEO tools via the shared data layer) and directly on each GA4 tool. Does not retry on other 4xx errors.

**Quota tracking** (`quota.py` + `indexing.py`): `QuotaTracker` is a module-level singleton in `indexing.py` that tracks Indexing API usage within a single process lifetime (200 req/day limit, warns at 180). It does not persist across restarts; restarting the server resets the counter.

**Batching** (`indexing.py`): `submit_batch` uses `svc.new_batch_http_request()` chunked at 100 URLs per HTTP request. This is a true multipart batch, not a sequential loop. Callbacks collect per-URL results.

## Test conventions

All tests are fully mocked (no real Google API calls). `tests/conftest.py` defines two shared fixtures:
- `mock_gsc_service`: MagicMock wired for `sites`, `searchanalytics`, `sitemaps`, `urlInspection`
- `mock_indexing_service`: MagicMock with a working `new_batch_http_request()` implementation that fires callbacks synchronously

Tests patch `get_searchconsole_service` / `get_indexing_service` / `get_ga4_service` at the call site (e.g., `gsc_mcp.tools.analytics.get_searchconsole_service`) and inject the fixture as the return value. GA4 tests also use an `autouse` fixture to set `GA4_PROPERTY_ID`, since `get_ga4_property_id()` raises `RuntimeError` if the env var is absent and no `override` is passed.

CrUX tests mock `httpx.Client` as a context manager (`client.__enter__` returns the mock itself). `sitemap_audit` tests patch `gsc_mcp.tools.sitemaps.httpx.Client` and `gsc_mcp.tools.sitemaps.get_search_analytics`. `schema_validate` tests patch `httpx.Client` directly (imported at module level in `technical.py`).

## Environment variables

| Variable | Purpose |
|---|---|
| `GSC_SERVICE_ACCOUNT_PATH` | Path to service account JSON (preferred for automation) |
| `GSC_CREDENTIALS_PATH` | Path to OAuth Desktop client JSON (interactive OAuth flow) |
| `GSC_SKIP_OAUTH` | Set to `true` to disable OAuth fallback (requires SA path) |
| `GA4_PROPERTY_ID` | Numeric GA4 property ID (e.g. `123456789`). Required for GA4 tools only, validated lazily |
| `CRUX_API_KEY` | Google API key with Chrome UX Report API enabled. Required for `crux_page_vitals` and `crux_history` only. Distinct from GSC/GA4 auth |
