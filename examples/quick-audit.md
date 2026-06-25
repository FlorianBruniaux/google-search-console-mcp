# Quick Site Health Check

Get a snapshot of your site's SEO health in one short conversation. Start here for a regular pulse check or when you want a fast read on what's happening.

Replace `yourdomain.com` with your GSC property URL.

---

## Step 1: Get the overview

> What's the overall SEO performance of yourdomain.com over the last 28 days? Flag anything that looks unusual.

Claude pulls `get_performance_overview` and `check_alerts`, summarizes clicks, impressions, CTR, and average position, and highlights anything outside the normal range.

## Step 2: Check for active issues

> Are there any traffic concentration risks or sudden drops I should know about?

Claude calls `traffic_health_check` and `analytics_anomalies` to surface z-score spikes and dips above a statistical threshold. A single page driving over 50% of total clicks is a risk worth knowing about.

## Step 3: Find the quick wins

> What are the easiest improvements I can make right now on yourdomain.com?

Claude calls `quick_wins` to surface high-impression, low-click pages and queries sitting just below page one.

## Step 4: Compare to last period

> How does this month compare to the same period last year? What changed and why?

Claude calls `compare_search_periods` with year-over-year ranges and explains the delta.

---

**What to do with the output**: the quick audit surfaces signals. If something looks off, go deeper with [traffic-drop.md](traffic-drop.md) or [page-deep-dive.md](page-deep-dive.md).
