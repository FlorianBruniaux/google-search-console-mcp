---
name: ai-overviews-impact
description: Assess evidence limits for Google AI Overview exposure and investigate
  descriptive CTR changes without attributing lost clicks to AI. Use for AI Overview
  impact, SGE cannibalization, or declining CTR despite stable rankings. Aussi déclenché
  par "les AI Overviews me piquent des clics", "mon CTR baisse alors que je suis
  toujours premier", "les réponses IA de Google" ou "aperçus IA".
---

# AI Overview evidence review

Report generic Search Console observations separately from unavailable AI exposure
and unidentified causal impact. A declining CTR with stable position does not
identify AI Overviews as its cause.

## Steps

1. Call `list_properties` and record the exact `site_url`. Done when the property
   identity is established or the access failure is reported.
2. Call `ai_overviews_impact`. Despite its legacy name, it now requests only
   `searchAppearance`, the documented discovery dimension. It returns generic Web
   appearance rows sorted by impressions, not query-level AI measurements. Preserve
   `source_scope`, `source_status`, `ai_exposure`, `evidence_limits` and field-level
   `_meta.evidence`. Done when observed generic appearances, empty generic data,
   invalid/unsupported request (400), or access denial (403) is reported distinctly.
   The legacy `AI_OVERVIEWS_NOT_AVAILABLE` error alias does not establish property
   capability, AI presence or AI absence.
3. Call `compare_search_periods(site, days=90)` for consecutive property-level
   windows. This tool accepts `site` and `days`; it does not accept query dimensions
   or a query limit. Report returned dates, clicks, impressions and descriptive
   deltas. Calculate period CTR only for present counts and positive impressions.
   Done when the observed window comparison or missing data is reported without
   assigning the change to AI.
4. If independent query-level or SERP observations are supplied, retain their
   dates, query, locale, device, method and coverage. Stable-position CTR declines
   are descriptive observations. An observed AI result at one time establishes
   neither exposure throughout the window nor its causal effect. Done when each
   additional observation has a source and an explicit limit, or is unavailable.

## Output

- Generic search appearances: returned label, clicks, impressions, CTR and position,
  with source scope, date window and coverage limits. A label that looks like
  `AI_OVERVIEW` is not authenticated by its spelling or a synthetic test fixture.
- Property comparison: returned windows and descriptive click/impression deltas;
  calculated CTR when its denominator is usable.
- AI exposure: unavailable and unverified for this tool. Do not report AI-exposed
  query counts, queries safe from AI, AI-attributed lost clicks or a causal effect.
- Next evidence needed: specify the missing observation that would support a
  narrower conclusion. Do not recommend changing content, schema or query strategy
  on the assumption that a CTR decline proves AI cannibalization.

## Provider boundary

Google includes AI feature traffic in the overall Web performance report. Its API
instructions require `searchAppearance` alone for discovery, then an observed
appearance value as a filter for any separate query/page breakdown. This workflow
performs discovery only and contains no verified AI-specific appearance mapping.
Documentation support and a live provider observation are both required before
introducing such a mapping. No authenticated provider request was made to validate
AI exposure in this implementation.

Sources checked on 2026-10-09:
[Google AI features and reporting](https://developers.google.com/search/docs/appearance/ai-features#measuring-the-performance-of-your-site),
[Google search appearance retrieval](https://developers.google.com/webmaster-tools/v1/how-tos/all-your-data#getting_search_appearance_data),
[Search Analytics API reference](https://developers.google.com/webmaster-tools/v1/searchanalytics/query).
