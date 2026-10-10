# Backlog execution, 10 October 2026

Base: `28e8e4ad47fc5fa9db3bcb1cbd3471958abc5b2b`, isolated branch `codex/seo-backlog-execution`. The primary checkout and other sessions' untracked handoffs/research were preserved. These are source changes, not a new PyPI version or a production rollout.

## Implemented and checked

- #74: absent query/page rows return null metrics, true zero counts remain zero, zero-denominator CTR is unavailable, and sorting/delta guards preserve their meaning. Six failing comparison cases preceded the correction. The integrated suite passed 1,957 tests at that stage.
- #38/#39: an opt-in read-only acquisition session, durable attempt ceiling, source-scope validation, immutable shared observations and dedicated MCP startup surface are implemented. Retried/failed/concurrent calls, configuration reuse, GA4 property scope and hidden Google credential replay have behavioral regressions. GA4 automatic SDK/transport retries are disabled only inside a budgeted session. A real MCP initialize/list/call exchange returned unknown indexing and reused an identical response with zero provider attempts.
- Native Codex adapter: the installed CLI completed a high-reasoning standalone synthetic source report. A complete bounded runner then acquired a supplied empty-observation indexing matrix twice, returned a draft and a fresh reviewer response, and reported two tool calls and zero provider attempts. This proves the observed native path on that packet, not live Google/Bing access, nine-role parallel dispatch or expert report accuracy. Claude's command boundary passed controlled executable tests; a live Claude run is not verified.
- #6: a separate claim-report evaluator and label-free author packet preparation are implemented for traffic, harmful competition and report fidelity. Missing references, split leakage, duplicate claims and same-identity review are refused. Synthetic correctness never approves release. Human provenance remains a caller declaration.
- #4/#5: offline FR/EN lexical intent and ordered variant-candidate prototypes are implemented and deliberately excluded from MCP discovery. The existing evaluator consumes their predictions and marks the supplied synthetic fixture ineligible for release. No real query-quality result is claimed.

Before independent review, the full declared-dependency Python environment passed 1,990 tests. Final review findings, final verification and delivery identifiers are appended after they exist. No test count below should be inferred from this pre-review run.

## Inputs still missing and work retained

| Scope | Next concrete input or condition | Why it remains open |
|---|---|---|
| #6, #38/#39 semantic quality | Authorized FR/EN cases, independently reviewed labels, pre-tuning targets | Native output and fixtures do not supply human ground truth |
| #41 extraction adoption | Annotated article/product/local/forum/JS-shell HTML and acceptable resource/quality criteria | Optional extraction already exists; no evidence permits changing its default |
| #42 Unlighthouse | Actual export, producer version, device/configuration, sampled routes and collection metadata | A SiteOne export does not establish another producer's schema |
| #49 SERP/backlinks | Representative authorized exports with locale/device/time and coverage semantics | No export from those producers was supplied |
| #53 Bulk Export | Representative local site/URL-table data and partition/revision metadata | Cloud access, backfill and API reconciliation cannot be invented |
| #45 temporal competition | Human-supported daily query/page cases and task-specific targets | Multi-URL presence/alternation alone does not establish harmful competition |
| #22 page similarity | Independent page-pair labels, usable extracted passages and thresholds | Query labels cannot validate page similarity |
| #47 controlled follow-up | Declared change, valid control cohorts, metrics and reviewed method | Descriptive before/after is already implemented; causal ground truth is not provided |
| #52 graph extension | Imported graph plus a named decision beyond the existing map | Added centrality cannot be justified from tool availability alone |
| #50 research federation | Selected authorized corpus and verified retrieval interface | No consulted-source retrieval benefit is demonstrated |
| #9 citability | Explicit page-level decision and evaluation design | Referral counts cannot validate citation probability |
| #7 model backend | Named-task held-out gain over rules and measured budget/footprint | No baseline comparison authorizes adding a backend |
| #51 crawler | Recorded inventory/restart/rendering gap beyond current imports | No measured need authorizes another collector dependency |

No human dataset, external export or experiment was fabricated. #10 remains the tracking parent. Full specialist-role projections, native Claude execution and expert validation remain distinct work even though a Codex packet author/reviewer path now exists.

Operational instructions: [source workflow](../bounded-native-audit.md). The model runner is optional; source acquisition alone remains usable.

## Independent review and final source verification

GPT-6-astra, high reasoning, reviewed the complete tracked/untracked implementation with fresh context and ran 53 targeted tests. Its verdict was with fixes, with 3 Important findings and no confirmed Critical finding. Each finding was reproduced with a failing regression before correction:

- httplib2 stale-connection retries now reserve at the physical HTTP dispatch boundary, including new connections. A real HttpRequest/Http path cannot dispatch a second request with a ceiling of 1.
- Bing URL arguments use the explicitly configured Bing scope, including page-query and feed URL parameters. Pagination numbers remain pagination numbers.
- Native supported claims require an acquired-observation reference; the draft alone cannot support a reviewer fact. This does not prove semantic correctness.

The additional minor SQLite connection-lifetime finding was reproduced and corrected with deterministic connection closure. Post-execution native output-size checks remain a documented limitation; no resource exhaustion was reproduced. Human diagnostic accuracy, live Claude behavior, adversarial Codex confinement and live authenticated providers were outside the reviewer's verified scope and remain unverified.

After those corrections, the full Python suite passed **1,994 tests** in the dedicated environment with declared dev/content dependencies, including real Trafilatura. The final native Codex runner returned draft and fresh review again using high reasoning, with 0 provider attempts and 4 cumulative tool calls under the reused durable run ID (2 per invocation).

Site checks: 6 documentation-source tests, translation hash verification, Astro check with 0 errors/warnings, a 61-page production build and 29 distribution tests passed. The browser run passed 104 cases and found 9 intentional update-banner snapshot changes. Pixel comparison showed every changed pixel inside the dated update banner (vertical range 82..141); the 9 references were updated, then all 16 local visual cases passed without update mode. This covers all 113 browser cases across the full run and focused rerun, not a claim that the first combined command passed.

Wheel and source distributions built successfully and passed Twine metadata checks. A fresh Python 3.13 environment installed the wheel outside the checkout: CLI discovery retained 96 tools, new modules imported from that installed wheel, and offline acquisition retained unknown indexing with 0 provider attempts. Distribution files were not uploaded to PyPI. Remote CI and delivery are separate from these local results.
