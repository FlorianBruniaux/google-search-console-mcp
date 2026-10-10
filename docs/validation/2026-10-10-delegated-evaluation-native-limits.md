# Delegated evaluation and native output limits

## Delivered scope

This lot advances #6, #39 and #41 from source base `baeb5486748aef12275976abb60db9e8aa98f9d7`. Those issues retain their human-corpus, authenticated-provider and adoption criteria.

- #39: stdout/stderr are counted during execution, each capped at 2,000,000 bytes. Stdout is retained in bounded memory and stderr discarded; no disk log is created. An isolated launcher installs a hard per-file `RLIMIT_FSIZE` ceiling before exec, preserving any lower inherited soft or hard limit. Overflow and timeout stop the ordinary process group, reap the direct child and retain observations and reserved attempts.
- #6: query and pair annotations with equal declared annotator/reviewer identifiers are rejected. The intake worksheet separates supported evaluator interfaces, missing human inputs and unsupported task metrics. Different identifiers do not authenticate independent humans.
- #41: a bounded local manifest runner compares both existing extraction profiles against independently declared inclusion/omission snippets. It records source hashes, partial/unavailable results, labeled snippet metrics and scoped resource observations. A supplied synthetic smoke corpus exercises the interface; it cannot approve extractor quality or a default change.

## Verification

The final combined Python suite passed **2,048 tests** under Python 3.11.15 with the optional content package installed. Four evaluator regressions failed before the self-review guard; native regressions reproduced excessive stderr acceptance and an incorrectly raised inherited soft file limit before correction. The new extraction tests failed before the runner existed, then passed with its implementation.

```sh
python -m pytest -q -p no:cacheprovider
```

Wheel and source distributions built successfully, and both passed `twine check`. The new wheel was installed into a separate Python 3.13.13 environment outside the checkout. Its installed `gsc_mcp.native_process` launcher successfully parsed both controlled local host envelopes through real subprocess execution. These were harmless local Python executables, not actual Claude/Codex invocations. Provider attempts were zero. This local build is not a PyPI release.

The extraction smoke used actual Trafilatura 2.3.1. Both profiles returned the inclusion snippets; the controlled template snippet was included by the visible profile and omitted by the optional profile. These fixture observations do not estimate expert FR/EN quality. Resource fields measure one wall-time observation and traced Python allocation peaks, excluding total RSS and untracked native allocations. Downstream content-quality warnings remain `not_measured`.

The independent integration reviewer inspected 13 source/test/documentation/fixture files, ran 85 targeted tests and reproduced the extraction smoke. No Critical or Important findings remained; its minor inclusion-snippet wording correction is included. The frozen bundle, canonical compact JSON of sorted paths to SHA-256 values, is:

```text
6c6efd82b3a811ebb29b216996fc6d957957ad01434595ad1b569ebfea97953b
```

Local verification records: `/private/tmp/gsc-delegated-final-python.log`, `/private/tmp/gsc-delegated-wheel-check.json` and `/private/tmp/gsc-delegated-review-freeze.json`. The plan and this record are outside that 13-file reviewed bundle. Remote CI and deployment must be assessed separately at the published commit.

## Remaining proof boundaries

Native process tests executed on macOS. The implementation supports Linux/macOS and explicitly refuses other native platforms. The file limit applies to every regular file the host writes, including host state, and may make a host unavailable. It is not an aggregate disk quota, a host memory ceiling, or a hostile-code sandbox. Deliberately detached process groups are outside descendant-cleanup guarantees.

No authenticated GSC/Bing/GA4 acquisition, interactive playbook validation, expert semantic-quality judgment or real human corpus was performed by this lot. The report/annotation declarations cannot establish consent, independence or actual pre-tuning chronology. Extraction scores cover labeled snippets, not whole-content recall or precision. The existing default profile and public tool registry remain unchanged. Site behavior was not locally re-tested by this lot; the Python and package checks do not establish browser behavior or public deployment.
