# Optional extraction validation, 2026-10-09

The default visible-text extractor and scoring rules remain unchanged. An opt-in Trafilatura 2.3 precision profile processes the same safely acquired HTML, with no second fetch or global deduplication. Configuration is copied per call. Decoded HTML hashes, source URL, version, options and acquisition time accompany results. Missing/no-main-text/failed/non-success-HTTP extraction has no placeholder quality scores.

Local validation without the extra passes 1,952 Python tests and skips one real-package integration case. A temporary isolated environment with Trafilatura 2.3.1 passes all nine extraction tests, including actual repeated and interleaved article calls, default-parser compatibility, missing dependency, algorithm exception, no-main-text and HTTP failure. Python CI and the publish workflow now install the extra for their test suite; the isolated wheel smoke installation remains the base package.

Documentation passes 6 tests, translations pass, Astro has zero diagnostics and builds 61 pages, built-distribution checks pass 29 tests, and Chromium/macOS passes 111 browser tests. These checks establish controlled extraction behavior and integration, not real-site recall, expert quality or native agent behavior.

The adapter preserves unavailable results and does not classify a no-text extraction as boilerplate-only. Partial main-content omission is unknown. Human annotations for FR/EN articles, products, services, forums and JS-shell pages, resource measurements and frozen adoption criteria remain outstanding in #6/#41. No default-profile adoption or authorship/indexing/cannibalization inference follows from these synthetic fixtures.
