# Search Console MCP documentation

Use Search Console MCP with Claude, Codex or another AI assistant to understand your latest SEO changes and get a prioritized list of fixes. Ask in plain language, without needing SEO expertise: "Analyze my site's recent performance and tell me what to fix first."

The server retrieves search metrics and audits pages; your assistant explains traffic changes, finds ranking opportunities and suggests changes to titles, content, internal links or technical SEO. Connect your accounts once, review the suggestions, then rerun the analysis to measure their effect. Recurring checks require a client automation or scheduler, and ranking improvements are not guaranteed.

## Choose your starting point

| Your problem | Open the route | What you get |
| --- | --- | --- |
| I’m new to SEO: where do I start? | [Assess my site and learn what matters](/#seo-getting-started) | A starting assessment, three priorities and what to measure |
| My traffic is dropping | [Analyze recent changes](/#seo-traffic) | A diagnosis and the affected pages, with supporting metrics |
| I want better search rankings | [Find ranking opportunities](/#seo-rankings) | A prioritized list of suggested fixes |
| My pages are hard to find | [Check indexing and technical SEO](/#seo-indexing) | Detected issues and suggested corrections |

Each route includes a prompt to copy into Claude or Codex, the data needed and an illustrative result. The copied text asks the assistant to use Search Console MCP and verify its connection before analysis. It includes links to the installation guide, Google setup and the matching GitHub example so the assistant can guide any missing setup. Replace the example site before sending the prompt.

If you are new to SEO, choose the first route. Your assistant explains what to analyze, how to interpret the findings and which metrics to follow. You can start with public pages; connect Google Search Console for search performance data. GA4 and Bing are optional.

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

For explicit Google comparison windows and bounded destination HTTP checks, use [bounded audit workflows](/docs/audit-workflows/). Release 1.3.0 includes these tools in its 85-tool registry.

The source checkout adds unreleased declared-change follow-up and draft/rewrite checks, bringing its registry to 87 tools. Read [editorial workflows](/docs/editorial-workflows/) for the draft and mechanical comparison boundaries.
