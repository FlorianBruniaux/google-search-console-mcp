# Installation and MCP client setup

This guide installs the published `gsc-mcp-tools` package, connects only the providers you use, and verifies the 96-tool registry in release 1.5.0. Python 3.11 or newer is required.

## Choose an installation mode

| Use case | Command | Upgrade path |
|---|---|---|
| Persistent MCP client | `uv tool install gsc-mcp-tools` | `uv tool upgrade gsc-mcp-tools` |
| One-time evaluation | `uvx gsc-mcp-tools` | Resolved on each launch |
| Existing Python environment | `pip install gsc-mcp-tools` | `pip install --upgrade gsc-mcp-tools` |
| Contributor checkout | `pip install -e ".[dev]"` | Pull the repository and reinstall if metadata changes |

For Codex and Claude Desktop, prefer the persistent `uv tool` installation. Pointing the client at the installed executable avoids an extra `uvx` launcher process for every active MCP server.

## Install the published package with uv

Install [uv](https://docs.astral.sh/uv/) first, then run:

```bash
uv tool install gsc-mcp-tools
command -v gsc-mcp-tools
gsc-cli list
```

`gsc-cli list` should print 96 commands for release `1.5.0`. Keep the absolute path returned by `command -v`; MCP clients do not always inherit the same `PATH` as your shell.

Upgrade later with:

```bash
uv tool upgrade gsc-mcp-tools
```

An installation created with `gsc-mcp-tools==1.3.1` stays pinned. Reinstall without the version constraint before using `uv tool upgrade`, or install the next explicit version with `--force`.

To reproduce this release exactly:

```bash
uv tool install --force gsc-mcp-tools==1.5.0
```

## Alternative installations

<details>
<summary>Run once with uvx</summary>

```bash
uvx gsc-mcp-tools
```

This is useful for evaluation. Do not use it as the persistent client command when you want the smallest process footprint.

</details>

<details>
<summary>Install in a Python virtual environment</summary>

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install gsc-mcp-tools
gsc-cli list
```

Use the absolute `.venv/bin/gsc-mcp-tools` path in the MCP client configuration.

</details>

<details>
<summary>Install a source checkout for development</summary>

```bash
git clone https://github.com/FlorianBruniaux/google-search-console-mcp
cd google-search-console-mcp
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
pytest -q
gsc-cli list
```

Use this mode only when developing or testing changes that are not yet published.

</details>

## Select MCP tool families (since 1.3.1)

Since version 1.3.1, `GSC_MCP_TOOL_FAMILIES` accepts a comma-separated family list. Release 1.3.0 predates this setting and exposes the full catalogue.

For a focused Google SEO session, set this non-secret variable in the MCP server environment:

```text
GSC_MCP_TOOL_FAMILIES=analytics,seo,sitemaps,links
```

Available families are `analytics`, `seo`, `inspection`, `indexing`, `sitemaps`, `ga4`, `cross`, `crux`, `technical`, `drift`, `content`, `editorial`, `links`, `bing` and `core`. When the variable is absent or set to `all`, the server exposes all tools. `core` remains exposed with every selection. Unknown family names and an empty selection fail startup.

Restart the MCP server or client after changing the setting: an existing process keeps its startup selection. Check the client's actual MCP tool list after restart. `gsc-cli list` continues to show the full catalogue, regardless of this variable.

Selection controls MCP discovery, not credentials, provider permissions or write authorization. Configure only the credentials you use; a selected tool can still fail when its required provider is unavailable. A smaller discovery response does not establish a particular token saving, which depends on the client and tokenizer.

## Configure provider credentials

Install the server once, then add only the credentials required by the provider families you use.

| Provider | Configuration | Required variable |
|---|---|---|
| Google Search Console | [Google setup](google-setup.md) | `GSC_SERVICE_ACCOUNT_PATH`, or `GSC_CREDENTIALS_PATH` plus an interactive OAuth login |
| Google Analytics 4 | [Google setup](google-setup.md#step-6-add-the-service-account-to-ga4-optional) | `GA4_PROPERTY_ID` plus Google credentials |
| Chrome UX Report | Enable the CrUX API and create a Google API key | `CRUX_API_KEY` |
| Bing Webmaster Tools | [Bing setup](bing-setup.md) | `BING_WEBMASTER_API_KEY` |
| IndexNow | Verify a key on each target host | Key passed explicitly to `indexnow_submit` |

Do not put API keys in prompts or tool arguments unless the tool contract explicitly requires one. `BING_WEBMASTER_API_KEY` belongs in the server environment. The Bing Webmaster key and the per-host IndexNow key are different credentials.

## Codex setup without global process proliferation

Codex starts one stdio MCP server for each task that loads it. Keep the complete definition disabled in the private user configuration, then enable it only in projects that need search data.

Add this to `~/.codex/config.toml`:

```toml
[mcp_servers.gsc-mcp]
command = "/absolute/path/to/gsc-mcp-tools"
enabled = false
startup_timeout_sec = 60
tool_timeout_sec = 90

[mcp_servers.gsc-mcp.env]
GSC_SERVICE_ACCOUNT_PATH = "/absolute/path/to/service-account.json"
GSC_SKIP_OAUTH = "true"
```

Remove every provider variable you do not use. This user-level file is private but still contains sensitive values, so keep its permissions restricted.

In each trusted project that needs the server, create `.codex/config.toml`:

```toml
[mcp_servers.gsc-mcp]
enabled = true
```

Add `.codex/config.toml` to the project `.gitignore`, restart the task, then verify from that project:

```bash
codex mcp get gsc-mcp
```

The resolved configuration should show `enabled: true` and the direct executable path. Outside an enabled project, the same command should show the server as disabled.

## Claude Desktop setup

Add the server to `~/Library/Application Support/Claude/claude_desktop_config.json` on macOS:

```json
{
  "mcpServers": {
    "gsc-mcp": {
      "command": "/absolute/path/to/gsc-mcp-tools",
      "env": {
        "GSC_SERVICE_ACCOUNT_PATH": "/absolute/path/to/service-account.json",
        "GSC_SKIP_OAUTH": "true"
      }
    }
  }
}
```

Remove unused variables and restart Claude Desktop. Saving the JSON file does not restart an existing MCP process.

## Verify the installation

Run these checks from the same environment used by the MCP client:

```bash
gsc-cli list
gsc-cli get-capabilities
```

`list` verifies package and registry loading. `get-capabilities` reports declared credential families; it does not prove that an external API accepts them. Verify provider access separately with `list-properties` for Google or `bing-sites-list` for Bing.

## Troubleshooting

**The client launches an older release:** run `uv tool list`, then `uv tool upgrade gsc-mcp-tools`. If the receipt is pinned, reinstall without `==...`.

**PyPI has the release but uv cannot resolve it immediately:** retry from outside the source checkout with an explicit refresh:

```bash
uv tool install --force --refresh --default-index https://pypi.org/simple gsc-mcp-tools
```

**The client cannot find the executable:** use the absolute path returned by `command -v gsc-mcp-tools`.

**Many `uvx` and server processes remain:** replace `uvx gsc-mcp-tools` with the persistent executable, disable the user-level Codex server, enable it only per project, then fully restart the client. Existing processes keep their old configuration until they exit.
