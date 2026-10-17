# Native runner and HTML extraction: combined local validation

The two correction candidates pass together: **2,247 tests passed, one skipped** in a single complete Python suite on 17 October 2026. This qualifies their local integration; it does not qualify live native-host recovery, provider behavior or human diagnostic quality.

## Frozen candidate and reproduction

The exact source baseline is `6aa558484687f95143df9ba2a7f0c11cb8ee7ed3`. The runtime patch touches nine files and the extraction patch four, with no shared paths. Both were applied to a separate temporary archive of that baseline. The existing Python 3.13 environment imported `gsc_mcp` from that copy's `src`, verified before execution.

The sole combined full-suite invocation was `python -m pytest -q -p no:cacheprovider`, with that copy as the working directory, its `src` on `PYTHONPATH`, and `PYTHONDONTWRITEBYTECODE=1`. Pytest reported `2247 passed, 1 skipped in 190.22s`. No package installation or additional full-suite run was needed. All 427 frozen regular files retained identical content hashes and permissions afterward, with no added files in the copy. The original patch sources also retained their hashes. The PR checkout's initial content was checked against all 427 hashes; subsequent edits update validation documentation only.

| Retained artifact | SHA-256 |
| --- | --- |
| Runtime patch | `80d5938119f76ed64027159d23a512dc827dd7a95bca13e76e2878428b21dc13` |
| Extraction patch | `a24642fe0d3983633ae18b69bf74485a8172578b2e7789d0d1a7351ec24172cf` |
| Combined patch | `0119ae3a108ab2f43c83733c915b7909d6432bf6acfe6c588033ed2a544741f1` |
| Full-suite log | `d112b01b636d252da388af8f6abe01a6cb591712d16d3cdfe9b3b3f29a6384d3` |
| File manifest, before and after | `0898c31353d94ee080f6759f983cfd48ead5bf3df71dc97fcf7ff4deeb7f5a56` |

The complete log, recoverable patches, manifests and validation receipt are retained privately. No private account observations or historical native traces are included in this record.

## What the evidence establishes

- A local SQLite/WAL write larger than the original 2 MB per-file ceiling completes under the distinct Codex state-file allowance. Stream and accepted-report ceilings remain separate. Captured CLI fixtures require a completed, coherent final response; a file or zero exit alone is insufficient.
- Synthetic HTML fixtures preserve package paths, URLs, options, literal code whitespace and explicit line breaks. The parser profile is versioned as `stdlib-htmlparser-v2`; existing v1 evaluation artifacts are not regenerated.
- The two lots' final code passes the full suite together. Earlier individual-run failures and interrupted runs in the linked records remain historical evidence, not the verdict on this combined candidate.

See the [runtime recovery record](2026-10-17-native-runner-recovery.md) and [HTML fidelity record](2026-10-17-html-command-fidelity.md) for reproductions and scoped limits.

## Remaining issue boundaries

Issue #39 remains open. Missing Codex final reports after the historical 16 MB workaround still have no established cause; these local fixtures do not retroactively repair those trials. Actual same-conversation native recovery, channel disconnect/reconnect, implicit routing with observed playbook reads, remaining semantic failures and real human follow-ups still need their own evidence. Independent expert evaluation remains under #6. This patch adds no live resume driver, automatic retry or new provider acquisition.

HTML extraction is heuristic rather than browser rendering. Empty highlighted `div` rows and layouts outside the documented code-line contract are not guaranteed. Changed v2 excerpts, offsets, counts and heuristic scores require a separately versioned evaluation dataset before comparison with historical v1 reports. Independent relevance annotations and matched-context provider evaluation remain under #95.

No external native invocation, provider acquisition, deployment or package publication was performed for this integration check. Remote CI is a separate gate and is not implied by this local result.
