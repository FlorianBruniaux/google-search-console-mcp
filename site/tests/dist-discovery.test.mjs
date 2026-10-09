import assert from 'node:assert/strict'
import { existsSync } from 'node:fs'
import { readFile } from 'node:fs/promises'
import test from 'node:test'
import { publishedPages } from '../scripts/prepare-doc-content.mjs'

const dist = new URL('../dist/', import.meta.url)
const readPage = (path) => readFile(new URL(`${path}index.html`, dist), 'utf8')

for (const prefix of ['', 'fr/']) {
  test(`HTML sitemap lists every published documentation page in ${prefix || 'English'}`, async () => {
    assert.ok(existsSync(new URL(`${prefix}sitemap/index.html`, dist)), 'HTML sitemap must be published')
    const html = await readPage(`${prefix}sitemap/`)
    for (const [, target] of publishedPages) {
      const path = target.replace(/index\.md$/, '').replace(/\.md$/, '/')
      assert.ok(html.includes(`href="/${prefix}${path}"`), `Missing ${prefix}${path}`)
    }
    for (const path of ['', 'sitemap/', 'updates/']) {
      assert.ok(html.includes(`href="/${prefix}${path}"`))
    }
    assert.doesNotMatch(html, /docs\/superpowers|docs\/validation|machine-readable/)
  })

  test(`dated updates preserve release status and are discoverable in ${prefix || 'English'}`, async () => {
    assert.ok(existsSync(new URL(`${prefix}updates/index.html`, dist)), 'Updates must be published')
    const html = await readPage(`${prefix}updates/`)
    const home = await readPage(prefix)
    assert.match(html, /<time datetime="2026-10-09"/)
    assert.match(html, prefix ? /Non publié/ : /Unreleased/)
    assert.match(html, /1\.3\.1/)
    assert.match(html, /2026-10-08/)
    assert.match(html, /search_weekday_reference/)
    assert.match(home, /class="updates-banner"/)
    assert.ok(home.includes(`href="/${prefix}updates/"`))
    assert.ok(home.includes(`href="/${prefix}sitemap/"`))
    assert.match(home, /<time datetime="2026-10-09"/)
    assert.ok(html.includes(`href="/${prefix}#install"`), 'Shared header must link to the home installation section')
    const other = prefix ? '' : 'fr/'
    assert.ok(html.includes(`href="/${other}updates/"`), 'Language switch must preserve the page')
  })
}
