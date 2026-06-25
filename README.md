# gsc-mcp

[![PyPI](https://img.shields.io/pypi/v/gsc-mcp-tools)](https://pypi.org/project/gsc-mcp-tools/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
[![Tests](https://img.shields.io/badge/tests-282%20passed-brightgreen)](https://github.com/FlorianBruniaux/google-search-console-mcp)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Google Search Console MCP server with 43 tools covering search analytics, URL inspection, the Google Indexing API, Google Analytics 4, Core Web Vitals (CrUX), sitemap auditing, JSON-LD schema validation, and composite health scoring. Built on Python 3.11+ and FastMCP.

**TL;DR:** Install with `uvx gsc-mcp-tools`, point at your GSC service account, and ask Claude things like "which pages on my site are crawled but not indexed? Submit them." The server handles the Google API calls, batching, retries, and quota tracking. All outputs are structured JSON so Claude can reason across results without parsing ambiguity.

No SEO expertise required. You can ask "run a full site audit", "why did my traffic drop last week?", or "which queries are close to page one?" and Claude guides the analysis, explains every metric, and tells you what to fix. See [`examples/`](examples/) for ready-to-use prompts covering quick audits, full audits, traffic drops, keyword opportunities, and more.

**Latest: v0.6.2** (9 Claude Code agents + skills, improved docs). See the [full changelog](CHANGELOG.md).

## What you can do with it

The 43 tools span ten families: Properties (list and inspect GSC sites), Analytics (impressions, clicks, CTR, position, anomalies, Discover and News performance), SEO (quick wins, traffic drops, cannibalization, striking-distance queries), Inspection (URL indexing status, batch inspection, issue categorization), Indexing API (single URL submit or true HTTP batch), and Sitemaps (list, submit, audit coverage against GSC data). The remaining four families cover GA4 (sessions, engagement, conversions, realtime, multi-step funnels), Cross (GSC+GA4 joined health check and page analysis), CrUX (real-user Core Web Vitals from the Chrome UX Report API), and Technical (JSON-LD schema validation with pattern-based suggestions).

## Tools (43)

<details>
<summary>Show all 43 tools</summary>

| Category | Tool | Description |
|---|---|---|
| Meta | `get_capabilities` | List all available tools |
| Properties | `list_properties` | List all GSC properties |
| Properties | `get_site_details` | Get details for a specific property |
| Analytics | `get_search_analytics` | Query search performance data |
| Analytics | `get_performance_overview` | Aggregate totals + top queries |
| Analytics | `compare_search_periods` | Compare two consecutive periods |
| Analytics | `get_search_by_page_query` | Performance broken down by page and query |
| Analytics | `get_advanced_search_analytics` | Flexible query with custom dimensions and filters |
| Analytics | `analytics_anomalies` | Z-score anomaly detection on daily clicks |
| Analytics | `discover_performance` | Top pages by impressions in Google Discover |
| Analytics | `news_performance` | Top pages by impressions in Google News |
| Analytics | `search_type_breakdown` | Clicks and impressions split across web, Discover, News, image, video |
| Analytics | `ai_overviews_impact` | Queries with searchAppearance data, graceful 400/403 fallback |
| SEO | `quick_wins` | Pages in positions 4-15 with CTR below benchmark |
| SEO | `traffic_drops` | Queries with declining clicks, with diagnosis |
| SEO | `check_alerts` | Traffic concentration risks and ranking opportunities |
| SEO | `seo_striking_distance` | Queries in positions 8-15, one push away from page 1 |
| SEO | `seo_cannibalization` | Queries split across multiple pages (HHI conflict score) |
| SEO | `seo_lost_queries` | Queries with a click drop >= 80% vs the previous period |
| Inspection | `inspect_url` | URL indexing status via URL Inspection API |
| Inspection | `batch_url_inspection` | Inspect up to 10 URLs at once |
| Inspection | `check_indexing_issues` | Inspect URLs and categorize by issue type |
| Indexing | `submit_url` | Request indexing for a single URL |
| Indexing | `submit_batch` | Request indexing for multiple URLs (true HTTP batch) |
| Sitemaps | `list_sitemaps` | List submitted sitemaps |
| Sitemaps | `submit_sitemap` | Submit a sitemap URL |
| Sitemaps | `sitemaps_get` | Fetch details for a single sitemap |
| Sitemaps | `sitemaps_delete` | Delete a submitted sitemap (with safety check) |
| Sitemaps | `sitemap_audit` | Fetch a sitemap, parse its URLs, cross-reference against 90 days of GSC coverage |
| GA4 | `ga4_organic_landing_pages` | Sessions and engagement for organic landing pages |
| GA4 | `ga4_traffic_sources` | Sessions and conversions by channel, source and medium |
| GA4 | `ga4_page_performance` | 7 metrics per page path, optional CONTAINS filter |
| GA4 | `ga4_realtime` | Active users right now by screen, country and device |
| GA4 | `ga4_user_behavior` | Device, country and user-type breakdowns in one batch call |
| GA4 | `ga4_conversion_funnel` | Converting pages and event counts, optional event filter |
| GA4 | `ga4_funnel` | Multi-step funnel report via GA4 v1alpha RunFunnelReport, conversion rate per step |
| Cross | `traffic_health_check` | GSC clicks vs GA4 organic sessions ratio, flags tracking gaps and filter issues |
| Cross | `page_analysis` | GSC+GA4 join per page with opportunity score, sorted by priority |
| Cross | `page_health_score` | Composite 0-100 score (GSC 30 pts, GA4 25 pts, CrUX 25 pts, schema 20 pts), graceful degradation per component |
| Cross | `content_brief` | Per-page top queries, question queries, and GA4 session data for content planning |
| CrUX | `crux_page_vitals` | Real-user Core Web Vitals (LCP, INP, CLS, FCP, TTFB) for a URL from the Chrome UX Report API |
| CrUX | `crux_history` | Historical Core Web Vitals trend (weekly data points) for a URL |
| Technical | `schema_validate` | Fetch any public URL and validate its JSON-LD schemas; suggests missing schemas by URL pattern |

</details>

## Requirements

- Python 3.11+
- A Google Cloud project with the Search Console API, Web Search Indexing API, and Google Analytics Data API enabled
- A Service Account JSON key (recommended) or OAuth Desktop credentials

## Installation

```bash
uvx gsc-mcp-tools
```

Or with pip:

```bash
pip install gsc-mcp-tools
```

To run from source:

```bash
git clone https://github.com/FlorianBruniaux/google-search-console-mcp
cd google-search-console-mcp
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
```

## Configuration

**Full setup guide:** [docs/google-setup.md](docs/google-setup.md) covers creating a Google Cloud project, enabling APIs, creating a service account, adding it to GSC with the right permission level, and configuring GA4.

**First audit prompts:** [docs/starter-prompt.md](docs/starter-prompt.md) contains ready-to-use prompts for a full site audit, a 5-minute health check, single-page inspection, reindexing workflow, and GA4-only analysis.

### Quick start (service account)

```bash
export GSC_SERVICE_ACCOUNT_PATH=/absolute/path/to/service-account.json
export GSC_SKIP_OAUTH=true
export GA4_PROPERTY_ID=123456789   # only needed for GA4 tools
export CRUX_API_KEY=AIza...        # only needed for crux_page_vitals, crux_history
gsc-mcp
```

`CRUX_API_KEY` is a Google API key (not a service account) with the **Chrome UX Report API** enabled in your GCP Console. It is separate from GSC auth and only required for CrUX tools.

### Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "gsc-mcp": {
      "command": "uvx",
      "args": ["gsc-mcp-tools"],
      "env": {
        "GSC_SERVICE_ACCOUNT_PATH": "/absolute/path/to/service-account.json",
        "GSC_SKIP_OAUTH": "true",
        "GA4_PROPERTY_ID": "123456789",
        "CRUX_API_KEY": "AIza..."
      }
    }
  }
}
```

Remove `GA4_PROPERTY_ID` if you are not using GA4 tools. Restart Claude Desktop after saving.

### Multi-property support

To query a different GA4 property without changing the config, pass `property_id` directly to any GA4 or cross tool:

```python
ga4_traffic_sources(property_id="987654321")
traffic_health_check(site="sc-domain:example.com", property_id="987654321")
```

## CLI usage (gsc-cli)

After installation, `gsc-cli` is available as a standalone shell command. It wraps all 43 tools from the MCP server and uses the same authentication.

```bash
# List all 43 commands
gsc-cli list

# Run any tool (all parameters are flags, no positional args)
gsc-cli get-search-analytics --site https://example.com/ --days 28
gsc-cli get-performance-overview --site https://example.com/

# Multi-value flags for list parameters
gsc-cli batch-url-inspection \
  --urls https://example.com/page-1/ \
  --urls https://example.com/page-2/ \
  --site https://example.com/

# GA4 funnel with a JSON steps array
gsc-cli ga4-funnel \
  --steps '[{"name":"Visit","event":"page_view"},{"name":"Convert","event":"purchase"}]' \
  --start-date 28daysAgo \
  --end-date today

# Keep the _meta diagnostic block in output
gsc-cli list-properties --meta

# Pipe to jq
gsc-cli get-search-analytics --site https://example.com/ | jq '.rows[:5]'
```

Set `GSC_SERVICE_ACCOUNT_PATH` for non-interactive use (same as the MCP server). To cache OAuth credentials interactively, run:

```bash
gsc-cli auth login --allow-browser
```

Exit codes: `0` success, `1` Google API error, `2` credential/config error or invalid arguments.

> **Quota note**: `submit-batch` and `submit-url` use the Google Indexing API (200 req/day limit). Each `gsc-cli` call starts a fresh process, so cross-invocation quota tracking is not implemented. The `@with_retry` decorator still catches 429s, but the in-process counter resets every call.

## Claude agents and skills

The `.claude/` directory ships 9 pre-built Claude Code agents and 9 skills. Each agent is wired to a single skill that defines exactly what it does: which tools to call, in what order, and how to format the output.

### Agents

<details>
<summary>Show 9 GSC agents</summary>

| Agent | Skill | When to use |
|---|---|---|
| `gsc-seo-reporter` | `seo-weekly-report` | Weekly traffic recap, period-over-period summary |
| `gsc-traffic-doctor` | `traffic-drop-diagnosis` | Sudden or sustained drop in clicks or impressions |
| `gsc-content-optimizer` | `content-opportunities` | Pages close to page 1 (positions 4-20) worth a push |
| `gsc-cannibalization-checker` | `cannibalization-check` | Multiple pages competing for the same query |
| `gsc-indexing-auditor` | `indexing-audit` | Crawl errors, pages not indexed, coverage gaps |
| `gsc-sitemap-auditor` | `sitemap-audit` | Sitemap health and declared-vs-indexed coverage |
| `gsc-schema-auditor` | `schema-audit` | JSON-LD errors blocking rich results |
| `gsc-page-analyst` | `page-deep-dive` | Full diagnostic for a single URL |
| `gsc-ai-overviews-analyst` | `ai-overviews-impact` | AI Overview cannibalization on CTR |

</details>

To use an agent from Claude Code, ask naturally ("why did traffic drop?") or invoke it by name. Each agent loads its skill at runtime and returns a structured answer, not a narration of what it did.

### Skills

Skills live in `.claude/skills/` and are invokable directly via slash command. They define the exact steps, tool call sequence, and output format. Agents reference them; skills run standalone when you want to drive the workflow yourself without delegating to an agent.

<details>
<summary>Show 10 SEO skills + 2 dev commands</summary>

| Skill | Command | When to use |
|---|---|---|
| `seo-weekly-report` | `/seo-weekly-report` | Weekly traffic recap, period-over-period summary |
| `traffic-drop-diagnosis` | `/traffic-drop-diagnosis` | Sudden or sustained drop in clicks or impressions |
| `content-opportunities` | `/content-opportunities` | Pages close to page 1 (positions 4-20) worth a push |
| `cannibalization-check` | `/cannibalization-check` | Multiple pages competing for the same query |
| `indexing-audit` | `/indexing-audit` | Crawl errors, pages not indexed, coverage gaps |
| `sitemap-audit` | `/sitemap-audit` | Sitemap health and declared-vs-indexed coverage |
| `schema-audit` | `/schema-audit` | JSON-LD errors blocking rich results |
| `page-deep-dive` | `/page-deep-dive` | Full diagnostic for a single URL |
| `ai-overviews-impact` | `/ai-overviews-impact` | AI Overview cannibalization on CTR |
| `python-clean-code` | `/python-clean-code` | Review a module for clean code violations before PR |
| `add-tool` | `/add-tool` | Step-by-step workflow to add a new MCP tool |
| `run-tests` | `/run-tests` | Run the pytest suite with automatic failure diagnosis |

</details>

## For AI assistants

The `docs/machine-readable/` directory contains structured architecture docs designed to give any AI agent (Claude, Cursor, Copilot...) an accurate picture of the project without reading the full codebase:

- `llms.txt`: quick reference covering all 43 tools, module map, security rules, test patterns, and a decision tree for common tasks
- `adr-index.yaml`: 15 Architecture Decision Records reconstructed from git history
- `code-map.yaml`: full module/test/dependency map
- `constraints.yaml`: forbidden patterns (no stdlib XML on external input, no pickle for tokens, no unvalidated URLs in sitemap fetch...) and required patterns
- `tech-decisions.yaml`: stack decisions by domain (auth, retry, output contract, packaging...)

Load `llms.txt` via your AI context or reference it in your CLAUDE.md with `@docs/machine-readable/llms.txt`.

## Development

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest tests/ -v
```

282 tests, all mocked (no real Google API calls needed).

## Troubleshooting

**`uvx gsc-mcp-tools` launches but no tools appear in Claude Desktop**

Fully quit Claude Desktop (`Cmd+Q`) and reopen it. Saving the config file is not enough; the MCP process is only started on launch.

**`GSC_SERVICE_ACCOUNT_PATH` is set but auth fails**

Use an absolute path. Relative paths and `~/` tilde expansion are not resolved. Check with `echo $GSC_SERVICE_ACCOUNT_PATH` that the value is a full `/Users/...` path.

**GA4 tools return "property_id required"**

Either set `GA4_PROPERTY_ID` in your config env block, or pass `property_id` directly to the tool call. The env var is the default; the parameter overrides it per call.

**`crux_page_vitals` or `crux_history` returns "CRUX_API_KEY not set"**

CrUX tools require a separate Google API key (not the service account) with the **Chrome UX Report API** enabled. Create one in Google Cloud Console under Credentials, enable the API, then set `CRUX_API_KEY=AIza...` in your config.

**Indexing API returns 403 on `submit_url`**

The service account needs **Owner-level** access on the GSC property, not just Full access. Go to Search Console Settings > Users and permissions, find the service account email, and upgrade its role to Owner.

**`submit_batch` quota warning at 180/200**

The Indexing API default quota is 200 requests per day per GCP project. The tool warns at 180. To increase it, request a quota increase in Google Cloud Console under APIs & Services > Quotas.

## Why this exists

Two projects shaped the approach here. [AminForou/mcp-gsc](https://github.com/AminForou/mcp-gsc) (Python, 1k+ stars) has strong search analytics and handles OAuth and Service Account auth cleanly, but does not include the Google Indexing API at all. [Suganthan-Mohanadasan/Suganthans-GSC-MCP](https://github.com/Suganthan-Mohanadasan/Suganthans-GSC-MCP) (Node.js) adds the Indexing API but implements `submit_batch` as a sequential loop with a 100ms delay between requests, not a real HTTP batch, and mixes plain-text and JSON outputs with no retry logic.

This project takes the auth and SEO patterns from the first, the Indexing API scope from the second, and closes the gaps in both. Python was the natural choice: `google-api-python-client` ships `service.new_batch_http_request()` natively, which makes true HTTP multipart batching possible without reimplementing the wire format by hand.

| Feature | AminForou/mcp-gsc | Suganthan | gsc-mcp |
|---|---|---|---|
| Google Indexing API | No | Yes (fake batch) | Yes (true HTTP batch) |
| submit_batch | N/A | Sequential loop | `new_batch_http_request()`, 100/chunk |
| Token storage | pickle | pickle | JSON (`creds.to_json()`) |
| Retry on 429/5xx | No | No | Yes, exponential backoff |
| Quota tracking | No | No | Yes, warns at 180/200 |
| Output format | Mixed text+JSON | Mixed | 100% JSON + `_meta` block |

## License

MIT
