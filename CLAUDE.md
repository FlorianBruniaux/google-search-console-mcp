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

# Run all tests (339 tests, fully mocked)
pytest tests/ -v

# Run a single test file
pytest tests/test_analytics.py -v

# Run a specific test by name
pytest tests/ -k "test_submit_batch" -v
```

## Architecture

**Entry point**: `src/gsc_mcp/server.py` creates a `FastMCP("gsc-mcp")` instance and registers all 61 tools by iterating `registry.TOOLS`. Dynamic: adding a function to `registry.py` is enough to register it in both the MCP server and the CLI.

**Registry** (`src/gsc_mcp/registry.py`): imports all 61 tool functions and exposes `TOOLS: dict[str, Callable[..., str]]`. An `assert` at import time verifies `set(TOOLS) == set(_ALL_TOOLS)` from `properties.py`, so any mismatch fails loudly at startup.

**CLI** (`src/gsc_mcp/cli.py`): shell frontend that generates 61 subcommands from `TOOLS` by introspection. All-flags (no positionals). `list[dict]` params take a JSON string. Sets `GSC_NO_BROWSER=1` at startup to prevent accidental OAuth browser popups.

**Auth layer** (`auth.py`): Three separate credential pairs (GSC API `searchconsole/v1`, Indexing API `indexing/v3`, GA4 `analytics.readonly`). Resolution order: if `GSC_SERVICE_ACCOUNT_PATH` is set, use service account credentials. Otherwise, fall through to OAuth with token cached as JSON (not pickle) at the OS user data dir (`~/Library/Application Support/gsc-mcp/` on macOS). Token files are written `chmod 0o600`; the directory is created with `0o700`. `get_ga4_property_id(override=None)` accepts an optional override string that bypasses `GA4_PROPERTY_ID`, enabling per-call multi-property support.

**Tools** (`src/gsc_mcp/tools/`): Modules, each owns a logical domain:
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
- `links.py`: `internal_links_audit` (zone-weighted internal linking, no auth needed)

**CrUX tools** (`crux.py`): `crux_page_vitals` and `crux_history` call the Chrome UX Report API via `httpx` (POST to `:queryRecord` / `:queryHistoryRecord`). Require `CRUX_API_KEY` (a plain Google API key, not a service account). The Chrome UX Report API must be enabled in the GCP project. A 404 from the API means not enough field data for that URL, returned as `verdict="not_enough_data"`.

**sitemap_audit** (`sitemaps.py`): fetches a sitemap via `httpx`, parses XML with `defusedxml.ElementTree` (prevents XXE and billion-laughs). Handles sitemap index files with one level of recursion; child sitemap URLs are validated against the parent's origin before fetching (`follow_redirects=False`, SSRF protection). Cross-references declared URLs against 90 days of GSC data. Returns `missing_sample` capped at 20 URLs. Verdicts: `empty` | `fetch_error` | `partial` (>20% URLs absent from GSC) | `healthy`.

**schema_validate** (`technical.py`): fetches any public URL, extracts `<script type="application/ld+json">` blocks with `html.parser` (stdlib), validates required fields per schema type (Article, LocalBusiness, FAQPage, Product, WebSite, BreadcrumbList, SoftwareApplication), and suggests missing schemas from URL path patterns (`/faq` → FAQPage, `/blog/` → BlogPosting, etc.). No auth required.

**Internal linking** (`links.py`): `internal_links_audit` parses every `<a href>` and tags it with the semantic zone it sits in (`body`, `nav`, `footer`, `header`, `aside`), tracked with a stack so nested containers resolve to the innermost one. `role="navigation"` / `contentinfo` / `banner` / `complementary` are treated like their semantic tags. The headline output is `footer_only_targets`: internal targets linked from nav/footer/aside but from no page body, which is the highest-value finding. Also reports generic and empty anchors (FR and EN lists), internal `rel=nofollow`, and self-links. Paths are compared with trailing slashes stripped, so `/x` and `/x/` are one target.

**Link equity** (`link_equity_map` in `links.py`): takes the top `max_pages` pages by impressions from GSC, crawls each with the same zone-aware parser, and builds a directed graph of internal links. Joining that graph to the GSC numbers yields `underlinked_striking_distance`, pages at position 11-20 with no body inbound link, which is the cheapest ranking move a site has. `max_pages` is capped at 100, requests are spaced by `delay_seconds` (0.2 by default, set 0 in tests), and `pages_crawled` / `pages_failed` / `coverage_note` are always returned. Only crawled pages act as link sources, so an "orphan" is a candidate within that set, never a site-wide fact.

**Pruning guard rail** (`prune_candidates` in `seo.py`): classifies pages into `has_traffic`, `impressions_no_clicks`, `low_impressions` and `zero_impressions` from 180 days of GSC data, and returns no "delete these" list. A page with clicks can never appear as a candidate. `tests/test_seo.py::test_prune_solar_panel_local_pages_are_protected` is the non-regression case: 300 short local pages that are indexed and bring traffic, which length-based tools advise deleting.

**No destructive recommendation without data**: any caller (agent or skill) proposing to delete a page, add `noindex`, consolidate, or strip content must first read that page's clicks, impressions and indexing status over at least 90 days, via `prune_candidates` or `get_search_analytics`. When the data contradicts the finding, downgrade it to an observation and say so in the report rather than dropping it silently. Content length and template similarity are not grounds for deletion.

**Heading structure** (`heading_audit` in `content.py`): H1 uniqueness, level jumps (H2 straight to H4), title vs H1 word-for-word duplication (a duplicate wastes a second angle on the target keyword), headings that carry no information, and words per H2. Uses its own `_HeadingParser` because `drift.py`'s parser only covers h1-h3 and discards document order; drift's output shape is persisted in baselines, so it is deliberately left alone.

**Cross-platform pattern** (`cross.py`): `traffic_health_check` and `page_analysis` compose functions from `analytics.py` and `ga4.py`. They call those functions, parse their JSON strings with `json.loads`, then join on `_normalize_url` (strips scheme/host/query/trailing-slash so GSC absolute URLs and GA4 paths match). `engagement_rate` is derived as `engaged_sessions/sessions`.

**Output contract** (`meta.py`): Every tool wraps its response dict with `with_meta(data, tool=..., params=...)`, which appends a `_meta` block (`{"tool": "<name>", "params": {...}}`). Data keys are spread at the top level (not nested under `"data"`). Any new tool must follow this pattern.

**Retry** (`retry.py`): `@with_retry(max_retries=3, base_delay=1.0)` wraps Google API calls. Catches two families of transient errors:
- `googleapiclient.errors.HttpError` on status codes `{429, 500, 502, 503, 504}`
- `google.api_core.exceptions` subtypes: `ServiceUnavailable`, `ResourceExhausted`, `InternalServerError`, `BadGateway`, `RetryError` (GA4 gRPC errors)

Applied to `_fetch_rows` in `analytics.py` (covers all GSC analytics/SEO tools) and directly on each GA4 tool. Does not retry on other 4xx errors.

**Quota tracking** (`quota.py` + `indexing.py`): `QuotaTracker` is a module-level singleton in `indexing.py` that tracks Indexing API usage within a single process lifetime (200 req/day limit, warns at 180). It does not persist across restarts.

**Batching** (`indexing.py`): `submit_batch` uses `svc.new_batch_http_request()` chunked at 100 URLs per HTTP request. True multipart batch, not a sequential loop.

**Write-tool confirmation protocol**: Any tool that mutates external state (`submit_url`, `submit_batch`, `sitemaps_delete`, `indexnow_submit`, `submit_sitemap`) is destructive or hard to reverse from the caller's side (Google re-crawls, IndexNow pings third-party search engines, sitemap deletion removes it from GSC tracking). Callers driving these tools (agents, skills) must follow four steps before invoking one:
1. **State**: read the current state first (e.g. `list_sitemaps` before `sitemaps_delete`, `check_indexing_issues` before `submit_batch`).
2. **Blast radius**: state plainly what will change and how many URLs/entities are affected.
3. **Confirm**: get explicit user confirmation naming the exact action, not a generic "ok to proceed?".
4. **Verify**: after the call, report what the tool actually returned (`QuotaTracker` counts, batch success/failure split), not just "done".
This is a calling-convention rule for agents/skills built on top of `gsc-mcp`, not code enforced inside the tools themselves, the tools stay pure API wrappers.

## Adding a new tool

1. Implement the function in the relevant `tools/` module (or create a new one).
2. Decorate with `@with_retry()` if the tool calls a Google API directly.
3. Return `json.dumps(with_meta(data, tool="tool_name", params={...}))`.
4. Add the function to the tuple in `src/gsc_mcp/registry.py`. The MCP server and `gsc-cli` both pick it up automatically from `TOOLS`. No change needed in `server.py`.
5. Add the tool name to `_ALL_TOOLS` in `properties.py` and update the `get_capabilities` docstring count.
6. Write tests in `tests/test_<module>.py`, mocking all Google API calls.

For GA4 tools that filter by hostname/country, use `_build_dimension_filter(hostname, country, base_filter)` from `ga4.py`. It returns `None` when both are `None` (backward-compatible), a single `FilterExpression` when only one is set, and an AND group (`FilterExpressionList`) when both are set.

## CLI (gsc-cli)

`gsc-cli` exposes all 61 tools as shell commands, auto-generated from `registry.TOOLS`. No manual registration is needed; adding a tool to the registry is enough.

```bash
# List all 61 commands
gsc-cli list

# Run any tool (all parameters are flags, no positional args)
gsc-cli get-search-analytics --site https://example.com/ --days 28
gsc-cli batch-url-inspection --urls https://a.com/ --urls https://b.com/ --site https://example.com/
gsc-cli ga4-funnel --steps '[{"name":"signup","event":"sign_up"},{"name":"buy","event":"purchase"}]' --start-date 28daysAgo --end-date today

# Keep _meta diagnostic block in output
gsc-cli list-properties --meta

# Interactive OAuth (the only path that opens a browser)
gsc-cli auth login --allow-browser
```

**QuotaTracker warning**: `QuotaTracker` in `indexing.py` is an in-process singleton, so the 200 req/day guard resets to zero on every new `gsc-cli` invocation. The CLI does not track quota across shell calls. Only the Google-side 429 (retried via `@with_retry`) provides real protection in shell use.

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
