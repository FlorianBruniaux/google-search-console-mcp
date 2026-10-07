# Real run: Claude Code Ultimate Guide

Run date: **2026-10-07**. Site: [cc.bruniaux.com](https://cc.bruniaux.com/). Source: 14 live Search Console MCP calls from Codex, Google search data and three public-page audits. This is an analysis snapshot. No site changes were applied and no ranking gain was measured.

[Download the shareable request/response trace](evidence/2026-10-07-cc-guide.json). It contains reviewed excerpts with timestamps, durations, parameters and the results discussed below. Account permissions, connection configuration, internal metadata and unrelated queries are omitted. Full original responses stay private and are not shipped with the website. These Search Console metrics are deliberately shared for this example; they are not public Google data.

## 1. What the analysis measured

The site received **459 clicks**, a **0.82% click-through rate** and an **average position of 7.3** from September 7 to October 4. Compared with August 10 to September 6, clicks rose **11.95%** and impressions rose **48.21%**. Visibility grew faster than clicks; this is not a traffic-drop example.

| Google web search | Aug 10–Sep 6 | Sep 7–Oct 4 |
| --- | ---: | ---: |
| Clicks | 410 | 459 |
| Impressions | 37,731 | 55,921 |
| Click-through rate, calculated from totals | 1.09% | 0.82% |

A click is a visit from a search result. An impression is an appearance in search. Click-through rate is clicks divided by impressions. Average position summarizes many searches; it is not the rank of one keyword. Totals come from dimensionless analytics, independently confirmed with `get_advanced_search_analytics` and `data_state="final"`. Visible query rows cannot reconstruct these totals.

## 2. Suggested actions

| Priority | Observed signal | Proposed action | Scope | What to measure |
| --- | --- | --- | --- | --- |
| P1 | `/releases/`: 19 clicks for 12,693 impressions; two visible latest-version queries have 936 impressions and no clicks | Inspect the actual search snippets by query, country and device, then test one snippet change if the observed intent supports it | One page and one test | Clicks and CTR for those queries, with impressions and position as context |
| P2 | `/guide/third-party-tools/`: 9 clicks for 7,106 impressions; searches include RTK / lean-ctx comparisons | Make the existing comparison easy to find: give it a descriptive heading and a table-of-contents entry | One existing content block | Page clicks and comparison-query CTR, with the small query sample noted |
| P2 | The same page exposes many navigation-only link targets | Review relevant contextual links, keeping existing body links and destination aliases in mind | One page's links | Actual links in the content and subsequent destination-page search metrics |

These are assistant recommendations based on the evidence. They have not been tested on the site. The `quick_wins` benchmark ranks candidates; its calculated click scores are not a forecast of recovered visits.

## 3. From tool results to a recommendation

### Find the pages that need attention

`get_performance_overview` and `compare_search_periods` establish the two equal 28-day windows. `get_search_analytics` returns page metrics; `quick_wins` puts the releases, third-party tools and architecture pages among the first candidates to investigate.

| Page | Clicks | Impressions | CTR | Average position |
| --- | ---: | ---: | ---: | ---: |
| [Releases](https://cc.bruniaux.com/releases/) | 19 | 12,693 | 0.15% | 7.2 |
| [Third-party tools](https://cc.bruniaux.com/guide/third-party-tools/) | 9 | 7,106 | 0.13% | 6.8 |
| [Architecture](https://cc.bruniaux.com/guide/architecture/) | 8 | 5,231 | 0.15% | 6.2 |

### Check intent and the page before suggesting a rewrite

`get_search_by_page_query` finds 485 impressions and no clicks for “latest claude code version” on `/releases/`, plus 451 impressions and no clicks for “claude code latest version”. The technical audit finds a title already matching that intent, a description, a self-canonical URL and no robots.txt block. Reading the public page also confirms that the latest release is explained near the top. The next step is a focused snippet investigation; a missing title or missing version summary was not found.

On the tools page, two visible RTK / lean-ctx comparison queries have 27 impressions and no clicks. Reading the page confirms that the comparison already exists inside the lean-ctx section. The suggestion is to make that existing answer easier to locate. This query sample is too small to promise a gain.

### Review the automated alerts

`heading_audit` reports one H1 and no hierarchy jumps on both guide pages. The tools page has 74 headings, although the tool also raises a low-severity words-per-H2 warning. Review the existing subheadings before adding more.

`internal_links_audit` finds 47 body links and 106 destinations reached only through structural zones on the tools page. That does not establish 106 orphaned pages across the site. The technical audits also flag three missing security headers per page. Those are hardening findings; this run does not establish them as ranking causes. No critical HTML issue was returned for the three audited pages.

## 4. What this run leaves unverified

GA4 engagement and conversions, Bing performance, field Core Web Vitals, competitors, backlinks and Google indexing status were not measured. No URL Inspection call was made. HTTP 200 and an accessible robots.txt do not prove indexation. Only three pages received technical audits.

The trace records that `row_limit` did not cap two returned row sets: 354 page rows and 1,399 page/query rows were returned. The public trace retains the three pages and only the four queries discussed in this case. Full heading and link lists, private-log hashes and repository details are also omitted. The website build accepts only this reviewed snapshot; changing it requires another privacy review. MCP package version is `UNKNOWN`; 81 available tools were observed. The listed calls are MCP-level excerpts, not an HTTP packet capture or an internal server log.

After a chosen change, collect another equal 28-day window and compare the affected page and queries. Keep the search mix and other changes visible; a before/after difference alone does not prove causality. To repeat this analysis, use the [quick-audit workflow](quick-audit.md) and the tool parameters in the trace.

Next action: inspect the search snippets for the two latest-version queries before choosing a single `/releases/` change.
