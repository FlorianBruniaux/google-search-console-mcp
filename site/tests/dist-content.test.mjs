import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

const html = await readFile(new URL('../dist/index.html', import.meta.url), 'utf8')
const product = JSON.parse(await readFile(new URL('../src/generated/product.json', import.meta.url), 'utf8'))

test('renders the product name and generated facts', () => {
  assert.match(html, /Search Console MCP/)
  assert.match(html, new RegExp(`${product.toolCount} MCP tools`))
  assert.match(html, new RegExp(`Version ${product.version.replaceAll('.', '\\.')}`))
  assert.match(html, new RegExp(`Python ${product.pythonRequires.replace('>', '&gt;')}`))
})
