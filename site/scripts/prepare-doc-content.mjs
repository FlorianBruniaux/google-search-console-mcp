import { createHash } from 'node:crypto'
import { existsSync } from 'node:fs'
import { mkdir, readFile, readdir, rm, writeFile } from 'node:fs/promises'
import { dirname, join, relative, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const scriptDirectory = dirname(fileURLToPath(import.meta.url))
const siteRoot = resolve(scriptDirectory, '..')
const repositoryRoot = resolve(siteRoot, '..')
const generatedRoot = join(siteRoot, 'src/content/docs')

export const publishedPages = [
  ['site/content/en/index.md', 'docs/index.md', 'Search Console MCP documentation', 'Install, connect search providers, run bounded audits, and interpret evidence safely.'],
  ['docs/installation.md', 'docs/installation.md', 'Installation and MCP client setup', 'Install Search Console MCP once, connect a compatible client, and avoid duplicate server processes.'],
  ['docs/google-setup.md', 'docs/google-setup.md', 'Google credentials setup', 'Configure Google Search Console and the optional Google data providers.'],
  ['docs/bing-setup.md', 'docs/bing-setup.md', 'Bing Webmaster Tools setup', 'Configure Bing Webmaster Tools and keep the account API key separate from IndexNow.'],
  ['docs/starter-prompt.md', 'docs/prompts.md', 'Starter prompts', 'Begin with bounded prompts for common search performance and technical SEO questions.'],
  ['examples/README.md', 'docs/examples/index.md', 'Example workflows', 'Choose a ready-to-use workflow for audits, traffic changes, indexing, or content planning.'],
  ['examples/quick-audit.md', 'docs/examples/quick-audit.md', 'Quick site health check', 'Run a bounded first-pass search and technical health check.'],
  ['examples/google-bing-comparison.md', 'docs/examples/google-bing-comparison.md', 'Google and Bing comparison', 'Compare provider evidence without merging incompatible metrics.'],
  ['examples/full-audit.md', 'docs/examples/full-audit.md', 'Full SEO audit', 'Run a structured multi-source audit with explicit evidence boundaries.'],
  ['examples/keyword-opportunities.md', 'docs/examples/keyword-opportunities.md', 'Keyword opportunities', 'Find query opportunities from observed search performance.'],
  ['examples/page-deep-dive.md', 'docs/examples/page-deep-dive.md', 'Page deep dive', 'Inspect one page across performance, indexation, and public-page signals.'],
  ['examples/traffic-drop.md', 'docs/examples/traffic-drop.md', 'Traffic drop investigation', 'Investigate a traffic change with comparable windows and explicit uncertainty.'],
  ['examples/indexing-issues.md', 'docs/examples/indexing-issues.md', 'Indexing issues', 'Separate submitted, crawled, and indexed states before taking action.'],
  ['examples/content-brief.md', 'docs/examples/content-brief.md', 'Content brief from search data', 'Build a content brief from observed queries and pages.'],
  ['docs/architecture.md', 'docs/architecture.md', 'Architecture', 'Understand the MCP server, provider boundaries, and guarded write operations.'],
  ['site/content/en/evidence-and-safety.md', 'docs/evidence-and-safety.md', 'Evidence and safety', 'Read results without confusing observed, derived, requested, crawled, and indexed states.'],
  ['CHANGELOG.md', 'docs/changelog.md', 'Changelog', 'Review the canonical release history for Search Console MCP.'],
  ['LICENSE', 'docs/license.md', 'MIT license', 'Read the project license and its usage boundary.'],
]

const routeBySource = new Map(publishedPages.map(([source, target]) => [source, `/${target.replace(/index\.md$/, '').replace(/\.md$/, '/')}`]))
const blockedSegments = ['docs/superpowers/', 'docs/machine-readable/', 'docs/validation/']

function sourceHash(content) {
  return createHash('sha256').update(content.replaceAll('\r\n', '\n')).digest('hex')
}

function removeFirstHeading(content) {
  return content.replace(/^#\s+[^\n]+\n+/, '')
}

function rewriteEnglishLinks(content, sourcePath) {
  return content.replace(/\]\(([^)#]+\.md)(#[^)]+)?\)/g, (_match, href, anchor = '') => {
    const absoluteSource = resolve(repositoryRoot, dirname(sourcePath), href)
    const repositoryPath = relative(repositoryRoot, absoluteSource).replaceAll('\\', '/')
    const publicRoute = routeBySource.get(repositoryPath)
    if (!publicRoute) {
      throw new Error(`Unmapped internal Markdown link in ${sourcePath}: ${href}`)
    }
    return `](${publicRoute}${anchor})`
  })
}

function frontmatter(title, description, canonicalSource) {
  return [
    '---',
    `title: ${JSON.stringify(title)}`,
    `description: ${JSON.stringify(description)}`,
    `canonicalSource: ${JSON.stringify(canonicalSource)}`,
    '---',
    '',
  ].join('\n')
}

async function writePage(target, content) {
  const path = join(generatedRoot, target)
  await mkdir(dirname(path), { recursive: true })
  if (existsSync(path) && await readFile(path, 'utf8') === content) return
  await writeFile(path, content)
}

async function prepareEnglish() {
  for (const [source, target, title, description] of publishedPages) {
    if (blockedSegments.some((segment) => source.startsWith(segment))) {
      throw new Error(`Blocked source cannot be published: ${source}`)
    }
    const sourcePath = join(repositoryRoot, source)
    if (!existsSync(sourcePath)) throw new Error(`Missing documentation source: ${source}`)
    const raw = await readFile(sourcePath, 'utf8')
    const body = rewriteEnglishLinks(removeFirstHeading(raw), source)
    await writePage(target, `${frontmatter(title, description, source)}${body.trim()}\n`)
  }
}

async function prepareFrench({ verifyTranslations = false } = {}) {
  const manifestPath = join(siteRoot, 'content/fr/manifest.json')
  if (!existsSync(manifestPath)) throw new Error('Missing French translation manifest')
  const manifest = JSON.parse(await readFile(manifestPath, 'utf8'))
  const expectedRoutes = new Set(publishedPages.map(([, target]) => target))
  const actualRoutes = new Set(Object.keys(manifest.pages))
  const missingRoutes = [...expectedRoutes].filter((route) => !actualRoutes.has(route))
  const extraRoutes = [...actualRoutes].filter((route) => !expectedRoutes.has(route))
  if (missingRoutes.length || extraRoutes.length) {
    throw new Error(`French route manifest mismatch. Missing: ${missingRoutes.join(', ') || 'none'}. Extra: ${extraRoutes.join(', ') || 'none'}.`)
  }

  const stale = []
  for (const [route, metadata] of Object.entries(manifest.pages)) {
    const frenchPath = join(siteRoot, 'content/fr', route)
    const canonicalPath = join(repositoryRoot, metadata.source)
    if (!existsSync(frenchPath)) throw new Error(`Missing French page: site/content/fr/${route}`)
    if (!existsSync(canonicalPath)) throw new Error(`Missing canonical source for ${route}: ${metadata.source}`)
    const canonical = await readFile(canonicalPath, 'utf8')
    const currentHash = sourceHash(canonical)
    if (metadata.sourceHash !== currentHash) stale.push(`${route} <= ${metadata.source}`)
    const french = await readFile(frenchPath, 'utf8')
    if (!/canonicalEnglish:\s*["']?\/docs\//.test(french)) {
      throw new Error(`French page lacks canonicalEnglish metadata: ${route}`)
    }
    await writePage(`fr/${route}`, french.trimEnd() + '\n')
  }

  if (stale.length) {
    const message = `Stale French translations:\n- ${stale.join('\n- ')}`
    if (verifyTranslations) throw new Error(message)
    console.warn(message)
  }
}

async function assertPublicationBoundary() {
  const files = await readdir(generatedRoot, { recursive: true })
  const leaked = files.filter((file) => blockedSegments.some((segment) => file.includes(segment)))
  if (leaked.length) throw new Error(`Internal documentation leaked into generated content: ${leaked.join(', ')}`)
}

async function removeUnexpectedGeneratedFiles() {
  const expected = new Set(publishedPages.flatMap(([, target]) => [target, `fr/${target}`]))
  const files = await readdir(generatedRoot, { recursive: true })
  for (const file of files) {
    if (file.endsWith('.md') && !expected.has(file)) {
      await rm(join(generatedRoot, file), { force: true })
    }
  }
}

export async function prepareDocumentation(options = {}) {
  await mkdir(generatedRoot, { recursive: true })
  await removeUnexpectedGeneratedFiles()
  await prepareEnglish()
  await prepareFrench(options)
  await assertPublicationBoundary()
  console.log(`Prepared ${publishedPages.length * 2} documentation pages.`)
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  prepareDocumentation({ verifyTranslations: process.argv.includes('--verify-translations') }).catch((error) => {
    console.error(error.message)
    process.exitCode = 1
  })
}
