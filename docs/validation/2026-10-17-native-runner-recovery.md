# Native runner recovery candidate, 2026-10-17

Scope: issue #39 runner and response recovery only. Local candidate on
`codex/issue39-runtime-recovery`, based on
`6aa558484687f95143df9ba2a7f0c11cb8ee7ed3`.

## Changes and acceptance

- Reproduced a SQLite/WAL commit larger than the old 2,000,000-byte per-file
  ceiling. Codex now requests a separate 16,000,000-byte regular-file ceiling.
  Stdout, stderr and accepted final output remain bounded by 2,000,000 bytes.
  With the override, the final-file threshold is monitored; transient growth
  can reach the larger kernel ceiling before rejection.
- A saved file or a successful process exit no longer proves a completed Codex
  report. Require consistent thread identity, a started and completed turn,
  no pending work, and a final JSON assistant message. Reject later tool work,
  post-completion items and mismatching saved output.
- Recover a missing last-message file only from a captured, completed assistant
  message. A pure parser can additionally check the expected resumed thread.
  No automatic retry, native resume launcher or provider acquisition is added.
- Preserve source observations, durable attempt reservations and static failure
  reason codes. Optional diagnostic stderr capture is exclusive, private and
  bounded; default stderr handling still discards content.

## Evidence

The final targeted run passed **70 tests** in **61.08 seconds**:
`/private/tmp/gsc39-targeted-final-20261017.log`.
This includes a real local SQLite/WAL write and normalized CLI event fixtures,
not calls to Claude, Codex models or GSC.

Red runs retained:
- `/private/tmp/gsc39-recovery-red-20261017.log`: ten original regression failures.
- `/private/tmp/gsc39-review-red-20261017.log`: three sequencing regressions,
  subsequently fixed and included in the final targeted run.

The final runtime-only full suite completed after the sequencing correction: **2,236 tests passed, one skipped** in 386.40 seconds. An earlier run passed 2,230 tests with one skipped but used the pre-review code; it remains evidence for that earlier candidate only. Independent final review also passed four sequencing regressions.

The subsequent [combined integration check](2026-10-17-native-extraction-integration.md) passed **2,247 tests with one skipped** after applying this lot and the HTML command-fidelity lot to the same exact baseline. Its code hashes, single-run method and limits are recorded separately.

## Evidence limits and handoff

Historic failures and verdicts remain unchanged. The original private traces
are unavailable in this checkout. In particular, missing reports after the
historic 16 MB workaround remain unexplained. Normalized fixture recovery is
not proof that those historical runs are repaired or that live resume works.
Issue #39 remains open; human evaluation #6 and semantic quality are outside
this candidate.

No external native tests, new provider requests, secret changes, issue edits,
push, merge, deployment or package publication were performed for this candidate.
This record describes the original local candidate. The combined PR preparation preserves its code and updates validation documentation. Local checks do not qualify a live native recovery or close #39.
