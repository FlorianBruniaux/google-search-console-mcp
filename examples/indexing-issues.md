# Indexing Issues

Find pages Google isn't indexing, understand why, and fix them. Works for single URLs, batches, and site-wide sweeps.

Replace `yourdomain.com` with your GSC property URL.

---

## Check a specific page

> Is yourdomain.com/your-page being indexed by Google? When was it last crawled?

Claude calls `inspect_url` and returns the exact indexing verdict, last crawl timestamp, crawl allowed status, and any canonical or redirect issues it found.

---

## Check multiple pages at once

> Check if these pages are indexed: yourdomain.com/page-1, yourdomain.com/page-2, yourdomain.com/page-3, yourdomain.com/page-4, yourdomain.com/page-5

Claude calls `batch_url_inspection` using true multipart HTTP (not a sequential loop) and returns a table with the indexing status of each URL in one request.

---

## Site-wide indexing sweep

> Run an indexing audit across my top pages on yourdomain.com. Which ones have issues and what kind?

Claude calls `check_indexing_issues` on your highest-traffic pages and groups results by verdict type: indexed, not indexed, crawled but not indexed, excluded by robots.txt or noindex.

---

## Sitemap coverage audit

> Audit all submitted sitemaps for yourdomain.com. Are there pages in the sitemaps that aren't getting indexed?

Claude calls `sitemap_audit`, cross-references declared URLs against 90 days of GSC coverage data, and flags any URL submitted in a sitemap but absent from the index.

### Follow-up

> For the pages in my sitemap that aren't indexed, group them by the reason Google gives. Which group is the largest and what's the fix?

---

## Submit pages for indexing

> Request indexing for yourdomain.com/new-page.

Claude calls `submit_url` to push the URL to Google's indexing queue.

> Submit these pages for indexing: yourdomain.com/new-page-1, yourdomain.com/new-page-2, yourdomain.com/new-page-3

Claude calls `submit_batch` for efficient bulk submission in a single request.
