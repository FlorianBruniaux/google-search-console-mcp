# SerpApi #95: local preparation validation

Validation on 11 October 2026, source branch `codex/serpapi-free-integration`, based on `712e1baaabb7a9d0450421bf17410d3b99bfdb81`. This record covers local implementation and synthetic behavior, not live entitlement, provider quality, CI or deployment.

## Delivered

- Two experimental registered tools: `serpapi_search` and `serpapi_import_preview`, shared with CLI commands and the `serp` discovery family.
- Default offline preview; acquisition requires explicit enablement, a private environment credential and a request identifier.
- Preflight acceptance only for an explicitly active free plan with a zero monthly price, no extra credits and available quotas. Unexpected/missing account fields refuse the search.
- Default 40 attempts per rolling 31 days, hard configuration ceiling 250; default/max 50 per rolling hour. Conservative account checks include other provider consumers visible in the counters.
- Durable private SQLite reservations, replay by exact request identity, no automatic retry after unresolved acquisition, no pagination/enrichment or paid fallback.
- Original query preserved; requested/effective context, producer dates/ID, feature sections, organic positions, raw-response hash and redacted body retained. Missing values remain unavailable.
- Source guide describes private free-account connection and qualification still required.

## Executed checks

| Check | Result | Evidence scope |
|---|---|---|
| Clean baseline Python suite | 2121 passed, 1 skipped | Current macOS/Python 3.13 development environment |
| Test-first new behavior | 68 expected failures after correcting the initial test import path | Missing adapter/tools and undeclared discovery family; no live data |
| Targeted final SerpApi suite | 85 passed | Synthetic HTTP transport, real local SQLite and MCP/CLI behavior |
| Complete final Python suite | 2208 passed, 1 skipped | Includes affected registry, field provenance, generated CLI surface and site metadata tests |
| Distribution build | Wheel and source distribution built offline | Build success, no upload or package release |
| Distribution metadata | Both artifacts passed `twine check` | Packaging metadata only |
| Installed wheel outside checkout | 98 tools; selected MCP discovery and SerpApi preview passed | Final wheel installed in a temporary environment; no source `PYTHONPATH`, no search |
| Site documentation source tests | 6 passed | Explicit route set, privacy guard and content generation |
| Site translations and Astro check | Translation verification passed; 0 diagnostic errors/warnings/hints | Startup content-loader warnings occurred with the initial shared dependency setup |
| Site build and dist tests | Build passed; 29 dist tests passed | Generated source catalogue includes the experimental family |
| Browser behavior/accessibility | 97 passed | Existing English/French interaction and accessibility checks |
| Initial local visual references | 9 failed, 7 passed | Intended 96-to-98 tool-count change, not treated as a green run |
| Local visual references after review | 16 passed | Nine images updated after comparing changed count regions, dimensions unchanged |
| Whitespace checks | `git diff --check` passed | Scoped text changes |

The nine changed screenshot files contain 121–192 differing RGB pixels each under direct pixel comparison. English desktop crops were inspected before the updates; the changed component text comes from the generated tool count. No layout/CSS change was made.

An offline site dependency install under the local pnpm 12.9.1 exited with `ERR_PNPM_IGNORED_BUILDS` for esbuild/sharp lifecycle scripts. The installed cached packages still ran the final local visual check. Global build-approval settings were not changed. The repository CI uses pnpm 9 and Python 3.11; that environment and its remote run have not been verified for this branch. The complete site command was not reported as passing after its initial visual failures: its passing phases and the final visual rerun are listed separately above.

The initial test collection error was corrected before the expected missing-feature failures were verified. Final reinspection added tests for a huge nonzero price, malformed producer dates/IDs and invalid UTF-8 surrogate values; all five reproduced failures passed after correction. Synthetic behavior tests are not independent human SEO evaluation.

## Not acquired or qualified

No SerpApi account signup, card, subscription, credit purchase, real account preflight, live SERP acquisition or other supplier fallback occurred. Public producer documentation was reviewed separately. Actual producer costs remain unavailable rather than a fabricated zero. No private GSC observation is included in code, fixtures or this record.

Still needed: actual free-account response shape; desktop/mobile Google responses; effective France/language/location; provider dates/cache observations; independently annotated diagnostic comparison. DataForSEO live comparison is not performed by these tests and agreement alone would not establish ground truth.

The existing bounded Google/Bing audit budget does not cover SerpApi. Acquisition is refused inside that audit context until a separate integration contract is reviewed. Cross-machine/rotated-key/store changes are outside the local ledger's coordinated ceiling, as described in the [setup guide](../serpapi-comparison.md).

Issue #95 remains open. This local preparation does not close its live comparison/quality acceptance criteria or publish a release.
