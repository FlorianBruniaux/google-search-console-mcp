# HTML command fidelity: local correction candidate

Date: 17 October 2026. Scope: the extraction defect identified in the existing `docs/validation/2026-10-15-cc95-reconciliation-comparison.md`, read from the principal checkout without modifying that document or its private evidence.

## Subsequent combined validation

The separate runtime-recovery lot and this final extraction lot were subsequently applied to the exact same baseline and validated together: **2,247 tests passed, one skipped** in one complete suite. The [combined integration record](2026-10-17-native-extraction-integration.md) supersedes the incomplete broad-suite qualification below for this combined candidate. The earlier failure and interrupted run remain retained; neither is relabeled as a pass. No extraction implementation changed during combined validation.

## Integration closure and source baseline

The local `origin/main` reference is `6aa558484687f95143df9ba2a7f0c11cb8ee7ed3`. Its history contains merge `895436c` for PR #115, plus the original SerpApi commits `09aaab1`, `e343ea4`, live-pilot validation `b5c25f5` and CI policy correction `efaa780`. The prior integration lot is therefore present in this local mainline history. No remote status refresh, provider acquisition or account request was needed for this diagnosis. Issue #95 still covers provider comparison and independent human quality evaluation; the integration alone does not satisfy that work.

Candidate branch: `codex/html-command-fidelity`. Checkout: `/Users/florianbruniaux/.codex/worktrees/html-command-fidelity/google-search-console-mcp`, created from the local `origin/main` reference above. The branch was clean before the new test file. The principal checkout and all concurrent work remain outside this candidate's edits. No commit, push, PR, merge, deployment, package publication, secret edit or SerpApi ledger edit was performed.

## Reproduction and root cause

The retained public Quick Start HTML is `public-pages/page-02.html` under the existing private evaluation store. Its SHA-256 is `6bf74a4304b3689aa6a13620669968f0d8373c73ab896db696a13f678d043100`, size 366346 bytes. All eight HTML snapshot hashes matched the existing source register. These files were read only; no page was fetched again and no private GSC metrics were read.

On the baseline parser, concatenated `<pre>` text contains both `npm install -g @anthropic-ai/claude-code` and `irm https://claude.ai/install.ps1 | iex`, while the `visible` extraction lacks those exact strings. `claude --version` was already preserved. The parser strips every data fragment and joins fragments with spaces. Syntax-highlighting spans split package paths, URLs and options into fragments, so this behavior changes command tokens. It also flattens literal line breaks.

This is one extraction defect reproduced on one stored public page. It is not six independent site defects, a command-safety assessment or evidence that a provider response is wrong. No extracted command was executed.

## Minimal correction

- `src/gsc_mcp/tools/content.py`: keep fragments within `<pre>`/`<code>` in one literal group, preserving source spaces, tabs and newlines. Preserve each explicit `<br>`/`<br/>` as one newline, including repeated breaks. Treat the `<div>` line containers used by highlighted code as line boundaries. Continue excluding the existing skipped tags and keeping the existing prose separation outside code.
- `src/gsc_mcp/content_extraction.py`: report the changed visible profile as `stdlib-htmlparser-v2`. Remove the stale comment promising unchanged output; content-quality documentation now describes literal code spacing rather than identical scores.
- `tests/test_code_text_extraction.py`: eleven synthetic cases cover package/URL/option tokens, inline code, nested pre/code, literal whitespace/entities, highlighted line containers, `<br>`, skipped content, incremental unclosed input and empty-code status. No live page body, real account data or credential is copied into a fixture.

The change uses the existing standard-library parser and adds no dependency. Literal groups are joined once rather than repeatedly concatenating a growing command string. Extraction remains heuristic text extraction, not browser rendering or an authenticated execution source. Empty `<div>` containers remain boundary-only: `<pre><div>a</div><div></div><div>b</div></pre>` yields `a\nb\n`, without preserving the empty visual row. This limitation is deliberate for this minimal candidate; div layout and nesting need a separate contract before promising rendered blank-row fidelity. In contrast, consecutive explicit `<br>` elements are not deduplicated. Other HTML/CSS line layouts and optional extraction profiles are outside the added fidelity guarantee.

## Verification

| Check | Result |
|---|---|
| Existing extraction, evaluation and content tests before the fix | 80 passed, 1 skipped |
| New synthetic cases against baseline | 7 failed for the expected token/whitespace/line-break defects, 2 passed |
| Initial cases plus affected existing suites after the first correction | 89 passed, 1 skipped |
| Review delta: consecutive `<br>` and `<br/>` against the first candidate | 2 expected failures |
| Final cases plus affected existing suites after the review delta | 91 passed, 1 skipped |
| Full Python suite | Not green: first complete run 2228 passed, 1 failed, 1 skipped; frozen-code rerun interrupted after 399 passed (details below) |
| Stored Quick Start HTML, original symptom | Both previously corrupted commands now occur exactly; `claude --version` remains present |
| Retained HTML evidence | All eight source hashes verified; original evidence not rewritten |
| Diff whitespace and patch applicability to the recorded baseline | Passed; patch check and application against the recorded baseline reproduce every candidate file exactly |

An initial complete run started before the final `<br>` delta finished with 2228 passed, 1 failed, 1 skipped. The failure was `tests/test_native_output_limits.py::test_timeout_kills_descendant_and_reaps_direct_child`: `parent.pid` was absent when read after the child launcher timed out. That test exercises `native_process.run_bounded` with a 0.3-second timeout and does not use HTML extraction. Neither its implementation nor its test was changed in this candidate. This run is not presented as a green or coherent final-candidate qualification. The subsequent frozen-code broad rerun was stopped by the assistant after 399 passing tests, before completion; the coordinator instruction to finish that running execution arrived after this interruption. No third complete rerun was launched. Thus there is no completed full-suite verdict for the final frozen candidate. The final affected-suite result of 91 passed and 1 skipped is complete. The coordinator separately reports that the same parent.pid failure was reproduced before modifications by the session owning native-runtime issue #39; that runtime correction remains in its separate candidate and was not copied into this branch.

Tests use the principal project's existing Python environment with this isolated checkout's `src` on `PYTHONPATH`; no dependency installation was required. The targeted suite's optional trafilatura case is skipped because that extra is unavailable. No live network or provider behavior is inferred from these synthetic tests. Site/browser builds and remote CI were not run for this local runtime candidate.

## Evaluation boundaries and handoff

Visible extraction text, token counts and derived heuristic scores may change on pages containing code. Newly extracted evidence must retain profile version v2 and its own hashes. Historical v1 page extractions, offsets, input packets and reports were not regenerated or silently replaced. A rerun of the evaluation would need a separately versioned dataset and review of any changed excerpts or offsets.

The unresolved provider acquisition and blocked SerpApi ledger remain untouched. No historical search was replayed and no new supplier acquisition was attempted. Independent human relevance annotations, paired diagnostic review and a matched-context supplier comparison remain necessary for issue #95. Fixing text fidelity does not measure a diagnostic-quality or SEO gain.

Reviewable local patch: `/private/tmp/serpapi-html-command-fidelity.patch`. The patch includes the two runtime files, synthetic test file and this standalone record. It is intended for local review; publication remains outside this task's authorization.
