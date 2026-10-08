# SEO expert feedback validation

Date: 2026-10-08. Base: main `cda1eef83da2183faceffa54bad9ae21cf9048e0`, published package 1.3.0, 85 tools. This feedback branch is independent of unmerged PR #27 and keeps the same tool count. Its fixes are not part of the stable package yet.

## Feedback and verification boundary

The reporter described real-account testing across GSC, Bing and GA4. Those account results were supplied feedback, not replayed here. The implementation uses controlled provider-shaped fixtures and the real adapter/tool consumers. No account credentials, production provider writes or private property inventory were used.

| Ticket | Confirmed problem and resulting contract |
| --- | --- |
| #28 | Bing contradictory counts crashed strict CTR validation. Preserve counts and source anomaly diagnostics, expose anomalous CTR as null, retain comparison window guards. |
| #29 | String-list flags lacked repetition help. Accept repeated values or JSON arrays of strings; preserve commas within URLs. |
| #30 | Traffic comparison included recent incomplete days. Use equal adjacent windows ending three days before today; missing queries remain unavailable and metric rules are candidates, not causal explanations. |
| #31 | Daily Bing rows consumed the query limit. Aggregate exact queries before sorting/limiting; keep the daily shape through `--daily`. Local sums/weighted metrics are calculations over returned rows, not provider completeness. |
| #32 | Diagnostic search-operator queries polluted default cannibalization candidates. Apply the documented conservative token filter, expose excluded count and provide an opt-in. Parenthesized/other operator syntax is not comprehensively parsed. |
| #33 | Legacy Anthropic crawler token. Check ClaudeBot, Claude-User and Claude-SearchBot separately using current official guidance. |
| #34 | Full discovery surface was required every session. Optional startup allowlist keeps core discovery; capabilities and tools/list share the same resolved snapshot. CLI keeps the full registry. |

The nullable-CTR change also exposed a quick_wins consumer failure. Its regression now excludes eligible rows with unavailable CTR and counts them explicitly. A missing comparison-side row or legacy 0/0 CTR may still retain compatibility placeholders; field-level metadata must mark them unavailable. Direct Bing positions absent or null at source are now null. Missing source counts retain legacy placeholders with bounded `unavailable_metrics` and unavailable field evidence; aggregates propagate these markers. A missing count input also makes its row/total comparison delta null, independently of the other count. Explicit provider zeros remain observed values.

## Catalogue measurement

Measurement: call the actual FastMCP `list_tools()` API in fresh processes; serialize each Tool with `model_dump(mode="json", exclude_none=True)` into compact UTF-8 JSON (`ensure_ascii=False`, separators comma/colon).

| GSC_MCP_TOOL_FAMILIES | Tools | JSON bytes |
| --- | ---: | ---: |
| Unset | 85 | 70110 |
| analytics,seo,sitemaps,links | 30 | 24821 |
| sitemaps,links | 11 | 7957 |

The 30-tool selection is about 65% smaller in this serialization. This is not the JSON-RPC envelope size, a tokenizer-independent token saving or measured session latency. The supplied approximately 17000-token observation was not independently tokenized.

## Validation

- Complete mocked Python suite: **1492 passed** on Python 3.11.15 and Python 3.13 (`python -m pytest tests/ -q`).
- Local browser suite: **84 passed**. Four EN/FR documentation screenshots were refreshed after inspecting their diffs for the already published 1.3.0 release summary.
- Documentation source tests: **5 passed**; translation verification: **42 pages**; Astro diagnostics: **0 errors, 0 warnings, 0 hints** across 32 files. Documentation builds **45 pages**; built-site checks: **23 passed**. The content synchronization phase emitted duplicate-ID cache notices, distinct from the clean diagnostics result.
- Source distribution and wheel build successfully; `twine check` passes for both local artifacts. An isolated Python 3.11 wheel installation passes actual MCP discovery/capability matching, full CLI discovery under restricted MCP selection, URL JSON/help, and Bing aggregation/anomaly/availability probes.
- Independent review passes after closing the absent-source-value and unknown-delta-dependency findings. Its final public comparison probe returns null/unavailable for the unknown click delta and preserves the independent impression delta.

The local artifacts retain source version 1.3.0 for verification only; they were not published over the existing release. Remote CI and deployment are not established by these checks. Source accuracy against the reporter's real account still needs a separate replay. Passing fixtures do not establish general SEO diagnostic accuracy.

Official crawler reference: [Anthropic crawler purposes and robots controls](https://support.claude.com/en/articles/8896518-does-anthropic-crawl-data-from-the-web-and-how-can-site-owners-block-the-crawler).
