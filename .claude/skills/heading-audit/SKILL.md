---
name: heading-audit
description: Audit the heading structure of a page. Checks H1 uniqueness, level jumps,
  whether the title duplicates the H1 word for word, headings that carry no information,
  and subheading density. Use when asked about headings, H1, H2, title tags, or page
  structure. Aussi déclenché en français par "mes balises H1", "structure de titres",
  "j'ai deux H1", "hiérarchie des titres", "mon title et mon H1", "balises Hn",
  "est-ce que mes titres sont bons", "audit des balises".
---

# Heading Audit

Headings and internal links are the two levers that move a page without touching
anything else. This audit covers the headings half.

## Input

A page URL.

## Steps

1. Call `heading_audit` on the target URL. No auth needed, no quota consumed.
2. Check `h1_count`. Zero or two and above is the first thing to fix.
3. Read `hierarchy_jumps`. An H2 followed by an H4 breaks the outline.
4. Check `title_h1_identical` and `title_h1_overlap`. A title that repeats the H1
   word for word wastes a free second angle on the target keyword.
5. Read `empty_headings` and `descriptive_ratio`. The test to apply: can someone
   understand the page by reading only its headings?
6. Check `words_per_h2`. Past 400, the page reads as a wall.

## Cross-reference before rewriting a title

Call `content_brief` on the page to get the queries it already ranks for. Rewrite the
title around a query the H1 does not already cover, not around a guess. If the page
has impressions on a question query, that phrasing belongs in an H2.

## Output format

**Verdict**: healthy or issues_found.

**Structure**: H1 count, heading count, words per H2, descriptive ratio.

**Outline as it reads today**: the headings in document order, indented by level.
Then state plainly whether the page is understandable from that outline alone.

**Title vs H1**:
- Current title
- Current H1
- Overlap score
- If identical, propose a rewritten title covering a second angle

**Priority list**:
1. Critical: missing or duplicated H1
2. High: level jumps, no H2 on a long page
3. Medium: headings that carry no information
4. Low: subheading density

Rewrites are proposed as concrete text, not as advice to "improve the heading".
