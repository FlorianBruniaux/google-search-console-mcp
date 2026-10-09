# U04 agent evidence-review pilot, 2026-10-09

Scope: `.claude/workflows/mega-audit.js`, the SEO reporter, indexing and sitemap
roles, and the new read-only evidence reviewer. This is a bounded U04 slice of
issue #39, not a complete orchestration implementation. No live Google, browser,
Perplexity or model calls were made. No global runtime configuration was changed.

## Corrected contract

The workflow refuses to run unless its host supplies `agent`, `parallel`,
`pipeline`, `phase` and `log`. No implementation of that host was found in the
repository. The workflow source retains the existing host contract; native
Claude/Codex execution is unverified. `claude` was absent from the validation PATH.

`maxPages` accepts 1 through 10 (default 10) and bounds the selected URL list passed
to the existing page loop. `maxConcurrentAgents` accepts 1 through 4 (default 2).
A semaphore bounds invocations of the host's agent function across its existing
scheduling. These bounds do not enforce aggregate provider requests made inside
model steps, token usage or a global provider budget. Prompts request a bounded
sample; actual model compliance remains unmeasured.

Tool arguments were checked against both `gsc_mcp.registry.TOOLS` signatures and
the actual FastMCP `list_tools()` input schemas, without invoking provider tools:

| Tool | Checked callable arguments |
| --- | --- |
| `get_site_details` | `site_url` |
| `get_search_analytics` | `site`, `days`, `dimensions`, `row_limit` |
| `get_advanced_search_analytics` | `site`, `date_range_days`, `dimensions`, `row_limit` |
| `compare_search_periods` | `site`, `days`; no dimensions or limit |
| `inspect_url` | `url`, `site` |
| `batch_url_inspection`, `check_indexing_issues` | `urls`, `site` |
| `sitemap_audit` | `site`, `sitemap_url` |
| `page_health_score` | `site`, `url`; score may be unavailable in the pilot |
| `get_search_by_page_query` | `site`, `days`, `row_limit`; no page URL filter |
| `page_analysis` | `site`, `days`, `limit`; no page URL filter |
| `crux_page_vitals`, `crux_history` | `url` |
| `content_brief` | `site`, `page_url` |

The page schema accepts null health score and indexing status. A deep dive runs
only for an observed numeric score below 70 or explicit `isIndexed: false`.
UNKNOWN inspection results and missing search rows do not become non-indexed
pages. Sitemap observations describe fetch status and search visibility, not a
submitted/indexed ratio. Causal AI/traffic claims, invented durations/costs and
mandatory scores were removed from the synthesis instructions.

Optional invocation failures remain `{status: "unavailable", agent, error}` in the
source bundle. Discovery and synthesis failures stop the workflow. The reviewer
receives the same source bundle as synthesis plus its draft. Findings are appended
without automatic approval or silent correction. A reviewer failure or missing
result marks the draft `unreviewed`. The reviewer has `Read` only and explicitly
disallows delegation, shell and editing tools. Scoped roles inherit native host
model settings; no Claude model aliases were copied into Codex configuration.

The SEO reporter uses corrected callable arguments when its existing weekly
report skill differs. That skill was deliberately not edited in this slice;
standalone skill behavior remains a separate scope.

## Executed checks

Before workflow changes, `tests/test_agent_workflow.py` reproduced 10 failures
and 1 passing scenario. Failures included the missing-host error, rejection of
nullable fields, absent review output and unbounded scheduling. After correction:

```text
PYTHONPATH=src /private/tmp/gsc-u00-validation/bin/python -m pytest tests/test_agent_workflow.py -q -p no:cacheprovider
12 passed
```

Node v22.18.0 executes the actual workflow source inside a controlled host. The
host substitutes only agent responses and the existing scheduling globals. Checks
cover missing runtime, nullable source propagation into the review prompt, four
observed/unknown deep-dive branches, page/concurrency bounds, optional-provider
failure, reviewer failure and invalid bounds. The controlled host validates the
schema's required keys and top-level field types. A separate failing check then
confirmed that an optional null result was dropped from the source bundle; it now
becomes unavailable with its agent label and reason. The four scoped role files
also passed Ruby's YAML structural parsing. The controlled host is not a native
schema-engine or agent-loader test. No source-grep assertions substitute for
behavior checks.

## Evidence limits and remaining scope

The checks prove local workflow routing and preservation of supplied fixtures,
not semantic model quality, real tool-call execution or end-to-end host operation.
Role/frontmatter review is structural and manual, not native agent loading.
No live model demonstrated claim detection, window mismatch detection or faithful
synthesis. A distinct reviewer invocation exists in the artifact; independent
review quality is unmeasured. User-visible draft prose can still be wrong and must
be assessed alongside the findings and source observations.

Issue #39 still needs a verified native workflow host, aggregate provider-budget
enforcement, real agent/provider trials, model-quality evaluation and Codex parity.
No new `.codex` role, skill projection or BM25 routing claim is made by this pilot.
