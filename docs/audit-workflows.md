# Bounded audit workflows

`search_change_breakdown` and `link_targets_audit` are included in `gsc-mcp-tools==1.3.0`, which exposes 85 tools. Follow the [installation instructions](installation.md) to use them. Examples below are synthetic explanatory fragments, not live Google or network runs.

Release 1.4.0 includes the AI-appearance correction, report contract/budget, weekday reference and crawl preview below. It exposes 89 tools; follow [installation](installation.md) to upgrade.

## Search appearances do not identify AI exposure

`ai_overviews_impact(site, days=28, limit=100)` keeps its public name but reads generic Web `searchAppearance` rows. It requests that dimension alone, as documented by Google; it does not return a query-level AI exposure comparison. Raw returned appearance values are observations, not an identification rule for AI Overviews.

`source_scope` is `web_search_appearance`; `ai_exposure.status` is `unavailable` and `ai_exposure.verification` is `unverified`. Success distinguishes observed and empty appearances. HTTP 400 retains the legacy error alias while identifying an invalid or unsupported request; HTTP 403 identifies access denial. Neither empty data nor these errors establishes AI presence or absence. Values requested with `dataState=all` can change during finalization. No causal click-loss estimate is produced.

See Google's [search-appearance request guidelines](https://developers.google.com/webmaster-tools/v1/how-tos/all-your-data#getting_search_appearance_data) and [AI-feature measurement limits](https://developers.google.com/search/docs/appearance/ai-features#measuring-the-performance-of-your-site). Tests use synthetic provider responses; they do not verify a live property's capabilities.

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

## Report evidence and response budget (since 1.4.0)

Release 1.4.0 adds `report_contract` to `search_change_breakdown`. It separates observed metric pointers (`facts`), calculated deltas and CTR (`calculations`), and absent evidence (`unavailable`). `hypotheses` is empty. Each finding has an identifier scoped to the exact GSC property, dimension, key and rule version. The snapshot fingerprint hashes the report and all retrieved sanitized observations, including rows hidden by the display limit. It does not store a snapshot or provide a retrieval handle.

`output_max_bytes=None` retains the full report. Set a positive integer, for example `output_max_bytes=50000` or CLI `--output-max-bytes 50000`, to bound the UTF-8 JSON envelope, including `_meta`. Budgeted CLI output preserves that envelope even without `--meta`; the final CLI newline and MCP transport wrapper are outside the count. Inspect `response_budget.status` and `serialized_bytes`.

If rows do not fit, the response contains `RESPONSE_BUDGET_EXCEEDED`, omits displayed rows and findings with explicit counts and unavailable-value reasons, and preserves source errors, coverage and summaries. If even that envelope cannot fit, the call raises `ResponseBudgetExceeded` with the minimum required byte count and source errors. It never returns clipped JSON. No automatic detail fetch, requery or durable storage is available.

## Compare disjoint periods with the same weekdays (since 1.4.0)

```python
search_weekday_reference(
    site="sc-domain:example.com", days=28, end_date="2026-09-30",
    dimensions=["query"], filters=None, search_type="web",
    aggregation_type="auto", row_limit=1000, max_requests=20, limit=50,
)
```

This wrapper makes one `search_change_breakdown` call with `data_state="final"`. Its default end date is three days before the current date in `America/Los_Angeles`. An explicit end date must respect that policy. The earlier window shifts by `7 * ceil(days / 7)` days: equal-length periods remain disjoint and start on the same weekday, including nonmultiples of seven. The child tool's physical-request budget still applies.

`weekday_reference` retains the effective dates, shift, lag policy, upstream metadata and coverage reasons. Missing dates or incompatible/unknown aggregates leave its delta null and status `unavailable`. A three-day lag and a final-data request do not certify provider completeness. An observed reference describes clicks and impressions; it does not establish annual seasonality, a search-system incident or a causal explanation. This wrapper has no response-byte-budget parameter.

## Preview a SiteOne export in memory (since 1.4.0)

```python
crawl_import_preview(report_json='{"results":[]}', producer="siteone")
```

Provide the export as a JSON string. This adapter does not read a path, launch a crawler, fetch a URL, install software, persist evidence or join GSC data. It supports the pinned SiteOne JSON exporter schema; tests use exporter-shaped fixtures, not a real crawl export. Inputs are capped at 2 MiB UTF-8, 5,000 rows and depth 20; previews retain at most 50 accepted rows and bounded error/rejection samples.

The result preserves producer declarations, raw URL identities and source-byte/configuration hashes. Selection and execution timezone stay unknown when unverified. Rejected or omitted records retain counts and reasons. Imported strings are data, never instructions. Extra values and unsupported configuration are withheld; raw input never enters `_meta.params`. Credential-bearing URLs are rejected rather than echoed. Imported quality scores remain third-party heuristics with `ranking_signal=false`. An empty export does not prove that a page is absent, healthy or unindexed.

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

## Follow a declared page change (since 1.4.0)

`seo_change_impact` is included in release 1.4.0 and its 89-tool registry. This explanatory example uses a caller-declared event, not an observed deployment or live follow-up:

```python
seo_change_impact(
    event={"site": "sc-domain:example.com", "url": "https://example.com/guide/",
           "changed_at": "2026-09-15T12:00:00+02:00", "timezone": "Europe/Paris",
           "description": "Revised page title", "revision": "caller-revision"},
    baseline_start="2026-09-08", baseline_end="2026-09-14",
    comparison_start="2026-09-16", comparison_end="2026-09-22",
    filters=None, search_type="web", align_weekdays=False,
    page_mapping=None, concurrent_changes=["Caller reports a concurrent navigation edit"],
    row_limit=1000, max_requests=20, limit=50,
)
```

The event requires `site`, `url`, `changed_at`, `timezone` and `description`; `revision` and `baseline_id` are optional declarations. The timestamp includes seconds and an explicit offset matching the IANA timezone. The packaged `tzdata` dependency supplies a fallback on hosts without system timezone data. No deployment time is inferred from Git or fetched HTML. The caller keeps the event and report: `persistence.status` is `not_persisted`.

Windows must be ordered, nonoverlapping and equal in inclusive length. They exclude the whole event date in Google's `America/Los_Angeles` calendar. `align_weekdays=True` also requires matching start weekdays. The three-day reporting lag in `maturity_policy` is a preflight policy; `provider_finalization_verified=false` explicitly avoids claiming finalized observations.

The tool reuses `search_change_breakdown` with identical filters and finalized-data requests. Caller page filters are rejected. An optional `page_mapping` has exactly `baseline_url` and `comparison_url`, one matching the effective event URL. Two distinct mapped URLs are requested together in both windows; totals describe that combined scope. No canonical or redirect discovery occurs. Inspect the retained `search_evidence` coverage, missing dates/rows, request limits and aggregation compatibility described above.

`comparison.status` is `observed` or `unavailable`. Missing or immature follow-up returns `insufficient_post_change_data`; missing baseline, incompatible aggregation and provider failures retain their reasons. Null observations never become zero. Available raw counts can survive an unavailable comparison, but its `descriptive_delta` stays null. Observed deltas report clicks, impressions and CTR percentage points. Collection timestamps retain the UTC interval.

`concurrent_changes` contains caller declarations. Seasonality, search-system changes and other edits can affect the windows. `attribution.causal_effect` stays null and its status is `not_identified`; a before/after observation establishes no causal lift, ROI, significance or ranking guarantee. Controlled fixtures do not establish usefulness for a real property. For pre-publication text checks, use [editorial workflows](editorial-workflows.md).
