import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

const html = await readFile(new URL('../dist/index.html', import.meta.url), 'utf8')
const docsHtml = await readFile(new URL('../dist/docs/index.html', import.meta.url), 'utf8')
const docsFrHtml = await readFile(new URL('../dist/fr/docs/index.html', import.meta.url), 'utf8')
const product = JSON.parse(await readFile(new URL('../src/generated/product.json', import.meta.url), 'utf8'))

test('renders the product name and generated tool count', () => {
  assert.match(html, /Search Console MCP/)
  assert.match(html, new RegExp(`${product.toolCount} MCP tools`))
})

test('shows Florian Bruniaux’s monogram in the home wordmark', () => {
  const wordmark = html.match(/<a\b[^>]*class="wordmark"[^>]*>[\s\S]*?<\/a>/)?.[0]
  assert.ok(wordmark, 'Missing home wordmark')
  assert.match(wordmark, /<span class="creator-mark" aria-hidden="true">FB<span>\.<\/span><\/span>/)
  assert.doesNotMatch(wordmark, /<img\b/)
  assert.match(wordmark, /Search Console MCP/)
})

test('shows the four approved product facts', () => {
  const proofList = html.match(/<ul\b[^>]*aria-label="Package facts"[^>]*>([\s\S]*?)<\/ul>/)?.[1]
  assert.ok(proofList, 'Missing package facts list')
  const facts = [...proofList.matchAll(/<strong>([^<]+)<\/strong>/g)].map((match) => match[1])
  assert.deepEqual(facts, [`${product.toolCount} MCP tools`, 'Google + Bing', 'Structured JSON', 'Guarded writes'])
})

test('offers the approved install actions and intent shortcuts', () => {
  assert.match(html, /<a\b[^>]*class="header-install"[^>]*href="#install"/)
  assert.match(html, />Copy uvx command<\/button>/)
  for (const [label, href] of [
    ['Compare Google and Bing', '#capabilities'],
    ['Diagnose indexing', '#safety'],
    ['Audit a public page', '#provider-public'],
  ]) {
    assert.match(html, new RegExp(`<a\\b[^>]*href="${href}"[^>]*>${label}`))
  }
})

test('keeps documentation reading paths on the public site', () => {
  for (const href of [
    '/docs/',
    '/fr/docs/',
    '/docs/installation/',
    '/docs/google-setup/',
    '/docs/bing-setup/',
    '/docs/prompts/',
    '/docs/changelog/',
    '/docs/architecture/',
    '/docs/evidence-and-safety/',
    '/docs/license/',
  ]) assert.ok(html.includes(`href="${href}"`), `Missing public documentation link: ${href}`)

  assert.doesNotMatch(html, /<a\b[^>]*href="https:\/\/github\.com\/FlorianBruniaux\/google-search-console-mcp\/(?:blob|tree)\/main\/(?:docs|examples|CHANGELOG|LICENSE)/)
})

test('publishes paired English and French documentation homes', () => {
  assert.match(docsHtml, /<html lang="en"/)
  assert.match(docsFrHtml, /<html lang="fr"/)
  assert.match(docsHtml, /rel="alternate" hreflang="fr" href="https:\/\/search-console\.bruniaux\.com\/fr\/docs\/"/)
  assert.match(docsFrHtml, /rel="alternate" hreflang="en" href="https:\/\/search-console\.bruniaux\.com\/docs\/"/)
  assert.match(docsHtml, /search-evidence-map\.webp/)
  assert.match(docsFrHtml, /Trois flux de preuves séparés/)
})

test('renders local copy feedback for every command and a final install call to action', () => {
  assert.equal((html.match(/data-copy-command=/g) ?? []).length, 5)
  assert.equal((html.match(/data-copy-status/g) ?? []).length, 5)
  assert.match(html, /Expected: the registered commands and their one-line descriptions\./)
  const finalInstall = html.match(/<section\b[^>]*id="final-install"[\s\S]*?<\/section>/)?.[0]
  assert.ok(finalInstall, 'Missing final installation call to action')
  assert.match(finalInstall, /uvx gsc-mcp-tools/)
  assert.match(finalInstall, /installation guide/i)
  assert.ok(html.indexOf('id="final-install"') < html.indexOf('<footer'), 'Final CTA must precede the footer')
})

test('renders every product section and provider boundary', () => {
  for (const id of ['capabilities', 'workflow', 'install', 'safety', 'faq']) {
    assert.match(html, new RegExp(`id="${id}"`))
  }
  for (const provider of ['Google data', 'Bing data', 'Public-page analysis']) {
    assert.match(html, new RegExp(provider))
  }
})

test('renders the intent menu without unsupported controls', () => {
  for (const label of ['Analyze', 'Start', 'Resources', 'Search providers', 'Workflow', 'Install', 'Configure providers', 'Project', 'Trust &amp; documentation']) {
    assert.match(html, new RegExp(label))
  }
  assert.doesNotMatch(html, /Search \(Cmd\+K\)|Latest:/)
})

test('keeps crawl and indexation claims bounded', () => {
  assert.match(html, /accepted submission proves neither crawl nor indexation/i)
  assert.match(html, /Google and Bing position semantics remain separate/i)
})

test('renders all visible FAQ questions', () => {
  for (const question of [
    'Does one Bing API key work for every site?',
    'Do I need every Google API enabled?',
    'Does a successful submission mean the page is indexed?',
    'Can I use the server from Claude and Codex?',
    'Where do credentials live?',
  ]) assert.ok(html.includes(question), `Missing FAQ: ${question}`)
  assert.equal((html.match(/data-faq-item/g) ?? []).length, 5)
})

test('resolves every local navigation destination to a unique rendered target', () => {
  const ids = [...html.matchAll(/\bid="([^"]+)"/g)].map((match) => match[1])
  assert.equal(new Set(ids).size, ids.length, 'Duplicate document IDs')
  for (const id of ['provider-google', 'provider-bing', 'provider-public', 'install-evaluate', 'install-persistent', 'install-verify']) {
    assert.ok(ids.includes(id), `Missing target: ${id}`)
  }
  for (const [, target] of html.matchAll(/href="#([^"]+)"/g)) {
    assert.ok(ids.includes(target), `Broken anchor: #${target}`)
  }
})

test('exposes semantic navigation controls and copy feedback for client behavior', () => {
  assert.match(html, /<a[^>]+href="#main-content"/)
  assert.match(html, /<div[^>]+id="primary-navigation"/)
  assert.match(html, /<nav[^>]+aria-label="Primary navigation"/)
  for (const section of ['analyze', 'start', 'resources']) {
    assert.match(html, new RegExp(`<details[^>]+data-nav-section="${section}"`))
    assert.match(html, new RegExp(`aria-controls="nav-panel-${section}"`))
    assert.match(html, new RegExp(`id="nav-panel-${section}"`))
  }
  assert.match(html, /id="mobile-menu-toggle"[^>]+aria-controls="primary-navigation"/)
  assert.match(html, /data-mobile-menu-close/)
  assert.match(html, /data-nav-backdrop[^>]*hidden/)
  assert.match(html, /data-copy-command="uvx gsc-mcp-tools"/)
  assert.match(html, /data-copy-status[^>]+role="status"[^>]+aria-live="polite"/)
})

test('connects the footer to the product and Florian Bruniaux ecosystem', () => {
  for (const label of ['Navigate', 'Product', 'Ecosystem']) {
    assert.match(html, new RegExp(`<nav[^>]+aria-label="${label} links"`))
  }

  for (const href of ['#main-content', '#capabilities', '#workflow', '#install', '#safety', '#faq']) {
    assert.match(html, new RegExp(`href="${href}"`), `Missing internal footer link: ${href}`)
  }

  for (const href of [
    'https://github.com/FlorianBruniaux/google-search-console-mcp',
    'https://pypi.org/project/gsc-mcp-tools/',
    'https://www.florian.bruniaux.com/projects/',
    'https://cc.bruniaux.com/',
    'https://starmapper.bruniaux.com/',
    'https://ccboard.bruniaux.com/',
    'https://ccbridge.bruniaux.com/',
    'https://github.com/FlorianBruniaux/youtube-video-insights',
    'https://www.florian.bruniaux.com/',
    'https://www.florian.bruniaux.com/blog/',
    'https://github.com/FlorianBruniaux',
    'https://www.linkedin.com/in/florian-bruniaux-43408b83/',
  ]) {
    assert.ok(html.includes(`href="${href}`), `Missing external footer link: ${href}`)
  }
})
