# gsc-mcp

Google Search Console MCP server with 18 tools covering search analytics, URL inspection, and the Indexing API (true HTTP batch, not sequential loop).

Built on Python + FastMCP. Covers both detection (inspection, analytics) and submission (Indexing API) in one place.

## Tools

| Category | Tools |
|---|---|
| Meta | `get_capabilities` |
| Properties | `list_properties`, `get_site_details` |
| Analytics | `get_search_analytics`, `get_performance_overview`, `compare_search_periods`, `get_search_by_page_query`, `get_advanced_search_analytics` |
| SEO | `quick_wins`, `traffic_drops`, `check_alerts` |
| Inspection | `inspect_url`, `batch_url_inspection`, `check_indexing_issues` |
| Indexing API | `submit_url`, `submit_batch` |
| Sitemaps | `list_sitemaps`, `submit_sitemap` |

## Setup

### Prerequisites

1. Google Cloud project with Search Console API and Web Search Indexing API enabled.
2. Credentials: OAuth Desktop app (for interactive use) or Service Account JSON.
3. For the Indexing API: your account or service account needs Owner-level access in Search Console (not just Full).
4. Default Indexing API quota: 200 requests per day.

### Install

```bash
# Clone and install
git clone https://github.com/yourname/gsc-mcp
cd gsc-mcp
pip install -e .
```

Or via uvx (once published):

```bash
uvx gsc-mcp
```

## Configuration

### OAuth (interactive, recommended for personal use)

```bash
export GSC_CREDENTIALS_PATH=/path/to/oauth-client-credentials.json
gsc-mcp
```

The first run opens a browser for Google authentication. Token is saved to `~/.local/share/gsc-mcp/token_gsc.json` (path varies by OS).

### Service Account (recommended for automation)

```bash
export GSC_SERVICE_ACCOUNT_PATH=/path/to/service-account.json
export GSC_SKIP_OAUTH=true
gsc-mcp
```

### Claude Desktop config

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

## Key design decisions

- Two separate API clients with distinct OAuth scopes (`auth/webmasters` for GSC, `auth/indexing` for Indexing API). The Indexing API rejects webmasters tokens.
- `submit_batch` uses true HTTP multipart batch requests via `new_batch_http_request()`, chunked at 100 per request. 200 URLs cost 2 API calls instead of 200.
- `_make_callback(url)` factory in `submit_batch` avoids the late-binding closure bug common in loop-based batch implementations.
- All outputs are JSON, wrapped with `_meta` block for context (tool name, params).
- Retry with exponential backoff on 429/5xx. No retry on 404.
- In-memory quota tracker warns at 180/200 requests.

## Development

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest tests/ -v
```
