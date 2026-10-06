import { siteLinks } from './content'

export interface NavigationLink {
  href: string
  label: string
  description: string
  external?: boolean
}

export interface NavigationGroup {
  label: string
  links: NavigationLink[]
}

export interface NavigationSection {
  id: 'analyze' | 'start' | 'resources'
  label: string
  description: string
  overview: { href: string; label: string; external?: boolean }
  groups: NavigationGroup[]
}

export const navigationSections: NavigationSection[] = [
  {
    id: 'analyze',
    label: 'Analyze',
    description: 'Choose the evidence source before interpreting search performance.',
    overview: { href: '#capabilities', label: 'Compare all capabilities' },
    groups: [
      {
        label: 'Search providers',
        links: [
          { href: '#provider-google', label: 'Google data', description: 'Search Console, GA4 and CrUX evidence.' },
          { href: '#provider-bing', label: 'Bing data', description: 'Webmaster performance, crawl and submission signals.' },
          { href: '#provider-public', label: 'Public-page analysis', description: 'Metadata, schema, sitemaps and internal links.' },
        ],
      },
      {
        label: 'Workflow',
        links: [
          { href: '#workflow', label: 'How it works', description: 'Connect, measure, compare, explain and submit.' },
          { href: '#safety', label: 'Evidence boundaries', description: 'Separate observed, derived and requested states.' },
          { href: '#faq', label: 'FAQ', description: 'Resolve common provider and credential questions.' },
        ],
      },
    ],
  },
  {
    id: 'start',
    label: 'Start',
    description: 'Install the smallest useful setup, then verify each provider separately.',
    overview: { href: '#install', label: 'See the installation path' },
    groups: [
      {
        label: 'Install',
        links: [
          { href: '#install-evaluate', label: 'Evaluate once', description: 'Run the package with uvx without changing a project.' },
          { href: '#install-persistent', label: 'Persistent install', description: 'Install the executable for repeat MCP use.' },
          { href: '#install-verify', label: 'Verify access', description: 'List properties and validate providers independently.' },
        ],
      },
      {
        label: 'Configure providers',
        links: [
          { href: siteLinks.googleSetup, label: 'Google setup', description: 'Configure Search Console and optional Google services.' },
          { href: siteLinks.bingSetup, label: 'Bing setup', description: 'Configure Webmaster Tools and host-scoped IndexNow.' },
          { href: siteLinks.starterPrompts, label: 'Starter prompts', description: 'Use bounded prompts for common audit workflows.' },
        ],
      },
    ],
  },
  {
    id: 'resources',
    label: 'Resources',
    description: 'Inspect the source, release history and explicit operating contracts.',
    overview: { href: siteLinks.repository, label: 'Open the repository', external: true },
    groups: [
      {
        label: 'Project',
        links: [
          { href: siteLinks.repository, label: 'GitHub', description: 'Source, issues and contribution history.', external: true },
          { href: siteLinks.pypi, label: 'PyPI', description: 'Published package and version metadata.', external: true },
          { href: siteLinks.changelog, label: 'Changelog', description: 'Release-by-release product changes.' },
          { href: siteLinks.architecture, label: 'Architecture', description: 'Server boundaries and provider structure.' },
        ],
      },
      {
        label: 'Trust & documentation',
        links: [
          { href: siteLinks.install, label: 'Installation', description: 'Client-specific setup and verification.' },
          { href: siteLinks.bingContract, label: 'Evidence and safety', description: 'States, scopes and write boundaries.' },
          { href: siteLinks.license, label: 'License', description: 'MIT usage terms.' },
          { href: '#faq', label: 'FAQ', description: 'Credentials, providers and evidence semantics.' },
        ],
      },
    ],
  },
]
