# HTML command fidelity: local correction candidate

Date: 17 October 2026. Scope: the extraction defect identified in the existing `docs/validation/2026-10-15-cc95-reconciliation-comparison.md`, read from the principal checkout without modifying that document or its private evidence.

## Subsequent combined validation

The separate runtime-recovery lot and this final extraction lot were subsequently applied to the exact same baseline and validated together: **2,247 tests passed, one skipped** in one complete suite. The [combined integration record](2026-10-17-native-extraction-integration.md) qualifies the combined candidate. The individual extraction-only run below independently completed with **2,231 tests passed, one skipped** on its recorded baseline; these counts describe different source cohorts. The earlier failure and interrupted run remain historical evidence. No extraction implementation changed during combined validation.

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
| Completed full Python suite on frozen final candidate | 2231 passed, 1 skipped, 0 failures/errors; exit code 0 |
| Stored Quick Start HTML, original symptom | Both previously corrupted commands now occur exactly; `claude --version` remains present |
| Retained HTML evidence | All eight source hashes verified; original evidence not rewritten |
| Diff whitespace and patch applicability to the recorded baseline | Passed; patch check and application against the recorded baseline reproduce every candidate file exactly |

## Completed frozen-candidate validation, 17 October 2026

The user-requested complete run finished normally with **2231 passed, 1 skipped, no failures or errors**, exit code 0. The skipped case is `tests/test_content_extraction.py::test_actual_optional_extractor_repeated_and_interleaved_calls`, because the optional trafilatura dependency is not installed. No dependency was installed for this run.

The run used the existing principal-project interpreter, selected this isolated checkout's absolute `src` path through `PYTHONPATH`, and executed `python -m pytest -vv -ra` with JUnit output. Neither provider credentials nor SerpApi acquisition enablement were passed from the shell into the test environment. No source, fixture or configuration file was edited while pytest was running.

Before/after SHA-256 manifests cover 456 tracked or candidate input files. Both manifest digests are `1bc34e37fa7549ac01611202e2ae20f51bf036265163e1f2269b32fa82dd6fd8`; HEAD remains `6aa558484687f95143df9ba2a7f0c11cb8ee7ed3`, and no input changed during the run. All six tracked native-runtime/native-test files are identical to HEAD. This report was updated only after completion; runtime code and tests retain their tested bytes.

Local evidence directory: `/private/tmp/seo95-frozen-full-64kroubs/`. It retains `pytest.log`, `junit.xml`, `before.json`, `after.json` and `result.json`. These are local verification artifacts, not remote CI or a deployment qualification.

## Historical native-runtime failure, not reproduced in the completed run

The earlier complete run, started before the final `<br>` delta, returned 2228 passed, 1 failed, 1 skipped. Its failure was `tests/test_native_output_limits.py::test_timeout_kills_descendant_and_reaps_direct_child`: `parent.pid` did not exist when read after a child-launch timeout of 0.3 seconds. The later broad rerun was interrupted after 399 passing tests and is retained as partial evidence only.

The completed frozen-candidate run above includes that same native test and records **passed**. The historical failure is therefore not reproduced in this run; this does not establish that its cause was fixed or that it cannot recur. Neither the native implementation nor its tests were changed. The coordinator separately reported a reproduction before modifications in the session owning issue #39; its runtime candidate was not imported into this extraction branch.

Tests use the principal project's existing Python environment with this isolated checkout's `src` on `PYTHONPATH`; no dependency installation was required. The targeted suite's optional trafilatura case is skipped because that extra is unavailable. No live network or provider behavior is inferred from these synthetic tests. Site/browser builds and remote CI were not run for this local runtime candidate.

## Evaluation boundaries and handoff

Visible extraction text, token counts and derived heuristic scores may change on pages containing code. Newly extracted evidence must retain profile version v2 and its own hashes. Historical v1 page extractions, offsets, input packets and reports were not regenerated or silently replaced. A rerun of the evaluation would need a separately versioned dataset and review of any changed excerpts or offsets.

The unresolved provider acquisition and blocked SerpApi ledger remain untouched. No historical search was replayed and no new supplier acquisition was attempted. Independent human relevance annotations, paired diagnostic review and a matched-context supplier comparison remain necessary for issue #95. Fixing text fidelity does not measure a diagnostic-quality or SEO gain.

Reviewable local patch: `/private/tmp/serpapi-html-command-fidelity.patch`. The patch includes the two runtime files, synthetic test file and this standalone record. It is intended for local review; publication remains outside this task's authorization.
