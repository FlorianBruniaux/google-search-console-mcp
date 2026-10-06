# Quick Site Health Check

Get a snapshot of your site's SEO health in one short conversation. Start here for a regular pulse check or when you want a fast read on what's happening.

Replace `yourdomain.com` with your GSC property URL.

---

## Step 1: Get the overview

> What's the overall SEO performance of yourdomain.com over the last 28 days? Flag anything that looks unusual.

The assistant pulls `get_performance_overview` and `check_alerts`, summarizes clicks, impressions, CTR and average position, and highlights measured risks.

## Step 2: Check for active issues

> Are there any traffic concentration risks or sudden drops I should know about?

The assistant calls `traffic_health_check` and `analytics_anomalies` to surface z-score spikes, dips and traffic concentration.

## Step 3: Find the quick wins

> What are the easiest improvements I can make right now on yourdomain.com?

The assistant calls `quick_wins` to surface page-level opportunities ranked 4 to 15 with high impressions and CTR below the built-in benchmark. It does not return query-level opportunities.

## Step 4: Compare to the previous period

> Compare the last 28 days with the immediately preceding 28 days. What changed, and which queries or pages account for the measured difference?

The assistant calls `compare_search_periods` for two adjacent equal-length windows. The result can localize a change, but it does not prove why the change happened.

## Optional: add Bing

> Bing is configured for https://yourdomain.com/. Compare the top queries and pages with Google over the requested 28-day window. Keep positions separate and omit deltas unless `compare_search_engines` confirms equal exact observed windows.

Use [google-bing-comparison.md](google-bing-comparison.md) when the cross-engine difference needs a deeper investigation.

---

**What to do with the output**: the quick audit surfaces signals. If something looks off, go deeper with [traffic-drop.md](traffic-drop.md) or [page-deep-dive.md](page-deep-dive.md). Keep this workflow read-only unless a later prompt explicitly confirms one named write.
