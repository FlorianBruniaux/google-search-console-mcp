# Full SEO Audit

A complete audit across performance, indexing, sitemaps, Core Web Vitals and structured data. The assistant returns a prioritized action plan with P0, P1 and P2 findings. Add Bing or GA4 only when those providers are configured.

Replace `yourdomain.com` with your GSC property URL.

---

## Run the 7-check audit

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

## Investigate the first measured issue

### Inspect 1 P0 finding

> Tell me more about [the flagged issue]. What evidence supports it, what remains unknown, and how should I fix it?

### Rank P0 and P1 work by change size

> Of the P0 and P1 issues, which changes have the smallest implementation surface? Rank them by measured impact, name the affected URL or query, and keep effort as relative sizing rather than a time estimate.

### Inspect 1 evidence area

> Zoom in on the indexing issues only. For each affected page, tell me the exact status Google returned and what that means in practice.

### Convert findings into assigned tasks

> Convert the P0 and P1 issues into a task list with one sentence per task and a suggested owner (developer, content writer, or SEO).

## Mutation boundary

> Keep the audit read-only. If a recommendation requires a sitemap, URL, feed, Google Indexing API or IndexNow write, name the exact tool and target and wait for explicit confirmation in a separate turn. An accepted request is not evidence of crawl or indexation.

## Bounded destination checks (since 1.3.0)

Use `link_targets_audit(url, max_targets=30, max_requests=60)` on one affected page to observe internal destination statuses and retain their source anchors. Source GETs and redirect hops consume the same request budget. A received 404 is an HTTP observation; a timeout or safety refusal leaves terminal status unavailable. Read [bounded audit workflows](../docs/audit-workflows.md) before interpreting partial coverage.

## Optional follow-ups in 1.4.0

Use `search_weekday_reference` to compare disjoint Google windows on matching weekdays. If a caller draft or revision is provided, use `editorial_audit` and `rewrite_fidelity_check` for bounded mechanical warnings. Use `seo_change_impact` only after the caller declares a real page event and confirms equal before/after windows. Preview a supplied SiteOne JSON export with `crawl_import_preview`; do not invent an export or treat crawler scores as ranking evidence. Copy the [1.4.0 prompts](../docs/starter-prompt.md#test-140-without-provider-access) and retain each tool's unavailable states and coverage limits.
