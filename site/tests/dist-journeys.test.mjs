import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

const dist = new URL('../dist/', import.meta.url)
const readPage = (path) => readFile(new URL(`${path}index.html`, dist), 'utf8')
const product = JSON.parse(await readFile(new URL('../src/generated/product.json', import.meta.url), 'utf8'))

for (const [prefix, folder, slugs] of [
  ['', 'for', ['site-owners', 'seo-experts', 'content-teams', 'developers']],
  ['fr/', 'pour', ['proprietaires', 'experts-seo', 'equipes-contenu', 'developpeurs']],
]) {
  test(`persona paths and catalogue are discoverable in ${prefix || 'en'}`, async () => {
    const home = await readPage(prefix)
    const sitemap = await readPage(`${prefix}sitemap/`)
    assert.ok(home.indexOf('id="real-example"') < home.indexOf('id="outcomes"'))
    const hero = home.match(/<section class="hero"[\s\S]*?<\/section>/)[0]
    assert.ok(hero.includes(`href="/${prefix}tools/"`))
    assert.ok(hero.includes(`>${product.toolCount} `))
    for (const slug of slugs) {
      const path = `${prefix}${folder}/${slug}/`
      assert.ok(home.includes(`href="/${path}"`))
      assert.ok(sitemap.includes(`href="/${path}"`))
      const html = await readPage(path)
      assert.ok(html.includes('id="guided"'))
      assert.ok(html.includes('id="details"'))
      assert.ok(html.includes('data-copy-prompt='))
      assert.ok(html.includes(`href="/${prefix}docs/installation/"`))
    }
    const catalogue = await readPage(`${prefix}tools/`)
    for (const tool of product.tools) assert.ok(catalogue.includes(`id="tool-${tool.name}"`), tool.name)
    assert.equal((catalogue.match(/class="tool-entry"/g) ?? []).length, product.toolCount)
    // Check actual rendered targets, including cross-page catalogue anchors.
    for (const path of [`${prefix}tools/`, ...slugs.map((slug) => `${prefix}${folder}/${slug}/`)]) {
      const html = await readPage(path)
      for (const [, href] of html.matchAll(/<a\b[^>]*href="([/#][^"]*)"/g)) {
        const url = new URL(href, `https://local.test/${path}`)
        const target = await readPage(url.pathname.slice(1))
        if (url.hash) assert.ok(target.includes(`id="${decodeURIComponent(url.hash.slice(1))}"`), `Broken ${path} -> ${href}`)
      }
    }
  })
}
