# Ready backlog validation, 2026-10-08

Scope: #14, #15, #2, #3 and #8 on `codex/backlog-ready-fixes`, starting from main `02d1cdd42bfe72112b4e864e16b4f7398a8bbb0f`. These are source changes awaiting merge and publication. They do not prove live GA4 behavior or a live SiteGround reproduction.

## Behavior and limits

- #14: concrete equal requested dates, per-source identity, availability and coverage gates. Empty or malformed measurements cannot become measured zeros in the comparison. Explicit zeros remain zero. Calendar alignment and site/property mapping remain explicitly unverified; clicks and sessions are different metrics.
- #15: known SiteGround-style challenge fixtures produce `challenge_page`, null schema measurements and no real-page schema verdict. Ordinary HTTP 202 pages and CAPTCHA discussion fixtures remain normal pages. General challenge detection is outside this scope.
- #2: an audited inventory of 82 registered tools attributes applicable fields through versioned JSON-pointer evidence metadata. Observations, calculations, rules and unavailable evidence are distinct. Structural tripwires do not prove semantic completeness for arbitrary future changes. Unsupported model descriptors are rejected until their required backend/version/calibration contract exists.
- #3: four fetched-page tools retain original audit evidence and mark page content untrusted even when no deterministic FR/EN signal matches. Samples and signals are bounded. External CSS, arbitrary paraphrases and exhaustive prompt-injection detection are outside the claim.
- #8: one compatible GA4 request supplies assistant source rows and the denominator. Exact ChatGPT attribution is confirmed; other candidate domains are separate and excluded from confirmed totals. Unknown coverage or a zero denominator prevents invented shares. These are attributed visits, not observed citations or a guaranteed lower bound on all AI visits.

## Independent review

An independent reviewer inspected a frozen candidate and ran 161 targeted tests. It reproduced two material defects, both corrected with failing regressions before the fixes:

1. Real child parsers converted blank/invalid GA4 sessions and missing aggregate GSC clicks into zeros. Three new provider-boundary regressions failed before correction. Nullable parsing now preserves missing measurements; explicit-zero controls and 278 targeted tests passed.
2. Unspecified inspection enums were unavailable individually but incorrectly supported category evidence. Three single/batch/anomaly regressions failed before correction. The shared unavailable predicate now excludes them while retaining historical category values; 34 evidence tests passed.

Machine-readable tool counts were also corrected to 82 total and eight GA4 tools.

## Validation

| Check | Result | Evidence boundary |
| --- | --- | --- |
| Full Python suite | 1124 passed | Mocked provider boundaries, no live credentials |
| Documentation source tests | 5 passed | Source synchronization |
| French translation verification | Passed, 38 documentation pages | Canonical hashes, not linguistic perfection |
| Astro check | 32 files, zero errors/warnings/hints | Static check |
| Site build | 41 pages built | Local artifact, not deployment |
| Built-site tests | 23 passed | Local build |
| Browser suite | 79 passed | Local Chromium |
| Visual baselines | Nine captures intentionally refreshed | Tool count 81 to 82; regular suite rerun without updates |
| Skill routing, both hosts | Gate passed | Isolated temporary indexes, no global configuration mutation |

Routing fixtures include realistic FR/EN requests and adjacent negatives. Indexing-audit: 18 true positives, three false positives, no false negatives, F1 0.9231. Sitemap-audit: 24 true positives, 12 false positives, one false negative, F1 0.7869. Eligible global F1: 0.7475. Twelve additional route probes passed on each host. These results do not claim perfect classification; existing false positives remain.

## Pending work

Merge, package release, deployment and live provider checks are separate steps. #6 still requires human labels and agreed evaluation thresholds. #4/#5 release stays gated; #7/#9 remain deferred. No labels or runtime evidence were fabricated.
