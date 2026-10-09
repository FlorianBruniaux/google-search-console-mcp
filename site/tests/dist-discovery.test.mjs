import assert from 'node:assert/strict'
import { existsSync } from 'node:fs'
import { readFile } from 'node:fs/promises'
import test from 'node:test'
import { publishedPages } from '../scripts/prepare-doc-content.mjs'
import { latestUpdate } from '../src/data/updates.mjs'

const dist = new URL('../dist/', import.meta.url)
const readPage = (path) => readFile(new URL(`${path}index.html`, dist), 'utf8')
const latest = latestUpdate(await readFile(new URL('../../CHANGELOG.md', import.meta.url), 'utf8'))

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
    assert.ok(html.includes(`<time datetime="${latest.date}"`), 'Latest update date must match the changelog')
    assert.match(html, /1\.4\.0/)
    const status = prefix ? /Sur main · non publié sur PyPI/ : /On main · not released on PyPI/
    if (latest.published) {
      assert.match(html, prefix ? /Cette version est disponible sur PyPI/ : /This version is available on PyPI/)
      assert.doesNotMatch(html, status)
    } else {
      assert.match(html, status)
      assert.doesNotMatch(html, prefix ? /Cette version est disponible sur PyPI/ : /This version is available on PyPI/)
    }
    assert.match(html, /1\.3\.1/)
    assert.match(html, /2026-10-08/)
    assert.match(html, /search_weekday_reference/)
    assert.match(home, /class="updates-banner"/)
    assert.ok(home.includes(`href="/${prefix}updates/"`))
    assert.ok(home.includes(`href="/${prefix}sitemap/"`))
    assert.ok(home.includes(`<time datetime="${latest.date}"`), 'Homepage update date must match the changelog')
    if (latest.published) {
      assert.ok(home.includes(`v${latest.version}`), 'Homepage release version must match the changelog')
    } else {
      assert.match(home, prefix ? /Sur main · non publié/ : /On main · unreleased/)
    }
    assert.ok(html.includes(`href="/${prefix}#install"`), 'Shared header must link to the home installation section')
    const other = prefix ? '' : 'fr/'
    assert.ok(html.includes(`href="/${other}updates/"`), 'Language switch must preserve the page')
  })
}
