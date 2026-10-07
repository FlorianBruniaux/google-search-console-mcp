# Content Brief from Real Search Data

Build a content brief from observed Search Console data: which queries drive traffic, which question queries appear, and how users behave once they arrive when GA4 is configured.

Replace `yourdomain.com/your-page-path` with the URL you want to build a brief for.

---

## Generate 1 evidence-based brief

> Build a content brief for yourdomain.com/your-page-path based on its current GSC performance and user behavior.

The assistant calls `content_brief`, which returns the page's top GSC queries, detected question queries, current focus and optional GA4 engagement data. Use those observations to draft:

- Topics to cover or expand based on impressions you're not converting to clicks
- Queries to target in headings and subheadings
- Whether the page intent matches what searchers expect
- Content hypotheses to validate against the page itself

Core Web Vitals are not part of `content_brief`; call `crux_page_vitals` separately when field performance matters.

---

## Add 3 evidence layers

### List underperforming query topics

> Use `get_search_by_page_query` for this page. Which queries have impressions but few or no clicks? Treat them as topics to inspect, not proof that the page fails to cover the intent.

### List queries with the highest CTR

> Which queries on this page have the highest CTR? What do they have in common?

### Add GA4 behavior when available

> Do users who land on this page from organic search actually engage with it? What's the bounce rate and time on page?

The assistant calls `ga4_organic_landing_pages` and `ga4_page_performance` to layer behavioral data on top of search performance. Engagement metrics do not explain ranking changes on their own.

---

## Brief 1 new page before writing

> I want to create a new page targeting [topic]. What observed queries on my site are related? Which existing pages are relevant internal-link candidates based on measured search visibility and the current link graph?

The assistant combines GSC query evidence with `link_equity_map` or `internal_links_audit`. It should report coverage limits rather than estimate keyword difficulty from position data alone.

---

## Check search signals after publishing

> I published yourdomain.com/new-page two weeks ago. Is it getting impressions yet? Which queries is Google starting to associate it with?

The assistant calls `get_search_by_page_query` to read early visibility signals and `inspect_url` for Google's current indexation evidence. No impressions yet is not proof that the page is absent from the index.
