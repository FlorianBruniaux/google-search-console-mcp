# Post-1.5.0 merge recap and release readiness

Date: 2026-10-11. Status: presentation corrected and current source artifacts inspected; no new PyPI publication. Source baseline: `ace96c9628fd3acb04bba2ca7228f0720a98e825`.

The published release remains `gsc-mcp-tools==1.5.0`. Its annotated tag resolves to `24cd2cb39e32ea57e86672d2f2e8519135568697`. The later merge of #72 finalized that release on `main`; it does not add another set of tools. The ten merged PRs below describe subsequent changes. The default registry remains at 96 tools.

## What was merged

| PR | Delivered change | User benefit and evidence limit |
| --- | --- | --- |
| [#73](https://github.com/FlorianBruniaux/google-search-console-mcp/pull/73) | Release-banner checks and site verification in PR CI | Version/date presentation is checked before merge; CI success alone is not deployment proof |
| [#75](https://github.com/FlorianBruniaux/google-search-console-mcp/pull/75) | Compact bilingual navigation aligned with page content, GitHub icon and language flag | Clearer header actions on desktop/mobile; no change to the Python tool catalogue |
| [#76](https://github.com/FlorianBruniaux/google-search-console-mcp/pull/76) | Preserve missing comparison metrics; optional acquisition budgets, native packet reviews and offline evaluators | Missing Google/Bing rows remain unavailable rather than fabricated zeros; prototypes add no public MCP tool |
| [#77](https://github.com/FlorianBruniaux/google-search-console-mcp/pull/77) | Nine source-review profiles, explicit selection, bounded concurrency and persistent native-attempt accounting | Reuse acquired observations across specialist, author and fresh reviewer invocations; model agreement is not human approval |
| [#78](https://github.com/FlorianBruniaux/google-search-console-mcp/pull/78) | Live output/file limits, process-group cleanup, human-evaluation intake and local extraction comparison | Bound retained native output and expose branch failures; human quality and extraction adoption remain unapproved |
| [#79](https://github.com/FlorianBruniaux/google-search-console-mcp/pull/79) | README, architecture and bilingual source-workflow/evaluation documentation | Readers can distinguish published tools from source prototypes and find their setup instructions |
| [#80](https://github.com/FlorianBruniaux/google-search-console-mcp/pull/80) | Google-only scope, noninteractive authentication, output preflight, indexing-state and native-reference corrections | Run a selected Google property without a dummy Bing site; unknown inspections and unavailable sources remain explicit |
| [#81](https://github.com/FlorianBruniaux/google-search-console-mcp/pull/81) | Native client playbook trials and traffic/appearance evidence clarifications | Retain requested versus observed dates and compatible appearance coverage; initial traffic C1 still failed in that batch |
| [#82](https://github.com/FlorianBruniaux/google-search-console-mcp/pull/82) | Missing-count branch before traffic causal ranking | Eight retained controlled cells pass the frozen C1 criteria, including a positive arithmetic control; whole-report quality remains unverified |
| [#83](https://github.com/FlorianBruniaux/google-search-console-mcp/pull/83) | Source installation, client/skill distinctions and updated FR/EN validation links | Users know which executable to configure and which workflows still require the checkout |

The [authenticated pilot record](2026-10-10-live-gsc-readiness.md) describes actual Google acquisition and private native source reviews, including partial coverage and a provider-budget limit. The [interactive trials](2026-10-10-interactive-playbook-trials.md) and [C1 follow-up](2026-10-11-claude-c1-followup.md) use separate controlled MCP replay. No private queries, traffic rows or URL-inspection observations are included in this recap.

## Presentation corrections

The previous README badge displayed 1,782 tests and the infographic displayed 81 tools. The updated badge points to the dated 2,081-test dev/content record; that count is not a promise about base-only installations or future runs. The corrected [infographic](../assets/gsc-mcp-workflow-96.png) changes the counter to 96. Its [generation prompt](../assets/gsc-mcp-workflow-96.prompt.md) records the exact requested edit; the prior asset remains intact.

The GitHub description was updated and reread: “96 MCP tools for Google Search Console, Bing, GA4 and CrUX: SEO audits, traffic diagnostics, local crawl evidence, guarded submissions, Claude/Codex playbooks and opt-in bounded native workflows.” The homepage URL and topics were preserved. These GitHub source capabilities do not establish that every workflow is installed by the currently published wheel.

## Package and publication boundaries

A minor release `1.6.0` is recommended because the range adds optional runtime modules and APIs alongside correctness fixes. There is no additional default MCP tool or dependency in this range. Version 1.5.0 cannot be overwritten with the updated artifact.

The actual wheel downloaded from PyPI was verified against its published SHA-256, `2eeb0e75fe9a4bd4c702687801d98a88d9261208cdc5c6c0e354ec36443bdba8`. It lacks all five new modules listed below, and its `search_compare.py` differs from the current source implementation. This confirms a package-content gap independently of GitHub merge history.

The wheel build packages `src/gsc_mcp`, including the acquisition runtime and native review modules. The repository runner and offline evaluation entry scripts live in `scripts/`; they are not new installed console commands. Workspace skills in `.agents/skills/` and their Claude projections also require the checkout. A release must preserve that distinction in installation instructions, rather than advertise a complete native audit from the Python package alone.

Before publication, inspect the built wheel and source archive, install the wheel outside the repository, verify its 96-tool discovery and run controlled budget/reference checks. Freeze the release commit and notes, update version-dependent installation/site wording, pass exact-commit CI, then publish a new tag through the existing trusted-publishing workflow. A prepared artifact or successful local build does not prove PyPI publication.

## Existing evidence and remaining gates

The current presentation/source snapshot passes a fresh dev/content suite of 2,081 Python tests and complete site verification, including 113 local browser tests. Wheel and source-archive metadata checks pass. Those local artifacts still carry the unchanged 1.5.0 metadata and were not uploaded; they are inspected snapshots, not replacement releases.

The wheel contains `audit_runtime.py`, `native_audit.py`, `native_roles.py`, `native_process.py` and `query_rules.py`, with only the existing three console commands. It excludes repository scripts and workspace skills; the source archive contains `scripts/run_bounded_audit.py`, `scripts/eval_audit_reports.py` and the canonical traffic playbook. A clean wheel installation outside the checkout discovers 96 tools and imports all nine native profiles. Controlled checks preserve missing comparison metrics, reuse one cached local matrix result across two tool calls, refuse a third call at the tool cap, preserve the native reservation cap across sessions and reject temporary `role_scope` references. The one native reservation is synthetic: no model was launched and no provider request was dispatched. These checks establish installed behavior at those boundaries, not semantic report quality.

The exact #83 source commit `5dec91336f1e9ddadb33b8fe06321ebb85391819` passed [manual CI](https://github.com/FlorianBruniaux/google-search-console-mcp/actions/runs/38091960706): 2,081 Python tests, distribution/installed-wheel checks and 97 CI browser tests; 16 local visual cases were skipped in CI. The local complete site run passed 113 browser tests. These are historical records for that commit, not checks of a future release candidate.

The [website deployment](https://github.com/FlorianBruniaux/google-search-console-mcp/actions/runs/38092231882) succeeded on merge commit `ace96c9628fd3acb04bba2ca7228f0720a98e825`; public deployment metadata reports that SHA and run ID. Eight public routes were verified for expected FR/EN home, installation, bounded-audit and changelog content. Automatic workflows failed before jobs started; the recorded successful CI and deployment were dispatched manually.

[#39](https://github.com/FlorianBruniaux/google-search-console-mcp/issues/39) stays open for semantic accuracy of next checks, real MCP errors/retries, Bing device refusal, implicit routing/human dialogue and the ancillary HTML/CrUX scope decision. [#6](https://github.com/FlorianBruniaux/google-search-console-mcp/issues/6) supplies independent expert-quality annotations; [#41](https://github.com/FlorianBruniaux/google-search-console-mcp/issues/41) retains extraction adoption gates. The [remaining action plan](../remaining-work-action-plan-2026-10-10.md) records their order and inputs.
