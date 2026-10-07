import sitemap from '@astrojs/sitemap'
import starlight from '@astrojs/starlight'
import { defineConfig } from 'astro/config'

export default defineConfig({
  site: 'https://search-console.bruniaux.com',
  base: '/',
  output: 'static',
  trailingSlash: 'always',
  integrations: [
    starlight({
      title: 'Search Console MCP',
      description: 'Documentation for Google Search Console, Bing Webmaster Tools and public-page analysis through MCP.',
      favicon: '/favicon.svg',
      defaultLocale: 'root',
      locales: {
        root: { label: 'English', lang: 'en' },
        fr: { label: 'Français', lang: 'fr' },
      },
      social: [
        {
          icon: 'github',
          label: 'GitHub',
          href: 'https://github.com/FlorianBruniaux/google-search-console-mcp',
        },
      ],
      customCss: ['./src/styles/starlight-overrides.css'],
      components: {
        Head: './src/components/docs/Head.astro',
        SiteTitle: './src/components/docs/SiteTitle.astro',
        Footer: './src/components/docs/DocsFooter.astro',
      },
      sidebar: [
        {
          label: 'Start · Démarrer',
          items: [
            { slug: 'docs' },
            { slug: 'docs/installation' },
            { slug: 'docs/google-setup' },
            { slug: 'docs/bing-setup' },
          ],
        },
        {
          label: 'Use · Utiliser',
          items: [
            { slug: 'docs/prompts' },
            {
              label: 'Examples · Scénarios',
              collapsed: false,
              items: [
                { slug: 'docs/examples' },
                { slug: 'docs/examples/quick-audit' },
                { slug: 'docs/examples/google-bing-comparison' },
                { slug: 'docs/examples/full-audit' },
                { slug: 'docs/examples/keyword-opportunities' },
                { slug: 'docs/examples/page-deep-dive' },
                { slug: 'docs/examples/traffic-drop' },
                { slug: 'docs/examples/indexing-issues' },
                { slug: 'docs/examples/content-brief' },
              ],
            },
          ],
        },
        {
          label: 'Understand · Comprendre',
          items: [{ slug: 'docs/architecture' }, { slug: 'docs/evidence-and-safety' }],
        },
        {
          label: 'Project · Projet',
          items: [{ slug: 'docs/changelog' }, { slug: 'docs/license' }],
        },
      ],
    }),
    sitemap(),
  ],
})
