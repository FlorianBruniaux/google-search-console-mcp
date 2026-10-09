import assert from 'node:assert/strict'
import { existsSync } from 'node:fs'
import { readFile, readdir } from 'node:fs/promises'
import { join, resolve } from 'node:path'
import test from 'node:test'

import { assertReviewedPublicEvidence, prepareDocumentation, publishedEvidence, publishedPages } from '../scripts/prepare-doc-content.mjs'
import { latestUpdate, formatUpdateDate } from '../src/data/updates.mjs'

const siteRoot = resolve(import.meta.dirname, '..')
const generatedRoot = join(siteRoot, 'src/content/docs')

test('update banner follows dated source changes and falls back to the latest published release', () => {
  assert.deepEqual(latestUpdate('## [Unreleased]\n\n<!-- unreleased-updated: 2026-10-09 -->\n\n- A source change.\n\n## [1.3.1] - 2026-10-08\n\n- A release.'), { date: '2026-10-09', version: null, published: false })
  assert.deepEqual(latestUpdate('## [Unreleased]\n\n<!-- unreleased-updated: 2026-10-09 -->\n\n## [1.4.0] - 2026-10-12\n\n- A release.'), { date: '2026-10-12', version: '1.4.0', published: true })
  assert.throws(() => latestUpdate('## [Unreleased]\n\n- Undated changes.\n\n## [1.3.1] - 2026-10-08'), /requires a valid/)
  assert.throws(() => latestUpdate('## [Unreleased]\n\n<!-- unreleased-updated: 2026-02-30 -->\n\n- Wrong date.'), /requires a valid/)
  assert.equal(formatUpdateDate('2026-10-09', 'fr'), '9 octobre 2026')
  assert.equal(formatUpdateDate('2026-10-09', 'en'), '9 October 2026')
})

test('blocks unreviewed data additions to the public MCP snapshot before publication', async () => {
  const [sourcePath, , approvedDigest] = publishedEvidence[0]
  const source = await readFile(join(siteRoot, '..', sourcePath), 'utf8')
  assert.doesNotThrow(() => assertReviewedPublicEvidence(source, approvedDigest))
  for (const extra of [
    { access_token: 'synthetic-test-token' },
    { properties: [{ url: 'sc-domain:private.example.invalid', permission: 'siteOwner' }] },
    { extraQuery: 'synthetic private customer query' },
  ]) {
    const changed = JSON.stringify({ ...JSON.parse(source), ...extra })
    assert.throws(() => assertReviewedPublicEvidence(changed, approvedDigest), /privacy review/)
  }
  const changedValue = JSON.parse(source)
  changedValue.calls[0].response.tools[0] = 'synthetic-test-token'
  assert.throws(() => assertReviewedPublicEvidence(JSON.stringify(changedValue), approvedDigest), /privacy review/)
})

test('the real run keeps derived totals tied to live tool responses and exposes only selected properties', async () => {
  const file = join(siteRoot, '../examples/evidence/2026-10-07-cc-guide.json')
  const source = await readFile(file, 'utf8')
  const trace = JSON.parse(source)
  assert.equal(trace.callCount, trace.calls.length)
  assert.equal(new Set(trace.calls.map((call) => call.seq)).size, trace.calls.length)
  const current = trace.calls.find((call) => call.tool === 'get_advanced_search_analytics').response.rows[0]
  const periods = trace.calls.find((call) => call.tool === 'compare_search_periods').response
  assert.equal(trace.summary.current.clicks, current.clicks)
  assert.equal(trace.summary.current.impressions, current.impressions)
  assert.deepEqual(trace.summary.previous, periods.period_a)
  assert.equal(trace.summary.derived.clickChangePct, Math.round((current.clicks - periods.period_a.clicks) / periods.period_a.clicks * 10000) / 100)
  assert.equal(trace.summary.derived.currentCtrPct, Math.round(current.clicks / current.impressions * 10000) / 100)
  assert.equal(trace.scope.changesApplied, false)
  assert.equal(trace.scope.rankingImpactMeasured, false)
  const properties = trace.calls.find((call) => call.tool === 'list_properties').response.properties
  assert.deepEqual(properties.map((property) => property.url), [trace.site])
  assert.deepEqual(properties.map((property) => Object.keys(property)), [['url']])
  const queries = trace.calls.find((call) => call.tool === 'get_search_by_page_query').response.rows.map((row) => row.query)
  assert.deepEqual(queries.sort(), ['claude code latest version', 'latest claude code version', 'lean ctx vs rtk', 'lean-ctx vs rtk'].sort())
  assert.doesNotMatch(source, /credential_env_declared|siteOwner|rawLogSha256|repositoryHead|repositoryState|\.claudedocs|"_meta"|"top_queries"/)
  assert.doesNotMatch(source, /\/Users\/|Bearer [A-Za-z0-9]|AIza|-----BEGIN PRIVATE KEY-----/)
  await prepareDocumentation()
  assert.equal(await readFile(join(siteRoot, 'public/evidence/2026-10-07-cc-guide.json'), 'utf8'), source)
})

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
  const workflows = await readFile(join(generatedRoot, 'docs/audit-workflows.md'), 'utf8')
  assert.match(workflows, /https:\/\/github\.com\/FlorianBruniaux\/google-search-console-mcp\/blob\/main\/docs\/crawl-log-audit\.md/)
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
