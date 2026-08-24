---
name: onpage-audit
description: Complete on-page audit of a single URL in one pass, combining heading
  structure, internal linking, technical meta tags, content quality and schema, then
  cross-checked against real Search Console data before any recommendation is made.
  Use when asked for a full page audit, an all-in-one check, or what to fix on a page.
  Aussi déclenché en français par "audit complet de cette page", "tout ce qui cloche
  sur cette page", "qu'est-ce que je corrige sur cette URL", "audit on-page",
  "passe cette page au peigne fin", "check complet", "audit tout-en-un".
---

# On-Page Audit

One URL in, one prioritized fix list out. Five tools, no auth beyond GSC, no quota
burned on the page-level checks.

## Input

A page URL. The GSC property is resolved with `list_properties` when the user has
not named it.

## Steps

Run the five page-level tools. None of them needs Google credentials, so they run
even when the property is not configured yet.

1. `heading_audit`: H1 uniqueness, level jumps, title vs H1, empty headings
2. `internal_links_audit`: link placement by zone, footer-only targets, anchors
3. `page_technical_audit`: title and description length, canonical, robots, viewport
4. `content_quality`: thin content, filler, information density, repetition
5. `schema_validate`: structured data present and valid

Then pull the ground truth, which is what turns findings into priorities:

6. `content_brief`: the queries this page already ranks for, and its GA4 engagement
7. `crux_page_vitals`: real-user Core Web Vitals, when the page has enough field data

## The rule that overrides every finding

**No destructive recommendation without the data behind it.**

Before proposing to delete a page, noindex it, consolidate it into another, or strip
content, read its clicks, impressions and indexing status over 90 days. A page that
looks thin and generic next to a long article can still be indexed and bringing in
traffic. Off-the-shelf SEO tools get this wrong routinely and recommend deleting
whole sets of working local pages.

If the data says the page performs, the finding is downgraded to an observation and
labelled as such. Say so out loud in the report rather than dropping it silently.

Same discipline on severity. A red flag on a page with no impressions is not urgent.
A low-severity finding on the page that carries the most clicks probably is.

## Output format

**Verdict**: one line, what state the page is in.

**Where it stands today**: clicks, impressions, average position, top three queries.
This section comes first because it sets the weight of everything after it.

**Findings**, grouped by tool, each with its severity as returned. Do not invent
severities and do not reorder them by feel.

**Fix list**, and this is the part that matters:

| # | Fix | Where | Impact | Effort |
|---|---|---|---|---|

Sorted by impact against the actual traffic of the page. Each row names the exact
element to change and the value to change it to. A row that says "optimize the title"
is not a row; "rewrite the title as X because the page ranks 12th on query Y" is.

**Observations kept aside**: findings the GSC data contradicted, with the number that
contradicted them.

## What this skill does not do

It does not touch the site. It does not call `submit_url`, `submit_batch`,
`indexnow_submit` or `sitemaps_delete`. Those are write tools and they follow the
confirmation protocol in CLAUDE.md, separately and explicitly.
