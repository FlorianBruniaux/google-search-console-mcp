# Indexing Issues

Find pages Google isn't indexing, understand why, and fix them. Works for single URLs, batches, and site-wide sweeps.

Replace `yourdomain.com` with your GSC property URL.

---

## Check a specific page

> Is yourdomain.com/your-page being indexed by Google? When was it last crawled?

The assistant calls `inspect_url` and returns Google's indexing verdict, last crawl timestamp, crawl-allowed status and canonical evidence.

---

## Check multiple pages at once

> Check if these pages are indexed: yourdomain.com/page-1, yourdomain.com/page-2, yourdomain.com/page-3, yourdomain.com/page-4, yourdomain.com/page-5

The assistant calls `batch_url_inspection` for the bounded URL set and returns the observed status of each inspected URL.

---

## Bounded indexing sweep

> Run an indexing audit across my 10 highest-traffic pages on yourdomain.com. Which inspected URLs have issues, and what exact verdict did Google return?

The assistant calls `check_indexing_issues` on the bounded high-traffic sample and groups the returned verdicts without generalizing them to the whole site.

---

## Sitemap coverage audit

> List the submitted sitemaps for yourdomain.com, then audit the main sitemap. Which declared URLs have no Search Analytics page row in the last 90 days and should be sampled with URL Inspection?

The assistant calls `sitemap_audit` to compare declared URLs with 90 days of Search Analytics page rows. URLs without search data are candidates for URL Inspection, not evidence that they are absent from the index.

### Follow-up

> Inspect the sampled URLs that have no Search Analytics row. Group only the returned URL Inspection verdicts by reason and keep uninspected URLs as unknown.

---

## Submit eligible pages through Google's Indexing API

Google restricts the Indexing API to pages containing `JobPosting` or `BroadcastEvent` embedded in a `VideoObject`. For other page types, use URL Inspection for diagnosis and normal discovery paths such as sitemaps and internal links. See [Google's official policy](https://developers.google.com/search/apis/indexing-api/v3/quickstart).

> This page contains eligible JobPosting or livestream BroadcastEvent markup: yourdomain.com/new-page. Inspect it, verify eligibility, state the exact `submit_url` action, and wait for my explicit confirmation before submitting.

After confirmation, the assistant can call `submit_url` once. The returned status proves notification receipt, not crawl or indexation.

> These three pages contain eligible markup: yourdomain.com/new-page-1, yourdomain.com/new-page-2, yourdomain.com/new-page-3. Inspect and validate each page, report the exact `submit_batch` target set, and wait for my explicit confirmation.

After confirmation, `submit_batch` can send the bounded eligible set in one HTTP batch. Check the pages again later with URL Inspection instead of treating acceptance as indexation.
