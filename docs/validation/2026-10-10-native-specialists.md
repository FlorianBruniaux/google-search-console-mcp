# Native source-only specialists, 10 October 2026

Base: `bce9c69632a76381ea323344f089932d3acf0460`, merged PR #76. Branch: `codex/native-specialist-audit`. The primary checkout's unrelated untracked handoffs/research were preserved. Published Python version remains 1.5.0; these source changes are not a PyPI release.

## Contract and implementation evidence

`src/gsc_mcp/native_roles.py` supplies nine source-only role projections shared by the optional Claude/Codex runner. Explicit role selection consumes the acquisition packet without adding provider requests. Frozen JSON and fresh decoded copies prevent specialists or synthesis from mutating retained observations. Matching observation indices remain original; validation rejects references outside a specialist's selected sources and rejects generated-only support for a factual claim.

Concurrency is 1..4 within a pipeline. Native invocation reservations have a separate durable SQLite ceiling per immutable run configuration, default 2 and configurable 1..64. Failed native launches consume reservations; reopened/concurrent sessions cannot exceed the shared ceiling. Specialists leave two locally available synthesis/review slots, but another process can consume them. The author and independent reviewer remain separate sequential invocations. Missing sources, failed sources, native failure and exhausted budgets preserve separate reasons. None establishes a healthy branch.

These projections do not execute interactive skills or the legacy Workflow host. They do not expand the acquisition allowlist to ancillary HTML/CrUX fetches. In particular the schema projection has no compatible acquisition tool in this bounded CLI; it reports unavailable without a model invocation. This is a narrower source-review path, not a complete technical audit. The validator checks structure and references, not semantic truth. Model attempt counts are not token, monetary cost or runtime measurements.

Fifteen role/budget tests failed before implementation, then a complete-launcher test failed before CLI integration. The first integrated focused run passed 38 tests and the full Python suite passed **2,010 tests** with declared dev/content dependencies.

## Actual native paths

The installed Codex CLI with `gpt-6.1-sol` and Claude CLI 2.1.296 with its host-supported `opus` alias each completed the same offline source case using high reasoning/effort. Each run acquired an empty-report local indexing matrix twice, dispatched the indexing and sitemap specialists with concurrency bound 2, then produced a draft and a fresh review. Both specialists returned structurally valid reports with original observation references. The schema role was explicitly skipped with `no_matching_observations`.

Each run recorded **4 native attempts, 2 tool calls and 0 provider attempts**, under separate run IDs and a native ceiling of 4. Its overall status was `partial; semantic_quality_unverified`, reflecting the unavailable schema branch. CLI reports were private files in `/private/tmp/gsc-native-specialist-smoke-20261010/`; the source observations were illustrative `example.com` data, not authenticated provider measurements. The Claude reviewer corrected draft wording that confused a supplied URL with missing source reports, illustrating why returned draft/review should not be presented as human-approved truth.

These observations establish only those installed-host paths on that packet. They do not validate all nine specialties on real SEO cases, adversarial confinement, semantic accuracy, live-provider permissions or causal diagnoses. Human FR/EN cases, independent labels and pre-tuning targets remain required by #6 and the unresolved portions of #38/#39.

## Rulings and remaining limits

- The source roadmap is not task-start-compatible; the existing manual ledger and behavioral tests remain the execution record.
- Packaged profiles are narrow projections, not copied Claude configuration or new repository/global skills. Model identifiers are explicitly chosen for each native host; no global client settings change.
- Native-attempt persistence starts when this counter is introduced; earlier prototype invocations cannot be reconstructed. The existing provider/tool ledger remains compatible when configuration is unchanged.
- There is no claimed measured token/cost bound or globally shared concurrency bound. Cross-process attempt reservations remain atomic.
- Native log/output files remain size-checked after execution. No runtime disk-write ceiling is established; the inherited prototype limitation remains documented.
- No dataset or producer export was invented. Extraction adoption, import producer adapters, harmful competition, similarity, controlled change measurement and model-backend release remain gated by the inputs listed in the [action plan](../remaining-work-action-plan-2026-10-10.md).

## Independent review and corrections

Fresh-context GPT-6-astra with high reasoning reviewed the final feature diff and ran 38 focused tests. Verdict: with fixes, two Important findings, no confirmed Critical or Minor finding. One correction pass reproduced three failing complete-launcher regressions, then passed all 41 focused tests:

- Malformed claim status types and a malformed Claude response envelope now fail as branch-local unavailable results. Remaining specialists, author/reviewer and the original observations survive. Controlled native executables reproduce both failures through the actual launcher.
- Retained report bodies are limited to 128,000 UTF-8 JSON bytes each. Nine distinct roles plus author/reviewer therefore retain at most 1,408,000 report bytes. A complete-launcher case returning eight individually valid 1.1 MB specialist reports previously lost the output; it now records unavailable oversized branches and writes all original observations. No factual truncation replaces the rejected report.

The reviewer declined to judge semantic SEO accuracy, authenticated acquisition and the parent's native-host results; they were not independently rerun. It retained the explicitly documented child disk-write limitation and the absence of guaranteed synthesis/review slots across processes. These remain evidence limits, not successes. No second independent review pass was requested.

Both real-host artifacts from the earlier native runs were replayed through the final reference validator and satisfy the final per-report byte limit. They are not claimed as new native executions after the correction. The model launch flags and role contracts were unchanged.

After the correction pass, the full Python suite passed **2,013 tests**. The complete site verification passed, including translations, Astro check/build, distribution checks and **113 browser tests**, without screenshot updates.

Wheel and source archives built at the unchanged version 1.5.0 and passed Twine checks. A Python 3.13 installed-wheel check outside the checkout retained 96 tools, imported all nine packaged profiles and exercised the role/budget pipeline against a controlled model boundary: 3 reservations, 2 cached-source tool calls, 0 provider attempts, unknown indexing preserved. This packaging check is not an actual model invocation. No distribution was uploaded to PyPI. Delivery identifiers follow after verification.
