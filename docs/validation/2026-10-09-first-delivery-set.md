# First audit evidence delivery set, 2026-10-09

Starting main: `a4b26364346ce2215e07a34963319303ed04334e`. Work was isolated in a managed worktree; the original checkout and its unrelated untracked files were preserved. Changes remain unreleased. The source catalogue contains 89 tools; published 1.3.1 retains 85.

## Delivered slices

| Unit | Issue | Implemented behavior | Remaining boundary |
| --- | --- | --- | --- |
| U00 | CI prerequisite | Owner-only PR checks, full Python suite, distributions and installed-wheel CLI smoke | Remote execution and branch protection are separate checks |
| U01 | #37 | Generic Web appearance discovery uses one valid dimension; AI exposure stays unavailable/unverified | No live AI-specific provider mapping or causal exposure comparison |
| U02 | #38 | Traffic and cannibalization playbooks use supported arguments and preserve missing evidence | Other playbooks, native routing, dual-host projections and BM25 checks remain |
| U03 | #40 | Search-breakdown finding identities, source references, snapshot fingerprint and optional full-envelope UTF-8 budget | One report pilot; no durable snapshot, detail retrieval or global report budget |
| U05 | #46 | Disjoint equal-length same-weekday reference, Pacific J-3 policy and explicit coverage gates | No annual reference, incident feed or causal seasonal diagnosis |
| U06 | #42 | Bounded caller-supplied SiteOne JSON preview with provenance, omissions and credential-URL rejection | Exporter-shaped fixtures only; no real export replay, persistence, shared import store or GSC join |
| U04 | #39 | Bounded agent scheduling, nullable page observations and source-plus-draft review | Controlled host only; native runtime, model quality, provider-wide budgets and Codex parity unknown |
| E01 | #6 | Written audit-evaluation protocol, case packet and independent-label requirements | No authorized human-labelled corpus, frozen thresholds or executed human/model evaluation |

These slices do not close the parent issues. Later content extraction, index reconciliation, log import, crawl diff and bulk-export work remains outside this set.

## Executed integrated validation

| Check | Observed result |
| --- | --- |
| Full Python suite in isolated declared-dependency environment | 1782 passed, no skips or failures |
| Controlled Node workflow scenarios, included in the suite | 12 passed; actual workflow source, simulated agent responses |
| Wheel and sdist build, `twine check` | Both distributions built and passed metadata checks |
| Wheel installed outside the checkout | CLI discovery and actual FastMCP discovery agree on 89 tools; empty import preview and optional byte-budget CLI flag passed |
| Action workflow syntax | `actionlint` passed; final workflow explicitly installs Node 22 |
| Site source tests | 5 passed |
| French translation freshness | 44 paired documentation pages prepared; source hashes current |
| Astro check | 32 files, 0 errors, warnings or hints |
| Site build | 47 pages built |
| Generated-page checks | 23 passed |
| Browser behavior and accessibility | 70 passed using an isolated preview port |
| Whitespace validation | `git diff --check` passed |

Site image-baseline comparisons were excluded from the browser run. Existing screenshot baselines were preserved; no pixel-equivalence claim is made. The site and distributions were built locally, without publication. The wheel retains the repository's current 1.3.1 version for local validation; it is not a new PyPI release.

The isolated environment uses declared pip dependencies. `uv` was absent from this execution PATH, so a frozen `uv.lock` installation was not verified. Baseline dependency diagnostics are in [CI validation](2026-10-09-ci-baseline.md).

## Independent review and regressions

A separate reviewer examined the implemented contracts and exercised real CLI subprocesses. Two confirmed integration defects were corrected before completion:

- Budgeted CLI output was reserialized with ASCII escaping, changing its UTF-8 byte count. The CLI now preserves the budgeted raw JSON envelope including metadata. The regression covers Unicode with and without `--meta`.
- Crawl errors/notices could echo credential-bearing URLs that row validation rejected. The adapter now applies the same bounded HTTP(S) credential/signed-URL boundary to emitted text, rejects sensitive rows/messages with counts and reasons, and retains ordinary data. Independent probes also reproduced and checked apostrophe userinfo and signed AWS URLs. This is a known-URL-format boundary, not a universal secret scanner.

A real-output test corrected unsupported-field count metadata paths. New message-rejection counts and reasons also have explicit evidence declarations. Tests were run after the final fixes, rather than inferring success from code review.

No remaining blocker was confirmed within the reviewed slices. Tests prove local contracts and supplied-fixture routing; they do not prove live Google/Bing accuracy, expert SEO diagnosis, native agent operation, semantic review quality or ranking improvement.

Related records: [playbook contract](2026-10-09-playbook-contract.md), [agent review](2026-10-09-agent-review.md), [human evaluation protocol](../classifier-evaluation.md#audit-evidence-tracks-preparation-for-6).
