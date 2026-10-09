# Traffic decline and cannibalization playbook contract, 2026-10-09

Scope: repository-local `.claude` skills and their matching agents only. This review is a structural and manual walkthrough of instructions against the current source registry. It does not show model execution, Google Search Console responses, semantic accuracy, or a live site outcome.

## Callable check

The registered functions and their Python signatures were inspected through `gsc_mcp.registry.TOOLS` in the editable worktree environment. All names below appear in the agents' tool allowlists and in the skills' calls.

| Function | Arguments used by these playbooks | Contract point |
| --- | --- | --- |
| `list_properties` | none | Returns accessible property URLs and permissions. |
| `compare_search_periods` | `site`, `days` | Rolling property totals only; no dimension or limit parameter. |
| `traffic_drops` | `site`, `days` | Query-level heuristic candidates; missing current rows remain unavailable. |
| `analytics_anomalies` | `site`, `days` | Daily z-score outliers; no causal attribution. |
| `search_change_breakdown` | `site`, four explicit dates, `dimensions` | Equal disjoint windows, independent dimension views, period and coverage metadata. |
| `seo_lost_queries` | `site`, `days` | Current period may include incomplete days; a missing current query is represented as zero. Treated as a lead only. |
| `check_alerts` | `site`, `days` | Traffic concentration and high-impression, low-rank opportunities; no manual-action or security data. |
| `seo_cannibalization` | `site`, `days` | Shared-query candidates and a heuristic score over retrieved page rows; zero-click fallback is uniform share, not observed click split. |
| `get_advanced_search_analytics` | `site`, `dimensions`, `date_range_days`, `row_limit` | Observed query/page rows including CTR and position. |
| `get_search_analytics` | `site`, `days`, `dimensions`, `row_limit` | Separate page-level 90-day traffic observation. |
| `inspect_url` | `url`, `site` | Separate URL Inspection call per affected URL. |

## Manual scenario walkthroughs

1. **Rolling decline, date unknown.** Select the exact property, read rolling property totals and their returned dates, then query candidates and daily anomalies. Do not label the drop an algorithm penalty or convert an absent query into zero. If a dated split cannot be selected from observed data, ask for the approximate change date before the exact-window step.
2. **Dated decline with sparse rows.** Use equal, disjoint explicit windows in `search_change_breakdown`. Retain requested dates, observed dates, aggregation/comparison status and per-dimension coverage beside each finding. A baseline-only query has unknown comparison traffic, not an observed zero. Page, query, device and country contributions are alternative views of the same property traffic, so do not sum them.
3. **Shared query, different page intents.** Report the observed overlap and page roles. Do not propose a canonical, redirect or merge solely from a conflict score or ranking difference.
4. **Shared query, possible same intent.** Check 90-day query/page rows, 90-day page rows, and each URL's separate inspection. A missing page row or unavailable inspection stays `UNKNOWN`; the proposal remains conditional until intent and harmful conflict are supported. The instructions never authorize a write.

## Review limits and remaining issue scope

The instruction files were checked for callable names and arguments against the registry and reviewed for property/window provenance, observation versus arithmetic versus hypothesis, missing-data handling, and read-only boundaries. Frontmatter delimiters and required keys passed a structural check. The related existing registry, breakdown, SEO, analytics and inspection tests passed (158 tests); pytest emitted a cache-write warning because the managed worktree cache is not writable in the sandbox. This is not a user study or an end-to-end agent run. The two skills currently live under `.claude/skills`; Codex discovery/source projection and BM25 routing evidence remain open in issue #38 and were outside this U02 slice. No global skill or router was changed.
