# Traffic Drop Investigation

Start here when Google clicks or impressions fell and you do not know why. The workflow localizes the observed drop and affected queries or pages, then produces hypotheses to verify. It does not infer cause from correlation.

Replace `yourdomain.com` with your GSC property URL.

---

## Step 1: Confirm the drop and find the window

> My organic traffic dropped recently on yourdomain.com. Diagnose what happened, find when it started, and tell me which queries or pages were hit hardest.

The assistant calls `traffic_drops`, `analytics_anomalies` and `compare_search_periods` to find the affected window and isolate the pattern.

For concrete equal windows, release 1.4.0 can call `search_change_breakdown`. Ask for baseline `2026-09-01` through `2026-09-07` and comparison `2026-09-08` through `2026-09-14`, retaining each dimension separately. Read [bounded audit workflows](../docs/audit-workflows.md) for the exact CLI call. Absent rows are unknown, and matched contributions do not establish cause.

## Step 2: Separate traffic types

> Was the drop in web search, Discover, or News? Break it down by search type.

The assistant calls `search_type_breakdown` to split clicks and impressions by surface. This narrows the investigation; it does not establish a ranking, Discover or News cause by itself.

## Step 3: Identify lost queries

> Which specific queries lost the most clicks in the affected period? Are there common topics or intent patterns across them?

The assistant calls `seo_lost_queries` and groups affected queries by topic to show whether the measured drop is concentrated in one content area.

## Step 4: Check for technical causes

> Were there any indexing changes on the affected pages around the same time the traffic dropped?

The assistant calls `check_indexing_issues` on a bounded sample of affected URLs to check for noindex, canonicalization or crawl evidence.

## Step 5: Add available AI Overview context

> Which query and searchAppearance rows are available around the affected topic? Show their clicks, impressions, CTR and position as additional evidence.

The assistant calls `ai_overviews_impact` to retrieve the available GSC rows. The tool does not build a comparison cohort or control for position, so report the rows as context rather than an explanation for the drop.

---

## Common patterns

| Symptom | Investigation area | Tool that measures it |
|---------|-------------|----------------------|
| All queries drop at once | Site-wide change or external search change | `traffic_drops` + `compare_search_periods` |
| Only Discover traffic drops | Discover-specific change requiring investigation | `search_type_breakdown` |
| CTR drops but positions hold | Query and searchAppearance context, when available | `ai_overviews_impact` |
| Specific topic cluster drops | Sample affected URLs for indexation evidence | `check_indexing_issues` |
| Gradual decline over months | Lost queries and remaining striking-distance queries | `seo_lost_queries` + `seo_striking_distance` |

## Bing boundary

Bing's current provider contract does not expose the exact adjacent windows required by `traffic_drops` and `seo_lost_queries`. Use [google-bing-comparison.md](google-bing-comparison.md) for a side-by-side snapshot, and report Bing's refusal instead of approximating the missing periods.
