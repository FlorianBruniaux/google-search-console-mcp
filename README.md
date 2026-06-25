# gsc-mcp

[![PyPI](https://img.shields.io/pypi/v/gsc-mcp-tools)](https://pypi.org/project/gsc-mcp-tools/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
[![Tests](https://img.shields.io/badge/tests-282%20passed-brightgreen)](https://github.com/FlorianBruniaux/google-search-console-mcp)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Google Search Console MCP server with 43 tools covering search analytics, URL inspection, the Google Indexing API, Google Analytics 4, Core Web Vitals (CrUX), sitemap auditing, JSON-LD schema validation, and composite health scoring. Built on Python 3.11+ and FastMCP.

**TL;DR:** Install with `uvx gsc-mcp-tools`, point at your GSC service account, and ask Claude things like "which pages on my site are crawled but not indexed? Submit them." The server handles the Google API calls, batching, retries, and quota tracking. All outputs are structured JSON so Claude can reason across results without parsing ambiguity.

**Latest: v0.6.2** (9 Claude Code agents + skills, improved docs). See the [full changelog](CHANGELOG.md).

## What you can do with it

```
You → Claude → gsc-mcp
                 ├── Properties     (list, details, capabilities)
                 ├── Analytics      (performance, periods, anomalies)
                 ├── SEO            (quick wins, drops, cannibalization)
                 ├── Inspection     (URL status, batch, issue categories)
                 ├── Indexing API   (submit URL, true HTTP batch)
                 ├── Sitemaps       (list, submit, audit coverage)
                 ├── GA4            (pages, sources, realtime, funnels)
                 ├── Cross GSC+GA4  (health check, page analysis)
                 ├── CrUX           (Core Web Vitals, history)
                 └── Technical      (JSON-LD schema validation)
```

### Tool summary

| Category | Tools | What it does |
|---|---|---|
| Properties | `list_properties`, `get_site_details`, `get_capabilities` | Discover and inspect your GSC properties |
| Analytics | `get_search_analytics`, `get_performance_overview`, `compare_search_periods`, `get_search_by_page_query`, `get_advanced_search_analytics`, `analytics_anomalies`, `discover_performance`, `news_performance`, `search_type_breakdown`, `ai_overviews_impact` | Query impressions, clicks, CTR, position; Discover and Google News performance; breakdown by search type; AI Overview appearance data |
| SEO | `quick_wins`, `traffic_drops`, `seo_striking_distance`, `seo_cannibalization`, `seo_lost_queries`, `check_alerts` | Surface opportunities, diagnose drops, detect cannibalization |
| Inspection | `inspect_url`, `batch_url_inspection`, `check_indexing_issues` | URL indexing status, crawl verdict, canonical, categorized by issue type |
| Indexing | `submit_url`, `submit_batch` | Request (re)indexing via the Google Indexing API, true HTTP batch, quota tracking |
| Sitemaps | `list_sitemaps`, `submit_sitemap`, `sitemaps_get`, `sitemaps_delete`, `sitemap_audit` | Manage submitted sitemaps; audit declared URLs against GSC coverage |
| GA4 | `ga4_organic_landing_pages`, `ga4_traffic_sources`, `ga4_page_performance`, `ga4_realtime`, `ga4_user_behavior`, `ga4_conversion_funnel`, `ga4_funnel` | Analytics 4 data: sessions, engagement, conversions, realtime, multi-step funnels via v1alpha (all filterable by `hostname` and `country`) |
| Cross | `traffic_health_check`, `page_analysis`, `page_health_score`, `content_brief` | Join GSC clicks with GA4 sessions; composite 0-100 health score (GSC+GA4+CrUX+schema); per-page content intelligence |
| CrUX | `crux_page_vitals`, `crux_history` | Real-user Core Web Vitals (LCP, INP, CLS, FCP, TTFB) from the Chrome UX Report API, requires `CRUX_API_KEY` |
| Technical | `schema_validate` | Fetch any public URL and validate its JSON-LD structured data schemas; suggests missing schemas by URL pattern |

## Why this exists

Two solid open-source projects cover parts of this problem:

**[AminForou/mcp-gsc](https://github.com/AminForou/mcp-gsc)** (Python, 1k+ stars) has excellent search analytics, rich SEO tooling, and solid OAuth + Service Account auth. It does not include the Google Indexing API at all (no `submit_url`, no `submit_batch`). You can analyze your traffic but you cannot request reindexing.

**[Suganthan-Mohanadasan/Suganthans-GSC-MCP](https://github.com/Suganthan-Mohanadasan/Suganthans-GSC-MCP)** (Node.js/TypeScript) adds the Indexing API, but its `submit_batch` is a sequential `for` loop with a 100ms delay between requests, not a real HTTP batch. It also mixes plain-text and JSON outputs, hardcodes version strings that diverge from package.json, and has no retry logic.

This project takes the auth patterns and SEO tools from the first, the Indexing API scope from the second, and fixes the gaps in both.

### Why Python instead of Go or Rust

The Google API Python client (`google-api-python-client`) is the official, best-maintained client for these APIs. It ships `service.new_batch_http_request()` natively, which is what makes true HTTP multipart batching possible without implementing the wire format by hand. The Go and Rust ecosystem for Google APIs relies on unofficial or auto-generated clients that do not expose this method. FastMCP also has first-class Python support with minimal boilerplate. The trade-off is startup latency (a few hundred ms vs near-zero for a compiled binary), but for a local MCP server called interactively by Claude that trade-off is irrelevant.

### What changed vs the two inspirations

| Feature | AminForou/mcp-gsc | Suganthan | gsc-mcp |
|---|---|---|---|
| Google Indexing API | No | Yes (fake batch) | Yes (true HTTP batch) |
| submit_batch | N/A | Sequential loop | `new_batch_http_request()`, 100/chunk |
| Token storage | pickle | pickle | JSON (`creds.to_json()`) |
| Retry on 429/5xx | No | No | Yes, exponential backoff |
| Quota tracking | No | No | Yes, warns at 180/200 |
| Output format | Mixed text+JSON | Mixed | 100% JSON + `_meta` block |

## Tools (43)

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
| Sitemaps | `sitemap_audit` | Fetch a sitemap, parse its URLs, cross-reference against 90 days of GSC coverage |
| CrUX | `crux_page_vitals` | Real-user Core Web Vitals (LCP, INP, CLS, FCP, TTFB) for a URL from the Chrome UX Report API |
| CrUX | `crux_history` | Historical Core Web Vitals trend (weekly data points) for a URL |
| Technical | `schema_validate` | Fetch any public URL and validate its JSON-LD schemas; suggests missing schemas by URL pattern |

## Requirements

- Python 3.11+
- A Google Cloud project with the following APIs enabled: Google Search Console API, Web Search Indexing API, Google Analytics Data API
- A Service Account JSON key (recommended) or OAuth Desktop credentials
- For the Indexing API: the service account must have **Owner-level** access on the GSC property (Full access is not enough)
- Indexing API default quota: 200 requests per day

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

## For AI assistants

The `docs/machine-readable/` directory contains structured architecture docs designed to give any AI agent (Claude, Cursor, Copilot...) an accurate picture of the project without reading the full codebase:

- `llms.txt`: quick reference covering all 43 tools, module map, security rules, test patterns, and a decision tree for common tasks
- `adr-index.yaml`: 15 Architecture Decision Records reconstructed from git history
- `code-map.yaml`: full module/test/dependency map
- `constraints.yaml`: forbidden patterns (no stdlib XML on external input, no pickle for tokens, no unvalidated URLs in sitemap fetch...) and required patterns
- `tech-decisions.yaml`: stack decisions by domain (auth, retry, output contract, packaging...)

Load `llms.txt` via your AI context or reference it in your CLAUDE.md with `@docs/machine-readable/llms.txt`.

## Claude agents and skills

The `.claude/` directory ships 9 pre-built Claude Code agents and 9 skills. Each agent is wired to a single skill that defines exactly what it does: which tools to call, in what order, and how to format the output.

### Agents

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

To use an agent from Claude Code, ask naturally ("why did traffic drop?") or invoke it by name. Each agent loads its skill at runtime and returns a structured answer, not a narration of what it did.

### Skills

Skills live in `.claude/skills/` and are also invokable directly via `/cannibalization-check`, `/indexing-audit`, etc. They define the exact steps, tool call sequence, and output format. Agents reference them; skills run standalone when you want to drive the workflow yourself without delegating to an agent.

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

## Inspirations

- [AminForou/mcp-gsc](https://github.com/AminForou/mcp-gsc): auth patterns, OAuth + Service Account flow, SEO analytics structure
- [Suganthan-Mohanadasan/Suganthans-GSC-MCP](https://github.com/Suganthan-Mohanadasan/Suganthans-GSC-MCP): Indexing API scope, `with_meta()` output pattern

## License

MIT
