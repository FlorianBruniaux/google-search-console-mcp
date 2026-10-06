import assert from 'node:assert/strict'
import { existsSync } from 'node:fs'
import { readFile, readdir } from 'node:fs/promises'
import { join, resolve } from 'node:path'
import test from 'node:test'

import { prepareDocumentation, publishedPages } from '../scripts/prepare-doc-content.mjs'

const siteRoot = resolve(import.meta.dirname, '..')
const generatedRoot = join(siteRoot, 'src/content/docs')

test('publishes only the explicit bilingual route set', async () => {
  await prepareDocumentation()
  const files = (await readdir(generatedRoot, { recursive: true })).filter((file) => file.endsWith('.md'))
  assert.equal(files.length, publishedPages.length * 2)
  for (const [, route] of publishedPages) {
    assert.ok(existsSync(join(generatedRoot, route)), `missing English route ${route}`)
    assert.ok(existsSync(join(generatedRoot, 'fr', route)), `missing French route ${route}`)
  }
  assert.equal(files.some((file) => /superpowers|machine-readable|validation/.test(file)), false)
})

test('generated pages expose Starlight metadata and public links', async () => {
  await prepareDocumentation()
  const english = await readFile(join(generatedRoot, 'docs/examples/index.md'), 'utf8')
  const french = await readFile(join(generatedRoot, 'fr/docs/index.md'), 'utf8')
  assert.match(english, /^---\ntitle:/)
  assert.match(english, /\/docs\/installation\//)
  assert.match(french, /lang: fr/)
  assert.match(french, /canonicalEnglish: \/docs\//)
})

test('ships exactly two documented WebP illustrations with accessible captions', async () => {
  const visuals = ['search-evidence-map.webp', 'guarded-action-loop.webp']
  const imageRoot = join(siteRoot, 'public/images/docs')

  for (const visual of visuals) {
    const bytes = await readFile(join(imageRoot, visual))
    assert.equal(bytes.subarray(0, 4).toString('ascii'), 'RIFF')
    assert.equal(bytes.subarray(8, 12).toString('ascii'), 'WEBP')
  }

  const englishHome = await readFile(join(siteRoot, 'content/en/index.md'), 'utf8')
  const englishSafety = await readFile(join(siteRoot, 'content/en/evidence-and-safety.md'), 'utf8')
  const frenchHome = await readFile(join(siteRoot, 'content/fr/docs/index.md'), 'utf8')
  const frenchSafety = await readFile(join(siteRoot, 'content/fr/docs/evidence-and-safety.md'), 'utf8')

  for (const [source, visual] of [
    [englishHome, visuals[0]],
    [englishSafety, visuals[1]],
    [frenchHome, visuals[0]],
    [frenchSafety, visuals[1]],
  ]) {
    assert.match(source, new RegExp(`<img[^>]+src="/images/docs/${visual}"[^>]+alt="[^"]+"`))
    assert.match(source, /<figcaption>[^<]+<\/figcaption>/)
  }
})
