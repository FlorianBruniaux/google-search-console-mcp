# gsc-mcp

Google Search Console MCP server with 30 tools covering search analytics, URL inspection, the Google Indexing API, and Google Analytics 4. Built on Python 3.11+ and FastMCP.

The main workflow it enables: ask Claude "which pages on my site are crawled but not indexed?" then "submit them for indexing", end to end, no manual Google Search Console tabs.

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

## Tools (30)

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

## Requirements

- Python 3.11+
- Google Cloud project with these APIs enabled:
  - Google Search Console API
  - Web Search Indexing API
  - Google Analytics Data API (for GA4 tools)
- Credentials: OAuth Desktop app OR Service Account JSON
- For the Indexing API: your account or service account needs **Owner-level** access in Search Console (Full access is not enough)
- Indexing API default quota: 200 requests per day

## Installation

```bash
git clone https://github.com/<your-username>/gsc-mcp
cd gsc-mcp
python3 --version  # must be 3.11 or higher
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
```

## Configuration

Copy `.env.example` to `.env` and fill in the relevant variables.

### OAuth (interactive, good for personal use)

```bash
export GSC_CREDENTIALS_PATH=/path/to/oauth-client-credentials.json
gsc-mcp
```

The first run opens a browser for Google login. The token is saved to your OS user data directory (`~/.local/share/gsc-mcp/` on Linux, `~/Library/Application Support/gsc-mcp/` on macOS) as JSON files.

### Service Account (recommended for automation and Claude Desktop)

```bash
export GSC_SERVICE_ACCOUNT_PATH=/path/to/service-account.json
export GSC_SKIP_OAUTH=true
gsc-mcp
```

### GA4 setup

GA4 tools use the same Service Account as GSC. Two steps to enable them:

1. Open GA4 Admin, go to Property Access Management, and add the service account email (the `client_email` field in your SA JSON) with the **Viewer** role.
2. Set the `GA4_PROPERTY_ID` environment variable to your numeric property ID (e.g. `123456789`, visible in GA4 Admin under Property Settings). The `properties/` prefix is added automatically if omitted.

```json
"env": {
  "GSC_SERVICE_ACCOUNT_PATH": "/path/to/service-account.json",
  "GA4_PROPERTY_ID": "123456789"
}
```

GSC-only users are not affected: the `GA4_PROPERTY_ID` check runs lazily on the first GA4 tool call, never at startup.

### Claude Desktop

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "gsc-mcp": {
      "command": "python",
      "args": ["-m", "gsc_mcp.server"],
      "env": {
        "GSC_SERVICE_ACCOUNT_PATH": "/absolute/path/to/service-account.json",
        "GSC_SKIP_OAUTH": "true"
      }
    }
  }
}
```

Or, once published to PyPI:

```json
{
  "mcpServers": {
    "gsc-mcp": {
      "command": "uvx",
      "args": ["gsc-mcp"],
      "env": {
        "GSC_SERVICE_ACCOUNT_PATH": "/absolute/path/to/service-account.json",
        "GSC_SKIP_OAUTH": "true"
      }
    }
  }
}
```

## Development

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest tests/ -v
```

139+ tests, all mocked (no real Google API calls needed).

## License

MIT
