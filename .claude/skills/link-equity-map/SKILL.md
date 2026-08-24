---
name: link-equity-map
description: Map internal link flow across a whole site and cross it with Search Console
  to find the pages sitting on page two that no page body links to. Site-wide companion
  to internal-linking-audit, which works on a single URL. Use when asked about site
  architecture, orphan pages, or where to place internal links. Aussi déclenché en
  français par "maillage de tout mon site", "quelles pages ont besoin de liens",
  "cartographie mes liens internes", "mes pages orphelines sur tout le site",
  "où placer des liens pour gagner des positions", "architecture de mon maillage".
---

# Link Equity Map

Internal linking is worth as much as off-site link building when it is deliberate.
This skill finds where a single link changes a ranking, instead of asking someone to
"improve internal linking".

## Input

A GSC property. Resolve it with `list_properties` when the user has not named one.
Ask how many pages to crawl if the site is large; the default of 25 is a sample, not
a survey.

## Steps

1. Call `link_equity_map` with the site, `days` (90 by default) and `max_pages`.
2. Read `pages_crawled`, `pages_failed` and `coverage_note` **first**, and carry the
   coverage into the report. Everything below is scoped to the pages actually crawled.
3. `underlinked_striking_distance` is the headline. Positions 11 to 20 with no body
   inbound link. Each row is one link away from moving.
4. `orphan_candidates`: pages with impressions and no body link found.
5. `footer_only_targets`: linked from nav, footer or aside only.
6. `hub_pages`: who already distributes. These are the natural source pages.

## Turning findings into placements

A finding without a source page is not actionable. For each target in
`underlinked_striking_distance`:

1. Call `content_brief` on the target to get the query it ranks for.
2. Pick a source among `hub_pages` or among pages ranking for a related query.
3. Propose the anchor text from the target's own query, not from its title.

On a site of several hundred pages, direct links stop scaling. That is when index
pages earn their place: group the targets by theme, link the hub to the index, the
index to the members.

## Coverage honesty

`max_pages` is capped at 100 and the crawl is a sample. Never write "the site has N
orphan pages". Write "N pages have no inbound link among the X pages crawled". The
difference matters when someone acts on the report.

## Output format

**Coverage**: pages crawled, pages failed, share of the GSC set.

**Where a link pays off now**: Target | Position | Impressions | Suggested source | Anchor

Sorted by impressions. This table is the deliverable.

**Orphan candidates**: Path | Impressions | Position

**Footer-only targets**: Path | Zones | Impressions

**Hubs available as sources**: Path | Body links out

**What not to do**: if a page appears with zero impressions and zero inbound links,
say it needs investigation, not deletion. Deletion goes through `prune_candidates`
and the data rule in CLAUDE.md.
