import assert from 'node:assert/strict'
import { readFile, readdir } from 'node:fs/promises'
import test from 'node:test'

const dist = new URL('../dist/', import.meta.url)
const html = await readFile(new URL('index.html', dist), 'utf8')
const product = JSON.parse(await readFile(new URL('../src/generated/product.json', import.meta.url), 'utf8'))

function jsonLdEntries() {
  return [...html.matchAll(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/g)]
    .map((match) => JSON.parse(match[1]))
}

test('publishes canonical and social metadata', () => {
  assert.match(html, /<link rel="canonical" href="https:\/\/search-console\.bruniaux\.com\/"/)
  assert.match(html, /<meta property="og:image" content="https:\/\/search-console\.bruniaux\.com\/og-image\.png"/)
  assert.match(html, /<meta property="og:site_name" content="Search Console MCP"/)
  assert.match(html, /<meta property="og:image:alt" content="[^"]+"/)
  assert.match(html, /<meta name="twitter:card" content="summary_large_image"/)
  assert.match(html, /<meta name="twitter:title" content="Search Console MCP for Google, Bing and SEO Analytics"/)
  assert.match(html, /<meta name="twitter:description" content="Connect AI assistants to Google Search Console, Bing Webmaster Tools, GA4, CrUX and guarded SEO workflows\."/)
  assert.match(html, /<meta name="twitter:image" content="https:\/\/search-console\.bruniaux\.com\/og-image\.png"/)
  assert.match(html, /<link rel="icon" type="image\/svg\+xml" href="\/favicon\.svg"/)
  assert.equal((html.match(/<h1[ >]/g) ?? []).length, 1)
})

test('publishes reciprocal landing alternates and localized metadata', async () => {
  const frenchHtml = await readFile(new URL('fr/index.html', dist), 'utf8')
  assert.match(html, /<link rel="alternate" hreflang="en" href="https:\/\/search-console\.bruniaux\.com\/"/)
  assert.match(html, /<link rel="alternate" hreflang="fr" href="https:\/\/search-console\.bruniaux\.com\/fr\/"/)
  assert.match(html, /<link rel="alternate" hreflang="x-default" href="https:\/\/search-console\.bruniaux\.com\/"/)
  assert.match(frenchHtml, /<link rel="canonical" href="https:\/\/search-console\.bruniaux\.com\/fr\/"/)
  assert.match(frenchHtml, /<link rel="alternate" hreflang="en" href="https:\/\/search-console\.bruniaux\.com\/"/)
  assert.match(frenchHtml, /<link rel="alternate" hreflang="fr" href="https:\/\/search-console\.bruniaux\.com\/fr\/"/)
  assert.match(frenchHtml, /<meta property="og:locale" content="fr_FR"/)
  assert.match(frenchHtml, /<meta name="twitter:title" content="Search Console MCP pour Google, Bing et l’analyse SEO"/)
})

test('keeps structured data aligned with generated and visible content', () => {
  const entries = jsonLdEntries()
  const software = entries.find((entry) => entry['@type'] === 'SoftwareApplication')
  const faq = entries.find((entry) => entry['@type'] === 'FAQPage')
  assert.ok(software, 'SoftwareApplication must be in the built HTML')
  assert.ok(faq, 'FAQPage must be in the built HTML')
  assert.equal(software['@context'], 'https://schema.org')
  assert.equal(faq['@context'], 'https://schema.org')
  assert.equal(software.softwareVersion, product.version)
  assert.equal(software.sameAs, product.repository)
  assert.equal(Object.hasOwn(software, 'codeRepository'), false, 'codeRepository belongs to SoftwareSourceCode')
  assert.equal(software.name, 'Search Console MCP')
  assert.equal(software.url, 'https://search-console.bruniaux.com/')
  assert.equal(software.downloadUrl, 'https://pypi.org/project/gsc-mcp-tools/')
  assert.equal(software.license, 'https://github.com/FlorianBruniaux/google-search-console-mcp/blob/main/LICENSE')
  assert.equal(faq.mainEntity.length, (html.match(/<details data-faq-item/g) ?? []).length)
  assert.ok(faq.mainEntity.length > 0, 'FAQ entries must not be empty')
  for (const entity of faq.mainEntity) {
    assert.equal(entity['@type'], 'Question')
    assert.equal(entity.acceptedAnswer['@type'], 'Answer')
    // Compare visible nodes, not the JSON-LD text itself.
    assert.ok(html.includes(`<summary>${entity.name}<span aria-hidden="true">+</span></summary>`))
    assert.ok(html.includes(`<p>${entity.acceptedAnswer.text}</p>`))
  }
})

test('publishes crawl files for the canonical host', async () => {
  assert.equal((await readFile(new URL('CNAME', dist), 'utf8')).trim(), 'search-console.bruniaux.com')
  assert.equal(await readFile(new URL('robots.txt', dist), 'utf8'), 'User-agent: *\nAllow: /\n\nSitemap: https://search-console.bruniaux.com/sitemap-index.xml\n')
  const sitemapFiles = (await readdir(dist)).filter((name) => /^sitemap.*\.xml$/.test(name))
  const sitemapText = (await Promise.all(sitemapFiles.map((name) => readFile(new URL(name, dist), 'utf8')))).join('\n')
  assert.match(sitemapText, /https:\/\/search-console\.bruniaux\.com\//)
  assert.match(sitemapText, /https:\/\/search-console\.bruniaux\.com\/fr\//)
  assert.match(sitemapText, /https:\/\/search-console\.bruniaux\.com\/docs\/installation\//)
  assert.match(sitemapText, /https:\/\/search-console\.bruniaux\.com\/fr\/docs\/installation\//)
  assert.doesNotMatch(sitemapText, /superpowers|machine-readable|docs\/validation/)
})

test('publishes an accessible favicon and a 1200 by 630 PNG social image', async () => {
  const favicon = await readFile(new URL('favicon.svg', dist), 'utf8')
  assert.match(favicon, /role="img"/)
  assert.match(favicon, /<title>Search Console MCP<\/title>/)
  const png = await readFile(new URL('og-image.png', dist))
  assert.deepEqual([...png.subarray(0, 8)], [137, 80, 78, 71, 13, 10, 26, 10])
  assert.equal(png.toString('ascii', 12, 16), 'IHDR')
  assert.equal(png.readUInt32BE(16), 1200)
  assert.equal(png.readUInt32BE(20), 630)
})

test('does not leak local paths or development origins', () => {
  assert.doesNotMatch(html, /\/Users\/|localhost|127\.0\.0\.1/)
})
