# SerpApi #95: local preparation validation

Validation on 11 October 2026, source branch `codex/serpapi-free-integration`, based on `712e1baaabb7a9d0450421bf17410d3b99bfdb81`. The initial record covers local implementation and synthetic behavior, not live entitlement, provider quality, CI or deployment. The separate connection follow-up below records the later live account check.

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

## Initial preparation: not acquired or qualified

During the initial preparation, no SerpApi account signup, card, subscription, credit purchase, real account preflight, live SERP acquisition or other supplier fallback occurred. Public producer documentation was reviewed separately. Actual producer costs remain unavailable rather than a fabricated zero. No private GSC observation is included in code, fixtures or this record.

Still needed at that stage: actual free-account response shape; desktop/mobile Google responses; effective France/language/location; provider dates/cache observations; independently annotated diagnostic comparison. DataForSEO live comparison is not performed by these tests and agreement alone would not establish ground truth.

The existing bounded Google/Bing audit budget does not cover SerpApi. Acquisition is refused inside that audit context until a separate integration contract is reviewed. Cross-machine/rotated-key/store changes are outside the local ledger's coordinated ceiling, as described in the [setup guide](../serpapi-comparison.md).

Issue #95 remains open. This local preparation does not close its live comparison/quality acceptance criteria or publish a release.

## Connection follow-up

The user supplied a private local credential. A real read-only account check accepted the active free-plan identity and zero price, but initially refused its higher hourly entitlement. The adapter had incorrectly treated the published 50/hour rate as an upper bound on provider account entitlement. A positive integer provider rate is now accepted independently of the unchanged local 50/hour ceiling; free-plan, price, extra-credit, remaining-quota and counter checks remain in place.

Four synthetic regressions cover higher-rate free-account acceptance, refusal of the 51st local hourly attempt and both single-hour and combined-hour provider exhaustion. Two acceptance tests failed with the original guard before the fix; the exhaustion tests already passed. The first isolated-environment test command lacked pytest, and an offline pytest-asyncio install could not resolve from cache. Tests then used the existing project test environment against this checkout's source.

The existing private Codex server command now points to the isolated checkout's executable. A real stdio MCP session discovered 98 tools, received the environment credential and returned an offline preview with zero network calls. This was a separately launched process; the already running desktop session still needs its MCP reloaded. Neither the key nor account identity was printed or added to source. No live search, subscription, purchase or credit consumption was requested in this follow-up. Account API checks are separate from SERP acquisition and do not qualify desktop/mobile search output or SEO quality.

Follow-up verification: the targeted SerpApi suite passed 89 tests; the complete project Python suite passed 2212 tests with 1 skipped. The corrected adapter's real read-only account preflight passed. A separately launched stdio session using the exact current private Codex configuration passed discovery and credential-bearing offline preview. No search request was sent. Remote CI, package release and desktop-session reload remain unverified.


## Current-session live follow-up, 11 October 2026

Codex session `01a12b90-611c-76d1-a6c5-2105d8049f72` worked only in the isolated `serpapi-free-integration/google-search-console-mcp` checkout. The branch was `codex/serpapi-free-integration`, HEAD `e343ea462b332f193ea966ce6bfd224550ea84ee`, with no tracked or untracked changes at intake. The two SerpApi commits follow base `712e1baaabb7a9d0450421bf17410d3b99bfdb81`. No upstream is configured and no known remote-tracking branch contains HEAD; this observation is not a fresh inventory of every remote ref. The principal checkout's existing modifications were not edited. This follow-up creates no commit, push, PR, merge or release.

### Availability and offline checks

The actual `gsc-mcp` connection loaded in this session answered `get_capabilities`: 98 tools, both `serpapi_search` and `serpapi_import_preview` present, credential declared and acquisition enabled. The configured executable points to this isolated checkout. No reload was needed. `runtime_qualified: false` remains the adapter's experimental release classification; it does not contradict these two live observations.

An actual `serpapi_search` invocation with `acquire=false`, query `tour Eiffel`, `fr`/`fr`, desktop and `fresh=false` returned `preview`, `network_calls=0`, local limits 40 attempts/31 rolling days and 50/hour. Parameters were `engine=google`, `google_domain=google.com`, `start=0`, `async=false`, `no_cache=false`. A synthetic offline import also succeeded through the actual session tool. After capture, offline imports of each retained redacted producer structure returned the same effective parameters, organic items and raw sections, with `delivery=caller_import`, `source_authenticity=unverified` and receipt time null. These imports do not acquire or authenticate new observations. Synthetic regression tests forbid HTTP-client construction for both offline tools, even with acquisition enabled.

### Free-account gate and acquisition allowance

A separate read-only account preflight confirmed `Free Plan`, `Active`, monthly price `0.0`, 250 monthly/remaining searches, no extra credits, hourly entitlement 250 and zero current/last-hour searches. The ledger did not yet exist. The same source guard checks the account before every new search. Desktop preflight reported 250 remaining; mobile preflight reported 249 and one current-hour search. Our local ceilings stayed 40/31 days and 50/hour throughout.

Exactly two new `/search.json` acquisitions were requested through the session's MCP tool, sequentially, using the public query `tour Eiffel`, country `fr`, language `fr`, `fresh=false`, no explicit location and distinct request IDs. Both provider statuses were `Success`; both normalized statuses were `success`. No ambiguous or pending acquisition occurred, and no new ID was used for recovery. Each delivery reported two network calls: one account preflight and one search. A separate account check before the pilot and another after it add two account requests, not SERP acquisitions. No purchase, subscription, recharge, fallback or private GSC query was used.

| Device | Request ID | Provider search ID | Provider created/processed UTC | Receipt UTC | Organic items/positions |
|---|---|---|---|---|---|
| desktop | `seo95-20261011-01a12b90-desktop` | `6acbaa9b7bf2f91297be8354` | 2026-10-11 15:26:19 UTC / 2026-10-11 15:26:19 UTC | 2026-10-11T15:26:20.099892+00:00 | 9: 1, 2, 3, 4, 5, 6, 7, 8, 9 |
| mobile | `seo95-20261011-01a12b90-mobile` | `6acbaaabff7aa2dcff6fb8d6` | 2026-10-11 15:26:35 UTC / 2026-10-11 15:26:35 UTC | 2026-10-11T15:26:36.918821+00:00 | 5: 1, 2, 3, 4, 5 |

The provider timestamps correspond to 17:26:19 and 17:26:35 in Europe/Paris. Source hashes cover the original received response bytes before redaction:

- desktop: `1bca5298074b6f12389448e5e33e5a7f680f73fcfcc40142c75dd77bedd73da8`.
- mobile: `80e5a585f2853b940bd13d172e1d7d7dd388c5875f6368a8bc12137bc79e34c6`.

### Parameters, missing fields and sections

For both responses, effective `engine`, exact query, `gl`, `hl`, device, Google domain and `start=0` matched the request. `missing_context=[]` and `context_mismatches=[]` apply to the adapter's required identity fields. Provider ID, creation/processing dates and every organic item's position, title, link and snippet were present. Positions are producer-reported ranks, not independently checked Google rankings or GSC average positions.

Neither effective parameter object echoes `async` or `no_cache`. Both flags were requested as false; their absence is not converted into a verified effective value. `provider_cache=unknown` and `actual_cost_usd=null` remain correct. No explicit location was requested or echoed, so city-level localization is unverified. A French country/language context does not imply that every returned page or snippet is French: one organic result links to an English page on both devices. Nine desktop and five mobile organic items are the complete delivered lists; the adapter does not pad to ten or fetch additional pages.

Raw top-level section inventory, including producer envelope fields:

- desktop: `ads` (1 items), `inline_images` (9 items), `knowledge_graph` (object), `organic_results` (9 items), `pagination` (object), `related_questions` (4 items), `related_searches` (8 items), `search_information` (object), `search_metadata` (object), `search_parameters` (object), `serpapi_pagination` (object), `short_videos` (10 items).
- mobile: `answer_box_list` (2 items), `filters` (8 items), `knowledge_graph` (object), `organic_results` (5 items), `pagination` (object), `related_questions` (4 items), `related_searches` (10 items), `search_information` (object), `search_metadata` (object), `search_parameters` (object), `serpapi_pagination` (object), `short_videos` (10 items).

Mobile supplied `answer_box_list` and `filters`; desktop supplied `ads` and `inline_images`. Sections omitted from a response are unavailable, not confirmed absent on Google. Feature contents and organic positions survived normalization and offline re-import. Producer pagination, HTML, image, pixel-position and enrichment links were not followed. This pilot captures two different device contexts, not an equivalent-context comparison between providers.

### Replay and retained ledger

Replaying desktop with `seo95-20261011-01a12b90-desktop` and exactly the original parameters returned `delivery=local_replay`, `network_calls=0`, the same provider ID, original creation/receipt dates, source hash, quota-before record and all other observation fields. Only delivery/network counts and invocation metadata changed. The ledger still contains exactly two completed records for this credential, with no unresolved record. Directory permissions are 0700 and database permissions 0600. The private credential's literal bytes were checked absent from the database; no credential, account identity or credential fingerprint is copied into this record or a fixture.

Final read-only free-account guard accepted the account. Its remaining numeric counters were:

```json
{
  "account_rate_limit_per_hour": 250,
  "extra_credits": 0,
  "last_hour_searches": 0,
  "plan_searches_left": 248,
  "searches_per_month": 250,
  "this_hour_searches": 2,
  "total_searches_left": 248
}
```

The remaining-search counter decreased from 250 to 248, consistent with two searches in this pilot. This counter observation is not billing reconciliation and does not establish cache origin. The ledger is retained in the configured private default store; it was not reset, removed or relocated.

### Corrections and automated checks

No functional defect was reproduced in these two live cases or their desktop replay. The documentation's present-tense statements that search output remained unchecked were stale; they now distinguish this limited pilot from general qualification. Runtime implementation, entitlement gates and quota ceilings were not changed.

Four additional synthetic cases cover desktop/mobile shapes with different organic counts and feature sections, unechoed cache/async flags, restart replay with no transport calls, and both offline tools refusing to construct a transport. Fixture query, IDs, URLs and text are synthetic; no real provider body is committed as a test fixture.

| Current follow-up check | Result | Evidence scope |
|---|---|---|
| Provider/tool files before comparison suite | 75 passed | Synthetic transport and local ledger |
| Complete targeted SerpApi suite (three files) | 93 passed | Previous 89 cases plus four new synthetic cases |
| Full Python suite | 2216 passed, 1 skipped | Current macOS/Python 3.13 environment; checkout source via `PYTHONPATH=src` |
| Scoped whitespace check | Passed | Documentation and two test files |

The isolated launcher environment has no pytest; tests used the principal project's existing test interpreter with this isolated checkout's source explicitly selected. No dependency install or global configuration edit was required. The skipped case remains outside the passing coverage. Site/browser/distribution checks were not rerun because this follow-up changed only tests and documentation.

### Acceptance boundaries and human evidence still needed

[Issue #95](https://github.com/FlorianBruniaux/google-search-console-mcp/issues/95) remains open. Two valid deliveries establish functioning acquisition for these two contexts. They do not prove better diagnostics, generally reliable coverage, faster service or that a default provider switch is justified. This session did not qualify remote CI, release/install distribution, explicit location, fresh acquisition, provider cache hits, other queries/languages, live interrupted-request recovery, supplier terms/rights or a DataForSEO comparison. Provider latency metadata is retained but no comparative latency benchmark was run.

Florian still needs to choose a named diagnostic gap and a representative public evaluation corpus, with matched query/location/language/device/time windows and independent human annotations of relevant results, SERP features, missing information and expected diagnostic conclusions. Compare the same diagnostics with and without the new evidence, blinded where practical, against those annotations and predefined quality criteria. Record disagreements and missing coverage; agreement between suppliers alone is not ground truth. No volume, impressions, clicks or business outcome is inferred from these ranks.


## Publication review, 11 October 2026

The publication review checked the full SerpApi branch and the four uncommitted test/documentation changes against refreshed `origin/main` at `712e1baaabb7a9d0450421bf17410d3b99bfdb81`. The two completed private ledger observations were read without network access and matched the report's request IDs, provider IDs, source hashes, device/context and 9/5 organic item counts. No unresolved acquisition was present. The configured credential was checked absent from all 25 changed branch files without printing it. No additional SERP acquisition or account request was made during this review.

The new tests retain synthetic producer structures and exercise real normalization, durable replay and the offline tool boundary. Two remaining outdated descriptions in the README and bilingual site catalogue were corrected to preserve the distinction between the two checked cases and broader provider/diagnostic qualification. Runtime implementation and local ceilings were not changed by the publication commit.

| Publication check | Observed result | Boundary |
|---|---|---|
| SerpApi plus registry/evidence/discovery tests | 151 passed | Includes the 93 synthetic SerpApi cases |
| First and second full Python runs inside the managed sandbox | Each: 2215 passed, 1 failed, 1 skipped | Existing native descendant-timeout test failed before writing its PID marker |
| Native output-limit tests inside the sandbox | 12 passed, 1 failed | Same `test_timeout_kills_descendant_and_reaps_direct_child` failure |
| Native output-limit tests outside the sandbox | 13 passed | Same source, existing 300 ms timeout |
| Complete Python suite outside the sandbox | 2216 passed, 1 skipped | macOS/Python 3.13; no native code/test changes |
| Complete site `pnpm verify` | Passed | 6 source-doc tests, translations, Astro check, build, 29 dist tests, 113 browser/accessibility/visual tests |
| Distributions and metadata | Wheel/sdist built offline; both passed Twine | Local artifacts only, no upload |
| Installed wheel outside checkout | CLI catalogue and real stdio discovery/preview passed | 98 catalogue tools, 5 selected MCP tools, 0 preview network calls; higher free hourly entitlement checked with synthetic transport |

The sandbox timeout failure reproduced with the site checks stopped and disappeared outside the sandbox. These observations establish an environment-dependent result, not a production timing guarantee. The failed runs are retained here; neither the timeout test nor the native runner was changed to make the suite green. Dependency-tool setup initially needed the cached Twine tool and permission to initialize the uv cache; no project environment or global setting was changed.

Issue #95's equivalent-context supplier benchmark, named diagnostic gap, broader coverage, explicit localization, fresh/provider-cache behavior, rights review and independent human diagnostic-quality evaluation remain open. Local checks and retained live observations do not establish remote CI, deployment, release or a default-provider decision. The main checkout's unrelated changes were preserved.
