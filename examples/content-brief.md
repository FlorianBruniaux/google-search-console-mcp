# Content Brief from Real Search Data

Build a content brief based on what Google already knows about your page: which queries drive traffic, which queries you're leaving clicks on the table for, and how users behave once they arrive.

Replace `yourdomain.com/your-page-path` with the URL you want to build a brief for.

---

## Generate the brief

> Build a content brief for yourdomain.com/your-page-path based on its current GSC performance and user behavior.

Claude calls `content_brief`, which cross-references search queries, impressions without clicks, GA4 behavior data (if configured), and Core Web Vitals to suggest:

- Topics to cover or expand based on impressions you're not converting to clicks
- Queries to target in headings and subheadings
- Whether the page intent matches what searchers expect
- Content gaps compared to what's generating impressions but no engagement

---

## Expand the research

### Find missing topics

> What topics bring impressions to this page but no clicks? Those are search intents the page isn't covering yet.

### Understand what's already working

> Which queries on this page have the highest CTR? What do they have in common?

### Add behavioral context

> Do users who land on this page from organic search actually engage with it? What's the bounce rate and time on page?

Claude calls `ga4_organic_landing_pages` and `ga4_page_performance` to layer behavioral data on top of the search performance data.

---

## Brief a new page before writing it

> I want to create a new page targeting [topic]. What existing queries on my site are related? Are there pages I already rank for that I could link from to pass authority?

Claude analyzes your GSC data for adjacent queries, finds internal linking opportunities, and estimates the difficulty based on your current position distribution in that topic area.

---

## Check early signals after publishing

> I published yourdomain.com/new-page two weeks ago. Is it getting impressions yet? Which queries is Google starting to associate it with?

Claude calls `get_search_by_page_query` to read early ranking signals and `inspect_url` to confirm the page is indexed and crawlable.
