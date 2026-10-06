# Full SEO Audit

A complete audit across performance, indexing, sitemaps, Core Web Vitals and structured data. The assistant returns a prioritized action plan with P0, P1 and P2 findings. Add Bing or GA4 only when those providers are configured.

Replace `yourdomain.com` with your GSC property URL.

---

## Start with one prompt

> Run a full SEO audit for the Google property sc-domain:yourdomain.com and give me a prioritized P0/P1/P2 action plan. Bing is available as https://yourdomain.com/ and GA4 is configured. Confirm provider access first, preserve observed windows, and separate measured facts, derived values, hypotheses and recommendations.

This single prompt triggers a multi-step investigation. The assistant will:

1. Pull 90 days of performance data and surface anomalies
2. Check for traffic drops and lost queries
3. Audit indexing across your top pages
4. List submitted sitemaps, audit the selected main sitemap, and treat URLs without Search Analytics rows as inspection candidates rather than non-indexed pages
5. Validate structured data on high-traffic pages
6. Pull Core Web Vitals from the Chrome UX Report (LCP, INP, CLS)
7. Return a ranked action plan

---

## Going deeper after the initial audit

### Dig into a specific P0 issue

> Tell me more about [the flagged issue]. What evidence supports it, what remains unknown, and how should I fix it?

### Prioritize by change size

> Of the P0 and P1 issues, which changes have the smallest implementation surface? Rank them by measured impact, name the affected URL or query, and keep effort as relative sizing rather than a time estimate.

### Focus on a specific area

> Zoom in on the indexing issues only. For each affected page, tell me the exact status Google returned and what that means in practice.

### Turn findings into tasks

> Convert the P0 and P1 issues into a task list with one sentence per task and a suggested owner (developer, content writer, or SEO).

## Mutation boundary

> Keep the audit read-only. If a recommendation requires a sitemap, URL, feed, Google Indexing API or IndexNow write, name the exact tool and target and wait for explicit confirmation in a separate turn. An accepted request is not evidence of crawl or indexation.
