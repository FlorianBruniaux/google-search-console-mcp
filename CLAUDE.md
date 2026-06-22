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

**Entry point**: `src/gsc_mcp/server.py` creates a `FastMCP("gsc-mcp")` instance and registers all 32 tools via `mcp.tool()()`. No dynamic discovery; every tool is explicitly imported and registered here. Adding a new tool means: implement it in the relevant `tools/` module, import it in `server.py`, and register it.

**Auth layer** (`auth.py`): Three separate credential pairs: GSC API (`searchconsole/v1`), Indexing API (`indexing/v3`), and GA4 (`analytics.readonly`). Resolution order: if `GSC_SERVICE_ACCOUNT_PATH` is set, use service account credentials. Otherwise, fall through to OAuth with token cached as JSON (not pickle) at the OS user data dir (`~/Library/Application Support/gsc-mcp/` on macOS). Token files: `token_gsc.json`, `token_indexing.json`, `token_ga4.json`. `get_ga4_property_id(override=None)` accepts an optional override string that bypasses `GA4_PROPERTY_ID`, enabling per-call multi-property support.

**Tools** (`src/gsc_mcp/tools/`): Eight modules, each owns a logical domain (analytics, cross, ga4, indexing, inspection, properties, seo, sitemaps). Every tool function is a plain Python function (no class, no decorator) registered by `server.py`. All return JSON strings via `json.dumps(with_meta(...))`.

**Cross-platform pattern** (`cross.py`): `traffic_health_check` and `page_analysis` compose the high-level functions from `analytics.py` and `ga4.py`. They call those functions, parse their JSON strings with `json.loads`, then join on `_normalize_url` (strips scheme/host/query/trailing-slash so GSC absolute URLs and GA4 paths match). `engagement_rate` is derived as `engaged_sessions/sessions` because `ga4_organic_landing_pages` does not expose it directly.

**Output contract** (`meta.py`): Every tool wraps its response dict with `with_meta(data, tool=..., params=...)`, which appends a `_meta` block (`{"tool": "<name>", "params": {...}}`). Any new tool must follow this pattern.

**Retry** (`retry.py`): `@with_retry(max_retries=3, base_delay=1.0)` wraps Google API calls. Retries on 429/500/502/503/504 with exponential backoff (`base_delay * 2^attempt`). Other HTTP errors propagate immediately.

**Quota tracking** (`quota.py` + `indexing.py`): `QuotaTracker` is a module-level singleton in `indexing.py` that tracks Indexing API usage within a single process lifetime (200 req/day limit, warns at 180). It does not persist across restarts; restarting the server resets the counter.

**Batching** (`indexing.py`): `submit_batch` uses `svc.new_batch_http_request()` chunked at 100 URLs per HTTP request. This is a true multipart batch, not a sequential loop. Callbacks collect per-URL results.

## Test conventions

All tests are fully mocked (no real Google API calls). `tests/conftest.py` defines two shared fixtures:
- `mock_gsc_service`: MagicMock wired for `sites`, `searchanalytics`, `sitemaps`, `urlInspection`
- `mock_indexing_service`: MagicMock with a working `new_batch_http_request()` implementation that fires callbacks synchronously

Tests patch `get_searchconsole_service` / `get_indexing_service` / `get_ga4_service` at the call site (e.g., `gsc_mcp.tools.analytics.get_searchconsole_service`) and inject the fixture as the return value. GA4 tests also use an `autouse` fixture to set `GA4_PROPERTY_ID`, since `get_ga4_property_id()` raises `RuntimeError` if the env var is absent and no `override` is passed.

## Environment variables

| Variable | Purpose |
|---|---|
| `GSC_SERVICE_ACCOUNT_PATH` | Path to service account JSON (preferred for automation) |
| `GSC_CREDENTIALS_PATH` | Path to OAuth Desktop client JSON (interactive OAuth flow) |
| `GSC_SKIP_OAUTH` | Set to `true` to disable OAuth fallback (requires SA path) |
| `GA4_PROPERTY_ID` | Numeric GA4 property ID (e.g. `123456789`). Required for GA4 tools only, validated lazily |
