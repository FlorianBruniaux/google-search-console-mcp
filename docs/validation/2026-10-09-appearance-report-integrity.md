# Appearance and report integrity, 2026-10-09

This follow-up completes the local provider-response and report-pilot contracts from #37/#40. It does not establish live AI exposure, semantic SEO diagnosis or a durable detail store.

Appearance fixtures exercise explicit zero, missing/null/invalid metrics, missing dimensions, malformed response containers, generic empty data, HTTP 400/403 and propagated server failures. Requested site and dates remain visible on failures. Without a dated probe, the observed window is unknown. No appearance spelling, mock or generic metric identifies an AI Overview or estimates lost clicks. The legacy error alias remains available.

Official sources reviewed:
- [Search appearance discovery](https://developers.google.com/webmaster-tools/v1/how-tos/all-your-data#getting_search_appearance_data).
- [Search Analytics request schema](https://developers.google.com/webmaster-tools/v1/searchanalytics/query).
- [AI feature measurement](https://developers.google.com/search/docs/appearance/ai-features#measuring-the-performance-of-your-site).

No verified AI-specific provider identification rule or approved export is available to this implementation. No new import adapter is claimed and no authorized live Google call was made.

Report findings use semantic rule version v2, source options and exact property identity. AND filter order does not alter a finding's identity, while the original scope remains in the report. Identical inputs retain finding/snapshot identifiers. Records distinguish observations from empty fix/hypothesis candidates, missing criteria and verification. The existing byte budget still covers the complete serialized JSON envelope, preserves source failures and accounts for omissions; it either returns an explicit omission error or fails when the minimum envelope cannot fit. It does not silently fetch fresh details or promise stored snapshots.

Validation: the full mocked Python suite passes 1,826 tests. Documentation source checks pass 6 tests and translation hashes match. These are fixture and contract checks, not live provider or native model verification.
