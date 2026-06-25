# Traffic Drop Investigation

Start here when clicks or impressions fell and you don't know why. Claude identifies when the drop started, which queries were affected, and the most likely cause.

Replace `yourdomain.com` with your GSC property URL.

---

## Step 1: Confirm the drop and find the window

> My organic traffic dropped recently on yourdomain.com. Diagnose what happened, find when it started, and tell me which queries or pages were hit hardest.

Claude calls `traffic_drops`, `analytics_anomalies`, and `compare_search_periods` to find the affected window and isolate the pattern.

## Step 2: Separate traffic types

> Was the drop in web search, Discover, or News? Break it down by search type.

Claude calls `search_type_breakdown` to split clicks and impressions by surface. This tells you whether you're dealing with a ranking issue, a Discover eligibility problem, or something specific to News.

## Step 3: Identify lost queries

> Which specific queries lost the most clicks in the affected period? Are there common topics or intent patterns across them?

Claude calls `seo_lost_queries` and clusters affected queries by topic to find whether the drop targets a specific content area.

## Step 4: Check for technical causes

> Were there any indexing changes on the affected pages around the same time the traffic dropped?

Claude calls `check_indexing_issues` on the top affected URLs to rule out accidental noindex tags, canonicalization changes, or crawl errors.

## Step 5: Rule out AI Overviews cannibalization

> Could AI Overviews explain the CTR drop even if my positions held steady?

Claude calls `ai_overviews_impact` to check whether queries that retained their position still lost clicks due to AI Overview appearances in the results.

---

## Common patterns

| Symptom | Likely cause | Tool that diagnoses it |
|---------|-------------|----------------------|
| All queries drop at once | Algorithm update or site-wide penalty | `traffic_drops` + `compare_search_periods` |
| Only Discover traffic drops | Content freshness or authority signal | `search_type_breakdown` |
| CTR drops but positions hold | AI Overviews cannibalization | `ai_overviews_impact` |
| Specific topic cluster drops | Page removed, noindex, or deindexed | `check_indexing_issues` |
| Gradual decline over months | Competitor gains, content staleness | `seo_lost_queries` + `seo_striking_distance` |
