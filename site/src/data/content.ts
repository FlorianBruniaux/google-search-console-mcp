export const siteLinks = {
  repository: 'https://github.com/FlorianBruniaux/google-search-console-mcp',
  pypi: 'https://pypi.org/project/gsc-mcp-tools/',
  install: 'https://github.com/FlorianBruniaux/google-search-console-mcp/blob/main/docs/installation.md',
  googleSetup: 'https://github.com/FlorianBruniaux/google-search-console-mcp/blob/main/docs/google-setup.md',
  bingSetup: 'https://github.com/FlorianBruniaux/google-search-console-mcp/blob/main/docs/bing-setup.md',
  starterPrompts: 'https://github.com/FlorianBruniaux/google-search-console-mcp/tree/main/examples',
  changelog: 'https://github.com/FlorianBruniaux/google-search-console-mcp/blob/main/CHANGELOG.md',
  architecture: 'https://github.com/FlorianBruniaux/google-search-console-mcp/blob/main/docs/architecture.md',
  bingContract: 'https://github.com/FlorianBruniaux/google-search-console-mcp/blob/main/docs/validation/bing-api-contract.md',
  license: 'https://github.com/FlorianBruniaux/google-search-console-mcp/blob/main/LICENSE',
  author: 'https://www.florian.bruniaux.com/about/?utm_source=search-console-mcp&utm_medium=website',
} as const

export const providers = [
  {
    id: 'google',
    title: 'Google data',
    copy: 'Search Console performance and inspection, optional GA4 behavior data, and optional CrUX field data.',
    items: ['Search performance', 'URL inspection', 'GA4', 'CrUX'],
  },
  {
    id: 'bing',
    title: 'Bing data',
    copy: 'Webmaster performance, crawl, feeds, backlinks and guarded submissions for sites visible to the configured Bing account.',
    items: ['Queries and pages', 'Crawl signals', 'Feeds', 'IndexNow'],
  },
  {
    id: 'public',
    title: 'Public-page analysis',
    copy: 'Fetched HTML, robots, sitemaps, structured data, content and internal-link signals without private provider credentials.',
    items: ['Metadata', 'Schema', 'Sitemaps', 'Internal links'],
  },
] as const

export const workflowSteps = [
  ['Connect', 'Select only the verified properties and provider credentials you need.'],
  ['Measure', 'Read queries, pages, crawl signals and public-page evidence.'],
  ['Compare', 'Keep provider semantics and observed windows explicit.'],
  ['Explain', 'Return structured facts, derived values and recommendations.'],
  ['Submit', 'Run bounded write tools only after the target and action are confirmed.'],
] as const

export const installSteps = [
  ['Evaluate once', 'Run uvx gsc-mcp-tools without changing a project environment.'],
  ['Install persistently', 'Run uv tool install gsc-mcp-tools and point the MCP client at the installed executable.'],
  ['Verify access', 'Run gsc-cli list, then verify each configured provider separately.'],
] as const

export const evidenceStates = [
  ['Observed', 'API responses and fetched public-page data.'],
  ['Derived', 'Calculations tied to an explicit observed window.'],
  ['Requested', 'A provider accepted a submission. Crawl and indexation remain unproven.'],
] as const

export const faqs = [
  {
    question: 'Does one Bing API key work for every site?',
    answer: 'One Bing Webmaster API key can access the verified sites visible to that Bing account. Every tool call still names its target site. IndexNow uses a different key verified on each target host.',
  },
  {
    question: 'Do I need every Google API enabled?',
    answer: 'No. Configure the provider families you use. Search Console credentials cover the core search workflows. GA4, CrUX and eligible Indexing API workflows require their own optional configuration.',
  },
  {
    question: 'Does a successful submission mean the page is indexed?',
    answer: 'No. An accepted submission proves only that the provider accepted the request. Crawl and indexation must be measured separately in a later comparable check.',
  },
  {
    question: 'Can I use the server from Claude and Codex?',
    answer: 'Yes. Search Console MCP runs over stdio and can be configured in Claude, Codex and other compatible MCP clients. The executable path and configuration format depend on the client.',
  },
  {
    question: 'Where do credentials live?',
    answer: 'Credentials stay in the MCP server environment or the client configuration. The public website never receives them, and prompts should not contain secret values.',
  },
] as const
