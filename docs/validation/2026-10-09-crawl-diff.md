# Crawl inventory difference validation, 2026-10-09

`crawl_diff` reads two existing site-owned snapshots, compares exact raw URL inventories and preserves both references plus original row indices. Duplicate raw keys abstain. Known producer version, adapter and configuration compatibility are required for shared-row field comparisons. Selection completeness and authenticated collection order remain unknown. Missing, null and failed-fetch placeholder fields are not compared as measured zero.

Local Python validation passes 1,929 tests. Difference fixtures cover partial inventory absence, changed configuration/version, Unicode/query/fragment identity, duplicate keys, null cache fields, failed fetches, named-field policy uncertainty, missing snapshots, preflight bounds, deterministic order and explicit omissions across 200 rows. These are controlled inventories and SQLite records, not a new live crawler or Google indexing check.

Policies inspect only matched retained unique URL rows and report local field changes, not ranking regression or site-wide health. Canonical, robots, noindex, title, headings, content fingerprint and internal-link fields are explicitly unsupported by the current adapter. Snapshot detail commands can inspect the bounded source inventories; there is no implicit identity map, normalization or mutation.

Repository BM25 passes 252 scenarios across 15 targets on both hosts. Import routing F1 is 1.00; log routing is 0.62 in this expanded corpus. No native agent behavior or expert accuracy is established. Shared import and read-only on-page skills document the difference boundary.

Documentation passes 6 tests, translations pass, Astro has zero diagnostics and builds 61 pages; built-distribution checks pass 29 tests. Chromium/macOS passes 111 browser tests with the inspected source catalogue count of 95. PyPI remains at 1.4.0 until the next release is published.
