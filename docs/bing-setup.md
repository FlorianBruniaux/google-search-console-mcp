# Bing Webmaster Tools setup

This guide connects the published MCP server to Bing Webmaster Tools. One account-level API key can access every verified site visible to that Bing account, while each tool call still names its target site.

## Prerequisites

- `gsc-mcp-tools>=1.2.0`, installed with the [installation guide](installation.md)
- a Bing Webmaster Tools account
- at least one verified site in that account
- permission to generate an API key

## Step 1: Verify the sites you need

Sign in to [Bing Webmaster Tools](https://www.bing.com/webmasters/) and confirm that each target site appears in the site selector. Importing sites from Google Search Console or completing Bing's verification flow happens outside this MCP server.

Use the exact site form returned by Bing, including its scheme and trailing slash where present, for example `https://example.com/`.

## Step 2: Generate the Webmaster API key

Open the API access settings in Bing Webmaster Tools and generate an API key for your account. Store it in a secret manager. Do not commit it, paste it into a prompt, or pass it as a Bing tool argument.

Set it in the server environment:

```bash
export BING_WEBMASTER_API_KEY='<from-your-secret-store>'
```

For Codex or Claude Desktop, add the same variable to the client configuration described in the [installation guide](installation.md).

## Step 3: Verify read access

Run:

```bash
gsc-cli get-capabilities
gsc-cli bing-sites-list
```

`get-capabilities` should report that a Bing credential is declared. `bing-sites-list` is the access check: it must return the sites visible to the account. A declared environment variable alone does not prove that Bing accepts the key.

Query one verified site:

```bash
gsc-cli bing-query-stats --site https://example.com/ --days 28 --limit 20
gsc-cli bing-page-stats --site https://example.com/ --days 28 --limit 20
```

## Bing Webmaster and IndexNow use different keys

| Credential | Scope | Used by |
|---|---|---|
| `BING_WEBMASTER_API_KEY` | Bing account and its verified sites | All `bing_*` tools |
| IndexNow key | Target host or subdomain where the key can be verified | `indexnow_submit` |

Do not reuse the Bing Webmaster API key as an IndexNow key. The server reads the Webmaster key from the environment. `indexnow_submit` receives a separately verified IndexNow key according to its tool contract.

## Read and write boundaries

The public Bing API exposed here covers performance, crawl, URL traffic, feeds, backlinks and guarded submissions. It does not expose every feature visible in the Bing Webmaster Tools web interface.

- Bing URL information is not equivalent to Google's URL Inspection verdict.
- The public API used here does not expose Bing AI Performance.
- Keyword research endpoints that returned HTTP 400 during canary validation are not registered.
- Some quota, crawl-issue, nested-backlink and feed-removal semantics remain explicitly unknown or runtime-unverified.

Before any write, the assistant should state the exact tool, site and affected URLs or feeds, then wait for explicit confirmation. An accepted submission proves only that the provider accepted the request, not that a URL was crawled or indexed.

## First prompt

Use the [Google and Bing audit prompt](starter-prompt.md#google-and-bing-audit) when both providers are configured, or start with:

```text
Use Bing Webmaster data for https://example.com/ over the last 28 days.

1. Confirm access with bing_sites_list.
2. Report top queries and pages with clicks, impressions and derived CTR.
3. Report crawl trends, URL traffic and backlinks without making indexation claims.
4. Run quick_wins and seo_striking_distance with engine="bing".
5. Separate observed facts, derived values and recommendations.
6. Do not call any write tool without naming the target and asking for confirmation.
```

## Troubleshooting

**`BING_WEBMASTER_API_KEY` is reported missing:** the MCP client did not inherit the shell variable. Add it to the client's `env` configuration and restart the client.

**The key exists but no sites appear:** sign in to Bing Webmaster Tools with the account that generated the key and confirm that the site is verified and visible there.

**A site argument is rejected:** copy the exact site URL returned by `bing-sites-list` instead of guessing a domain-property form.

**A write returns accepted but the page is not indexed:** this is not a contradiction. Submission, crawl and indexation are separate states and must be measured separately.
