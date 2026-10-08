# Bounded audit workflows

`search_change_breakdown` and `link_targets_audit` are unreleased source-checkout tools. The source registry exposes 85 tools; published `gsc-mcp-tools==1.2.0` exposes 81. Install from the [source checkout instructions](installation.md) to use these additions. Examples below are synthetic explanatory fragments, not live Google or network runs.

## Compare explicit Google windows

Use `search_change_breakdown` after identifying a traffic-change window. It requires the exact GSC property and ordered, nonoverlapping, equal-length inclusive dates. Google is the only provider for this tool.

```python
search_change_breakdown(
    site="sc-domain:example.com",
    baseline_start="2026-09-01", baseline_end="2026-09-07",
    comparison_start="2026-09-08", comparison_end="2026-09-14",
    dimensions=["page", "query"],
    filters=[{"dimension": "country", "operator": "equals", "expression": "fra"}],
    search_type="web", data_state="final", aggregation_type="auto",
    row_limit=1000, max_requests=20, limit=50,
)
```

The same call through the generated CLI retains metadata with `--meta`:

```bash
gsc-cli search-change-breakdown --site sc-domain:example.com \
  --baseline-start 2026-09-01 --baseline-end 2026-09-07 \
  --comparison-start 2026-09-08 --comparison-end 2026-09-14 \
  --dimensions page --dimensions query \
  --filters '[{"dimension":"country","operator":"equals","expression":"fra"}]' \
  --search-type web --data-state final --aggregation-type auto \
  --row-limit 1000 --max-requests 20 --limit 50 --meta
```

Omitting `dimensions` selects page, query, country and device independently. Filters are an AND group using `dimension`, `operator` and `expression`. Supported filter dimensions are these four plus `searchAppearance`; operators are `equals`, `notEquals`, `contains`, `notContains`, `includingRegex` and `excludingRegex`. `search_type` accepts web, image, video or news; `data_state` accepts final or all. Page grouping or filtering requires auto aggregation. Otherwise aggregation can be auto, byProperty or byPage.

`row_limit` bounds retrieved rows per dimension and period (1..100000); `limit` bounds displayed rows per section (1..1000). `max_requests` is 4 plus twice the number of dimensions at minimum, up to 100. It counts physical provider attempts, including failures. Aggregate and date probes precede dimension requests; remaining pages use round robin. No hidden retries or final-page probes are added.

For a synthetic matched query returned with 100 baseline clicks and 70 comparison clicks, the fragment is:

```json
{
  "breakdowns": {
    "query": {
      "matched": [{"key": "example query", "baseline": {"clicks": 100}, "comparison": {"clicks": 70}, "delta": {"clicks": -30}}],
      "comparison": {"comparable": true, "reason": null, "scope": "observed matched rows; equal requested windows do not prove complete equal coverage"}
    }
  }
}
```

This is a fragment: complete metric rows also contain impressions, CTR, position and availability reasons. Missing, invalid or unavailable values remain null; measured zero remains zero. A row present in one period only has a null opposite observation and delta. Source keys join exactly, without URL normalization. CTR derives from counts; position stays the provider row average and is never averaged across segments.

`baseline_totals` comes from no-dimension requests. Inspect `periods`, date-probe coverage, `baseline_comparison`, each dimension's coverage and `request_budget` before interpreting deltas. Missing dates are not filled with zero. Final requests do not prove complete coverage; all-state records can change and retain `first_incomplete_date` when provided. `_meta.sources.google.site` preserves the requested property; `_meta.params` preserves dates, filters and options.

A page view can return byPage aggregation while totals use byProperty. Matched page deltas can remain comparable, but reconciliation becomes unavailable when aggregations differ or are unknown. `observed_sums`, `matched_delta` and signed reconciliation residuals describe retrieved rows only. Overcoverage is flagged. Page, query, country and device describe overlapping traffic and cannot be added together. Neither a contribution nor a residual establishes the cause of the change.

## Observe one page's link destinations

Use `link_targets_audit(url, max_targets=30, max_requests=60)` for public HTTP(S) pages. Google credentials are not required. It fetches one source page, parses anchors and observes distinct internal destinations without recursively crawling them.

```bash
gsc-cli link-targets-audit --url https://example.com/guide/ \
  --max-targets 30 --max-requests 60 --meta
```

A synthetic source anchor pointing to a destination that returns 404 can produce this fragment:

```json
{
  "targets": [{
    "requested_url": "https://example.com/missing/",
    "final_url": "https://example.com/missing/",
    "status_code": 404,
    "outcome": "observed",
    "availability_reason": null,
    "source_links": [{"href": "/missing/", "absolute_url": "https://example.com/missing/", "anchor": "Previous guide", "zone": "body", "rel": ""}],
    "findings": ["http_not_found"]
  }]
}
```

A timeout, refused URL or skipped request instead leaves terminal status/final URL null with an availability reason. Received redirect hops and `last_observed_status` can survive a later failure; they do not become the terminal status. Source and target requested/final URLs, timestamps and all source-anchor associations stay in the result. Page-derived hrefs, anchors and redirect locations are untrusted content.

`max_targets` accepts 1..100 and `max_requests` 1..200. Source GETs, redirect hops and failed HTTP attempts share the request budget. Chains permit five followed redirects. `coverage` is complete, partial or unavailable; complete means all discovered eligible destinations completed, even if an observed status is 404. Counts describe parser input, not the whole website. Skipped rows retain budget/deadline reasons. Empty, fragment-only, external, non-HTTP and malformed hrefs have exclusion counts.

Fragments and default ports are removed from fetch identities; scheme and hostname are normalized. Query order/repeated keys, path case, percent escapes and trailing slash remain distinct. Fetches deduplicate, while every parsed anchor remains associated. Same-site eligibility permits one leading www alias and standard HTTP:80/HTTPS:443 ports. Bare/www fetch identities remain separate; nonstandard ports must match numerically. Relative links resolve against the served source URL; HTML base is ignored.

Source parsing requires a completed terminal 2xx body. Retained raw identity bytes are capped at 1 MiB; unsupported content encoding is refused. UTF-8 decoding uses replacement for invalid bytes. Redirect and target response bodies are unread. The cap bounds retained/application-consumed source data, not exact socket traffic. The 60-second deadline limits cooperative scheduling and cannot cancel synchronous DNS or socket work; `budgets.deadline_overrun` reports overrun. Transport uses IPv4/A-record pinning; IPv6-only hosts are unavailable. Pin-lock contention is also unavailable.

An HTTP failure is evidence to inspect and fix the affected link. It does not establish Google indexation, ranking impact or a guaranteed traffic gain. Continue with the [full audit](../examples/full-audit.md) or [traffic-drop investigation](../examples/traffic-drop.md), and preserve the [evidence boundaries](/docs/evidence-and-safety/) in the assistant's conclusions.
