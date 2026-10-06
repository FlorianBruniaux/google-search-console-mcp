import sitemap from '@astrojs/sitemap'
import { defineConfig } from 'astro/config'

export default defineConfig({
  site: 'https://search-console.bruniaux.com',
  base: '/',
  output: 'static',
  trailingSlash: 'always',
  integrations: [sitemap()],
})
