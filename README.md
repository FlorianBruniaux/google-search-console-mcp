# gsc-mcp

Google Search Console MCP server with 18 tools covering search analytics, URL inspection, and the Google Indexing API. Built on Python 3.11+ and FastMCP.

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

## Tools (18)

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
| SEO | `quick_wins` | Pages in positions 4-15 with CTR below benchmark |
| SEO | `traffic_drops` | Queries with declining clicks, with diagnosis |
| SEO | `check_alerts` | Traffic concentration risks and ranking opportunities |
| Inspection | `inspect_url` | URL indexing status via URL Inspection API |
| Inspection | `batch_url_inspection` | Inspect up to 10 URLs at once |
| Inspection | `check_indexing_issues` | Inspect URLs and categorize by issue type |
| Indexing | `submit_url` | Request indexing for a single URL |
| Indexing | `submit_batch` | Request indexing for multiple URLs (true HTTP batch) |
| Sitemaps | `list_sitemaps` | List submitted sitemaps |
| Sitemaps | `submit_sitemap` | Submit a sitemap URL |

## Requirements

- Python 3.11+
- Google Cloud project with these APIs enabled:
  - Google Search Console API
  - Web Search Indexing API
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

52 tests, all mocked (no real Google API calls needed).

## License

MIT
