# Full SEO Audit

A complete audit across performance, indexing, sitemaps, Core Web Vitals, and structured data. Claude returns a prioritized action plan with P0 (fix now), P1 (fix this month), and P2 (fix eventually) issues.

Expect 15 to 25 minutes depending on site size.

Replace `yourdomain.com` with your GSC property URL.

---

## Start with one prompt

> Run a full SEO audit for yourdomain.com and give me a prioritized action plan with P0/P1/P2 issues.

This single prompt triggers a multi-step investigation. Claude will:

1. Pull 90 days of performance data and surface anomalies
2. Check for traffic drops and lost queries
3. Audit indexing across your top pages
4. Inspect all submitted sitemaps for coverage gaps
5. Validate structured data on high-traffic pages
6. Pull Core Web Vitals from the Chrome UX Report (LCP, INP, CLS)
7. Return a ranked action plan

---

## Going deeper after the initial audit

### Dig into a specific P0 issue

> Tell me more about [the issue Claude flagged]. What exactly is broken and how do I fix it?

### Prioritize by effort

> Of the P0 and P1 issues you found, which ones can be fixed in under an hour? Rank them by impact.

### Focus on a specific area

> Zoom in on the indexing issues only. For each affected page, tell me the exact status Google returned and what that means in practice.

### Turn findings into tasks

> Convert the P0 and P1 issues into a task list with one sentence per task and a suggested owner (developer, content writer, or SEO).

---

**Tip**: the hosted version at [advancedgsc.com](https://www.advancedgsc.com/mcp) adds GA4 integration, which brings behavioral data (engagement rate, time on page, conversions) into the audit alongside the GSC data.
