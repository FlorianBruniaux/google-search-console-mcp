---
name: internal-linking-audit
description: Audit internal linking on a page, weighted by where each link sits. A link
  in the body of a page carries far more weight than the same link in the footer or
  the main nav. Surfaces targets linked only from footer/nav, generic anchors, and
  internal nofollow. Use when asked about internal links, anchor text, link placement,
  or orphan pages. Aussi déclenché en français par "maillage interne", "mes liens
  internes", "liens en footer", "texte d'ancre", "où placer mes liens", "pages
  orphelines", "est-ce que mes liens sont bien placés", "audit du maillage".
---

# Internal Linking Audit

A link in the body of a page carries materially more weight than the same link in the
footer or the main nav. This audit measures that placement instead of assuming it.

## Input

A page URL. If the user gave a site rather than a page, ask which page, or run the
audit on the pages that matter most from `get_search_analytics`.

## Steps

1. Call `internal_links_audit` on the target URL. No auth needed, no quota consumed.
2. Read `footer_only_targets` first. These are internal pages linked from nav, footer
   or aside and from the body of no page. This is the highest-value finding.
3. Check `body_links` against `demoted_links`. A page whose internal links are almost
   all structural has no editorial linking at all.
4. Read `generic_anchors` and `empty_anchors`. The anchor is a ranking signal for the
   target page, so "en savoir plus" wastes it.
5. Read `nofollow_internal`. An internal link marked nofollow throws away the weight
   it would otherwise pass, and it is almost always unintentional.

## Cross-reference before recommending

Do not recommend adding links blind. Pull `seo_striking_distance` for the site first.
A page sitting at position 11 to 20 with no body link pointing at it is where an
internal link pays off fastest. A page already at position 3 does not need one.

Same rule in reverse: before calling a page orphaned, confirm with
`get_search_analytics` that it actually has impressions worth rescuing.

## Output format

**Verdict**: healthy or issues_found, with the counts behind it.

**Placement**: body links vs nav/footer/aside links, and what that ratio says.

**Targets linked only from footer or nav**: Path | Zones | Current anchor

For each one, say where a body link should go instead, naming the source page.

**Anchor problems**: URL | Current anchor | Suggested anchor

**Priority list**:
1. Critical: a page with search impressions and no body link anywhere
2. High: an important target that lives only in the footer
3. Medium: generic or empty anchors on pages that matter
4. Low: internal nofollow, self-links

Every recommendation names a source page, a target page, and the anchor to use.
"Improve internal linking" is not a recommendation.
