---
name: ai-overviews-impact
description: Measure how Google AI Overviews are cannibalizing organic CTR. Use when
  asked about AI Overview impact, SGE cannibalization, or why CTR is dropping despite
  stable rankings.
---

# AI Overviews Impact Analysis

Measure how Google's AI Overviews are affecting organic click-through rates on the property.

## Steps

1. Call `list_properties` to confirm the exact `site_url`.
2. Call `ai_overviews_impact` to get the dedicated report on queries where AI Overviews appear and their CTR compared to queries without.
3. Call `compare_search_periods` for the last 90 days vs. the prior 90 days, using `dimensions=query` and `limit=100`.
4. From step 3, isolate queries where position held steady or improved but CTR declined by more than 15%. These are the primary AI Overview candidates.
5. Sort those queries by impressions descending and take the top 20.

## Output format

**AI Overview impact summary**: total queries affected, estimated clicks lost vs. 90 days ago, overall CTR delta.

**Most impacted queries table**: Query | Position | Impressions | CTR now | CTR 90d ago | CTR delta | Est. clicks lost

**Strategic recommendations**:
- Which query types are most cannibalized (informational vs. navigational vs. transactional)
- Whether to optimize for AI Overview inclusion (structured answers, schema markup) or shift focus to transactional intents where AI Overviews are less prevalent
- Queries safe from AI Overviews that are worth reinforcing
