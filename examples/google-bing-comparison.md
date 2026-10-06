# Google and Bing Comparison

Compare how the same site performs in Google Search Console and Bing Webmaster Tools without treating their positions, reporting windows or coverage as interchangeable.

Requirements:

- Google property: `sc-domain:yourdomain.com`
- Bing verified site: `https://yourdomain.com/`
- both credential families configured
- `gsc-mcp-tools>=1.2.0`

## Start with a bounded comparison

> Compare Google and Bing performance for yourdomain.com over the last 28 days. Confirm access first, compare queries and pages, and keep provider-specific position values side by side.

The assistant should call `list_properties`, `bing_sites_list` and `compare_search_engines`. It should show click and impression deltas only when the tool reports equal exact observed windows.

## Find opportunities per engine

> Run `quick_wins`, `seo_striking_distance` and `prune_candidates` separately for Google and Bing. Show which opportunities appear in both engines and which are engine-specific. Do not recommend deletion from missing or partial provider data.

These are supported Bing analyses. `traffic_drops`, `seo_lost_queries`, `check_alerts` and `seo_cannibalization` require contracts that Bing does not currently provide, so an explicit refusal is the expected result.

## Compare one page

> Compare this page across Google and Bing: https://yourdomain.com/your-page. Use Google's URL Inspection and page-query data, then Bing URL traffic and page-query data. State clearly which fields are unavailable in either provider.

`bing_url_info` is not equivalent to Google's URL Inspection API. Do not turn Bing URL data into an indexation verdict.

## Investigate visibility differences

> For queries or pages with a large click or impression difference, list the observed evidence and three hypotheses to investigate. Do not claim that one engine caused the difference, and do not subtract Google and Bing positions.

Useful follow-ups include on-page technical checks, internal-link audits, structured data validation and crawl trends. Label those findings separately from provider performance data.

## Prepare a report

> Produce a report with four sections: shared opportunities, Google-specific findings, Bing-specific findings, and unknowns. Every recommendation must name the supporting query or URL and metric. Keep measured facts, derived CTR and hypotheses separate.

## Guard writes

> If a recommendation involves a Bing URL or feed submission, a sitemap change, Google Indexing API or IndexNow, stop before the mutation. Name the tool, exact target and number of affected items, then ask for explicit confirmation. After an approved call, report the provider response without claiming crawl or indexation.
