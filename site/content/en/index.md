# Search Console MCP documentation

Use Search Console MCP to inspect Google Search Console, Bing Webmaster Tools, optional GA4 and CrUX data, and public-page signals from one bounded interface.

<figure class="docs-visual">
  <img src="/images/docs/search-evidence-map.webp" width="1376" height="768" alt="Three separate evidence streams converge on a bounded analysis workspace." loading="eager" fetchpriority="high">
  <figcaption>Google, Bing, and public-page evidence stay distinct while the assistant analyzes them in one bounded workspace.</figcaption>
</figure>

## Start with 1 of these 5 tasks

1. [Install the server](/docs/installation/) without launching duplicate long-running processes.
2. [Connect Google](/docs/google-setup/) and verify the properties exposed to the configured identity.
3. [Connect Bing](/docs/bing-setup/) and keep the account API key separate from IndexNow host keys.
4. [Run a starter prompt](/docs/prompts/) or choose an [example workflow](/docs/examples/).
5. [Interpret the evidence](/docs/evidence-and-safety/) before submitting a write action.

## Evidence returned by 3 sources

The server can return provider responses, fetched public-page data, and calculations tied to explicit windows. An accepted submission proves that a provider accepted a request. It does not prove a later crawl or indexation.

<div class="provider-boundaries" role="list" aria-label="Evidence providers">
  <div role="listitem"><strong>Google</strong><span>Search performance, inspection, GA4 and CrUX when configured.</span></div>
  <div role="listitem"><strong>Bing</strong><span>Webmaster performance, crawl, feeds, backlinks and bounded submissions.</span></div>
  <div role="listitem"><strong>Public pages</strong><span>HTML, robots, sitemaps, metadata, schema and internal links.</span></div>
</div>

## Source code and release history

Read the [architecture](/docs/architecture/), review the [changelog](/docs/changelog/), or inspect the [source repository](https://github.com/FlorianBruniaux/google-search-console-mcp).
