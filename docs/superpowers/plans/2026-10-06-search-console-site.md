# Search Console MCP Website Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and publish a one-page Astro website for Search Console MCP at `https://search-console.bruniaux.com/` without coupling the site release to PyPI publishing.

**Architecture:** The Astro application lives in `site/` and produces static files for GitHub Pages. A Python exporter reads package metadata and the central tool registry before every development, check and build command, so changing product facts are never copied into page source. A separate Pages workflow installs the Python package and locked Node dependencies, verifies the site, records the deployed commit and uploads only `site/dist`.

**Tech Stack:** Python 3.11, pytest, Astro 5.17, TypeScript 5.9, pnpm 9, Node.js 22, native CSS, Playwright, axe-core, GitHub Pages.

**Spec:** `docs/superpowers/specs/2026-10-06-search-console-site-design.md`

## Global Constraints

- Keep the site in `site/` inside `FlorianBruniaux/google-search-console-mcp`.
- Use `https://search-console.bruniaux.com/` as Astro `site` and `/` as `base`.
- Use **Search Console MCP** as the public name and `gsc-mcp-tools` as the package name.
- Keep `.github/workflows/publish.yml` unchanged.
- Use Astro static output, native CSS and minimal browser JavaScript. Do not add React, Vue, Tailwind, Starlight or a web font.
- Generate `version`, `toolCount`, `pythonRequires`, package name and repository URL from `pyproject.toml` plus `src/gsc_mcp/registry.py`.
- Fail the build if product data cannot be generated or validated.
- Keep Google and Bing metrics provider-specific. Do not claim that position semantics are interchangeable.
- State that an accepted submission proves neither crawl nor indexation.
- Never expose Google, Bing, GA4, CrUX or IndexNow credentials to Astro, browser JavaScript or GitHub Pages.
- Follow the BoldGuy palette and layout from the approved spec. Provider colors may label provider sections but must not replace orange as the product accent.
- Verify 390 by 844 and 1440 by 1000 in light and dark modes.
- Do not update README or package homepage links to the custom domain until the public URL returns the intended commit.
- Preserve `.agents/handoffs/2026-10-05-164757-bing-provider-execution.md` and `docs/superpowers/plans/2026-09-05-bing-webmaster-provider.md`; they are unrelated untracked work.

## Review Focus

1. A malformed `pyproject.toml` or missing project field must fail the exporter without leaving a partial JSON file. Task 1 tests both conditions.
2. An empty or non-dictionary `TOOLS` registry must fail the exporter instead of publishing a zero-tool claim. Task 1 tests both shapes.
3. Clipboard permission rejection must leave the command visible and announce a manual-copy fallback. Task 4 tests the rejected browser API.
4. Missing or inaccessible `localStorage` must not block first paint or theme switching. Task 4 tests the operating-system fallback and a storage exception.
5. At 390 px, navigation, buttons and disclosures must remain keyboard-operable, at least 44 px high and free of document-level horizontal overflow. Task 4 tests all three conditions.

---

## File Map

### Python and generated data

- `site/scripts/export-product-data.py`: deterministic CLI that reads repository product facts and atomically writes JSON.
- `tests/test_site_product_data.py`: subprocess contract tests for success, determinism and fail-closed behavior.
- `site/src/generated/product.json`: build output consumed by Astro and ignored by Git.
- `.gitignore`: ignores the generated JSON, Astro cache, site build output and Playwright reports.

### Astro application

- `site/package.json`: scripts and JavaScript dependencies.
- `site/pnpm-lock.yaml`: exact Node dependency graph.
- `site/tsconfig.json`: Astro strict TypeScript configuration.
- `site/astro.config.mjs`: static site URL, trailing slash and sitemap integration.
- `site/src/data/content.ts`: stable copy, links, provider groups, workflow, evidence states and FAQ.
- `site/src/layouts/BaseLayout.astro`: document shell, metadata, pre-paint theme boot and structured-data slots.
- `site/src/pages/index.astro`: one-page composition only.
- `site/src/components/SiteHeader.astro`: skip link, fixed navigation and theme toggle.
- `site/src/components/Hero.astro`: product proposition, command action and terminal proof surface.
- `site/src/components/ProofStrip.astro`: generated facts.
- `site/src/components/ProviderCoverage.astro`: Google, Bing and public-page boundaries.
- `site/src/components/Workflow.astro`: semantic five-step flow.
- `site/src/components/InstallPath.astro`: evaluation, persistent installation and provider setup links.
- `site/src/components/EvidenceSafety.astro`: observed, derived and requested states.
- `site/src/components/Faq.astro`: visible questions and answers used by JSON-LD.
- `site/src/components/SiteFooter.astro`: repository, PyPI, documentation, license and author links.
- `site/src/scripts/interactions.ts`: copy command and theme switch behavior.
- `site/src/styles/global.css`: BoldGuy tokens, layout, responsive states, focus and reduced motion.

### Public and verification assets

- `site/public/CNAME`: custom GitHub Pages hostname.
- `site/public/favicon.svg`: repository-owned product mark.
- `site/public/og-image.png`: 1200 by 630 social image.
- `site/public/robots.txt`: sitemap declaration.
- `site/tests/dist-content.test.mjs`: built content and evidence-boundary assertions.
- `site/tests/dist-seo.test.mjs`: metadata, structured data, sitemap and public-file assertions.
- `site/tests/site.spec.ts`: Playwright behavior, accessibility, responsive and visual tests.
- `site/playwright.config.ts`: Chromium and preview-server configuration.
- `site/tests/site.spec.ts-snapshots/`: four reviewed visual baselines.

### Delivery

- `.github/workflows/site.yml`: isolated Pages build and deploy workflow.
- `tests/test_site_workflow.py`: structural workflow boundary tests.
- `README.md`: public site entry point added only after deployment verification.
- `pyproject.toml`: homepage URL changed only after deployment verification.

---

### Task 1: Deterministic Product Data Export

**Files:**
- Create: `site/scripts/export-product-data.py`
- Create: `tests/test_site_product_data.py`
- Modify: `.gitignore`

**Interfaces:**
- Consumes: `[project]` and `[project.urls]` from repository `pyproject.toml`; `TOOLS: dict[str, Callable[..., str]]` from `src/gsc_mcp/registry.py`.
- Produces: UTF-8 JSON at `site/src/generated/product.json` with `package: str`, `version: str`, `toolCount: int`, `pythonRequires: str`, `repository: str`.

- [ ] **Step 1: Add fail-closed exporter tests**

Create `tests/test_site_product_data.py` with subprocess helpers so every run imports a fresh registry:

```python
import json
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

from gsc_mcp.registry import TOOLS


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "site" / "scripts" / "export-product-data.py"


def run_export(pyproject: Path, source_root: Path, output: Path):
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--pyproject",
            str(pyproject),
            "--source-root",
            str(source_root),
            "--output",
            str(output),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def write_fake_source(root: Path, registry_value: str) -> Path:
    package = root / "gsc_mcp"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "registry.py").write_text(
        f"TOOLS = {registry_value}\n",
        encoding="utf-8",
    )
    return root


def write_pyproject(path: Path, *, include_repository: bool = True) -> Path:
    repository = (
        '\n[project.urls]\nRepository = "https://github.com/example/project"\n'
        if include_repository
        else ""
    )
    path.write_text(
        '[project]\nname = "gsc-mcp-tools"\nversion = "1.2.0"\n'
        'requires-python = ">=3.11"\n'
        + repository,
        encoding="utf-8",
    )
    return path


def test_export_matches_repository_sources(tmp_path):
    output = tmp_path / "product.json"
    result = run_export(REPO_ROOT / "pyproject.toml", REPO_ROOT / "src", output)

    assert result.returncode == 0, result.stderr
    payload = json.loads(output.read_text(encoding="utf-8"))
    project = tomllib.loads(
        (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    )["project"]
    assert payload == {
        "package": project["name"],
        "pythonRequires": project["requires-python"],
        "repository": project["urls"]["Repository"],
        "toolCount": len(TOOLS),
        "version": project["version"],
    }


def test_export_is_byte_deterministic(tmp_path):
    output = tmp_path / "product.json"
    first = run_export(REPO_ROOT / "pyproject.toml", REPO_ROOT / "src", output)
    first_bytes = output.read_bytes()
    second = run_export(REPO_ROOT / "pyproject.toml", REPO_ROOT / "src", output)

    assert first.returncode == second.returncode == 0
    assert output.read_bytes() == first_bytes


@pytest.mark.parametrize("registry_value", ["{}", "[]"])
def test_export_refuses_invalid_registry(tmp_path, registry_value):
    pyproject = write_pyproject(tmp_path / "pyproject.toml")
    source_root = write_fake_source(tmp_path / "src", registry_value)
    output = tmp_path / "product.json"

    result = run_export(pyproject, source_root, output)

    assert result.returncode != 0
    assert "TOOLS must be a non-empty dictionary" in result.stderr
    assert not output.exists()


def test_export_refuses_missing_repository_without_partial_file(tmp_path):
    pyproject = write_pyproject(tmp_path / "pyproject.toml", include_repository=False)
    source_root = write_fake_source(tmp_path / "src", '{"example": object()}')
    output = tmp_path / "product.json"

    result = run_export(pyproject, source_root, output)

    assert result.returncode != 0
    assert "project.urls.Repository" in result.stderr
    assert not output.exists()


def test_export_refuses_malformed_pyproject_without_partial_file(tmp_path):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[project\nname = broken", encoding="utf-8")
    source_root = write_fake_source(tmp_path / "src", '{"example": object()}')
    output = tmp_path / "product.json"

    result = run_export(pyproject, source_root, output)

    assert result.returncode != 0
    assert "product data export failed" in result.stderr
    assert not output.exists()
```

- [ ] **Step 2: Run the tests and confirm the exporter is absent**

Run: `pytest tests/test_site_product_data.py -q`

Expected: failures identify the missing `site/scripts/export-product-data.py`.

- [ ] **Step 3: Implement the exporter with atomic output**

Create `site/scripts/export-product-data.py`:

```python
#!/usr/bin/env python3
import argparse
import importlib
import json
import os
import sys
import tempfile
import tomllib
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]


def require_string(mapping: dict[str, Any], key: str, label: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value


def load_registry(source_root: Path) -> dict[str, Any]:
    sys.path.insert(0, str(source_root.resolve()))
    try:
        registry = importlib.import_module("gsc_mcp.registry")
    finally:
        sys.path.pop(0)
    tools = getattr(registry, "TOOLS", None)
    if not isinstance(tools, dict) or not tools:
        raise ValueError("TOOLS must be a non-empty dictionary")
    return tools


def build_payload(pyproject_path: Path, source_root: Path) -> dict[str, Any]:
    document = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    project = document.get("project")
    if not isinstance(project, dict):
        raise ValueError("project must be a table")
    urls = project.get("urls")
    if not isinstance(urls, dict):
        raise ValueError("project.urls.Repository must be a non-empty string")

    return {
        "package": require_string(project, "name", "project.name"),
        "pythonRequires": require_string(
            project, "requires-python", "project.requires-python"
        ),
        "repository": require_string(
            urls, "Repository", "project.urls.Repository"
        ),
        "toolCount": len(load_registry(source_root)),
        "version": require_string(project, "version", "project.version"),
    }


def write_atomic(output: Path, payload: dict[str, Any]) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    descriptor, temporary_name = tempfile.mkstemp(
        dir=output.parent,
        prefix=f".{output.name}.",
        text=True,
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(output)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pyproject", type=Path, default=REPO_ROOT / "pyproject.toml")
    parser.add_argument("--source-root", type=Path, default=REPO_ROOT / "src")
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / "site" / "src" / "generated" / "product.json",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        write_atomic(args.output, build_payload(args.pyproject, args.source_root))
    except (ImportError, OSError, TypeError, ValueError, tomllib.TOMLDecodeError) as error:
        print(f"product data export failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Ignore generated and browser-test output**

Append these exact entries to `.gitignore`:

```gitignore
site/.astro/
site/dist/
site/node_modules/
site/playwright-report/
site/test-results/
site/src/generated/product.json
```

- [ ] **Step 5: Run focused and full Python verification**

Run: `pytest tests/test_site_product_data.py -q`

Expected: all product-data tests pass.

Run: `pytest -q`

Expected: the full Python suite passes. This verifies repository behavior covered by the suite, not external APIs.

- [ ] **Step 6: Commit the product-data boundary**

```bash
git add -- .gitignore site/scripts/export-product-data.py tests/test_site_product_data.py
git commit -m "feat(site): generate product data from Python sources"
```

---

### Task 2: Astro Foundation and First Vertical Slice

**Files:**
- Create: `site/package.json`
- Create: `site/pnpm-lock.yaml`
- Create: `site/tsconfig.json`
- Create: `site/astro.config.mjs`
- Create: `site/src/layouts/BaseLayout.astro`
- Create: `site/src/pages/index.astro`
- Create: `site/src/styles/global.css`
- Create: `site/tests/dist-content.test.mjs`

**Interfaces:**
- Consumes: `site/src/generated/product.json` from Task 1.
- Produces: static `site/dist/index.html`; Astro `BaseLayout` props `title: string`, `description: string`, `image?: string`, `jsonLd?: Record<string, unknown>[]`.

- [ ] **Step 1: Add the first built-output test**

Create `site/tests/dist-content.test.mjs`:

```javascript
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
```

- [ ] **Step 2: Run the dist test and confirm no site exists**

Run from `site/`: `node --test tests/dist-content.test.mjs`

Expected: failure because `dist/index.html` does not exist.

- [ ] **Step 3: Create the package and install the locked foundation**

Create `site/package.json`:

```json
{
  "name": "search-console-mcp-site",
  "private": true,
  "type": "module",
  "scripts": {
    "export:data": "python3 scripts/export-product-data.py",
    "dev": "pnpm export:data && astro dev",
    "build": "pnpm export:data && astro build",
    "preview": "astro preview",
    "check": "pnpm export:data && astro check",
    "test:dist": "node --test tests/dist-*.test.mjs",
    "test:e2e": "playwright test",
    "verify": "pnpm check && pnpm build && pnpm test:dist && pnpm test:e2e"
  },
  "dependencies": {
    "@astrojs/sitemap": "^3.7.0",
    "astro": "^5.17.1"
  },
  "devDependencies": {
    "@astrojs/check": "^0.9.10",
    "@axe-core/playwright": "^4.10.2",
    "@playwright/test": "^1.55.0",
    "typescript": "^5.9.3"
  }
}
```

Run from `site/`: `pnpm install`

Expected: `site/pnpm-lock.yaml` is created and records the resolved dependency graph.

- [ ] **Step 4: Configure Astro and TypeScript**

Create `site/tsconfig.json`:

```json
{
  "extends": "astro/tsconfigs/strict",
  "include": [".astro/types.d.ts", "**/*"],
  "exclude": ["dist"]
}
```

Create `site/astro.config.mjs`:

```javascript
import sitemap from '@astrojs/sitemap'
import { defineConfig } from 'astro/config'

export default defineConfig({
  site: 'https://search-console.bruniaux.com',
  base: '/',
  output: 'static',
  trailingSlash: 'always',
  integrations: [sitemap()],
})
```

- [ ] **Step 5: Create the minimal layout and page**

Create `site/src/layouts/BaseLayout.astro`:

```astro
---
import '../styles/global.css'

interface Props {
  title: string
  description: string
  image?: string
  jsonLd?: Record<string, unknown>[]
}

const { title, description, image = '/og-image.png', jsonLd = [] } = Astro.props
const canonical = new URL(Astro.url.pathname, Astro.site)
const socialImage = new URL(image, Astro.site)
---

<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{title}</title>
    <meta name="description" content={description} />
    <link rel="canonical" href={canonical} />
    <meta property="og:title" content={title} />
    <meta property="og:description" content={description} />
    <meta property="og:type" content="website" />
    <meta property="og:url" content={canonical} />
    <meta property="og:image" content={socialImage} />
    {jsonLd.map((entry) => (
      <script type="application/ld+json" set:html={JSON.stringify(entry)} />
    ))}
  </head>
  <body>
    <slot />
  </body>
</html>
```

Create `site/src/pages/index.astro`:

```astro
---
import product from '../generated/product.json'
import BaseLayout from '../layouts/BaseLayout.astro'

const title = 'Search Console MCP for Google, Bing and SEO Analytics'
const description = 'Connect AI assistants to Google Search Console, Bing Webmaster Tools, GA4, CrUX and guarded SEO workflows.'
---

<BaseLayout {title} {description}>
  <main id="main-content">
    <h1>Search Console MCP</h1>
    <p>{product.toolCount} MCP tools</p>
    <p>Version {product.version}</p>
    <p>Python {product.pythonRequires}</p>
  </main>
</BaseLayout>
```

Create `site/src/styles/global.css` with the first render-safe baseline:

```css
:root {
  color-scheme: light dark;
  font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

* {
  box-sizing: border-box;
}

html,
body {
  margin: 0;
  min-height: 100%;
}
```

- [ ] **Step 6: Verify the first static slice**

Run from `site/`: `pnpm check`

Expected: Astro reports no errors.

Run from `site/`: `pnpm build && pnpm test:dist`

Expected: the site builds and the initial dist test passes.

- [ ] **Step 7: Commit the Astro foundation**

```bash
git add -- site/package.json site/pnpm-lock.yaml site/tsconfig.json site/astro.config.mjs site/src/layouts/BaseLayout.astro site/src/pages/index.astro site/src/styles/global.css site/tests/dist-content.test.mjs
git commit -m "feat(site): add Astro static foundation"
```

---

### Task 3: BoldGuy Page Content and Components

**Files:**
- Create: `site/src/data/content.ts`
- Create: `site/src/components/SiteHeader.astro`
- Create: `site/src/components/Hero.astro`
- Create: `site/src/components/ProofStrip.astro`
- Create: `site/src/components/ProviderCoverage.astro`
- Create: `site/src/components/Workflow.astro`
- Create: `site/src/components/InstallPath.astro`
- Create: `site/src/components/EvidenceSafety.astro`
- Create: `site/src/components/Faq.astro`
- Create: `site/src/components/SiteFooter.astro`
- Modify: `site/src/pages/index.astro`
- Modify: `site/src/styles/global.css`
- Modify: `site/tests/dist-content.test.mjs`

**Interfaces:**
- Consumes: product JSON and the content arrays exported by `site/src/data/content.ts`.
- Produces: semantic section IDs `capabilities`, `workflow`, `install`, `safety`, `faq`; visible FAQ data later reused by JSON-LD.

- [ ] **Step 1: Extend the content test before adding sections**

Append to `site/tests/dist-content.test.mjs`:

```javascript
test('renders every product section and provider boundary', () => {
  for (const id of ['capabilities', 'workflow', 'install', 'safety', 'faq']) {
    assert.match(html, new RegExp(`id="${id}"`))
  }
  for (const provider of ['Google data', 'Bing data', 'Public-page analysis']) {
    assert.match(html, new RegExp(provider))
  }
})

test('keeps crawl and indexation claims bounded', () => {
  assert.match(html, /accepted submission proves neither crawl nor indexation/i)
  assert.match(html, /Google and Bing position semantics remain separate/i)
})

test('renders all visible FAQ questions', () => {
  const questions = [
    'Does one Bing API key work for every site?',
    'Do I need every Google API enabled?',
    'Does a successful submission mean the page is indexed?',
    'Can I use the server from Claude and Codex?',
    'Where do credentials live?',
  ]
  for (const question of questions) assert.match(html, new RegExp(question.replace('?', '\\?')))
})
```

- [ ] **Step 2: Run the test and confirm the sections are absent**

Run from `site/`: `pnpm build && pnpm test:dist`

Expected: the new section, provider and FAQ assertions fail.

- [ ] **Step 3: Create the stable content contract**

Create `site/src/data/content.ts`:

```typescript
export const siteLinks = {
  repository: 'https://github.com/FlorianBruniaux/google-search-console-mcp',
  pypi: 'https://pypi.org/project/gsc-mcp-tools/',
  install: 'https://github.com/FlorianBruniaux/google-search-console-mcp/blob/main/docs/installation.md',
  googleSetup: 'https://github.com/FlorianBruniaux/google-search-console-mcp/blob/main/docs/google-setup.md',
  bingSetup: 'https://github.com/FlorianBruniaux/google-search-console-mcp/blob/main/docs/bing-setup.md',
  license: 'https://github.com/FlorianBruniaux/google-search-console-mcp/blob/main/LICENSE',
  author: 'https://www.florian.bruniaux.com/about/?utm_source=search-console-mcp&utm_medium=website',
} as const

export const providers = [
  {
    id: 'google',
    title: 'Google data',
    copy: 'Search Console performance and inspection, optional GA4 behavior data, and optional CrUX field data.',
    items: ['Search performance', 'URL inspection', 'GA4', 'CrUX'],
  },
  {
    id: 'bing',
    title: 'Bing data',
    copy: 'Webmaster performance, crawl, feeds, backlinks and guarded submissions for sites visible to the configured Bing account.',
    items: ['Queries and pages', 'Crawl signals', 'Feeds', 'IndexNow'],
  },
  {
    id: 'public',
    title: 'Public-page analysis',
    copy: 'Fetched HTML, robots, sitemaps, structured data, content and internal-link signals without private provider credentials.',
    items: ['Metadata', 'Schema', 'Sitemaps', 'Internal links'],
  },
] as const

export const workflowSteps = [
  ['Connect', 'Select only the verified properties and provider credentials you need.'],
  ['Measure', 'Read queries, pages, crawl signals and public-page evidence.'],
  ['Compare', 'Keep provider semantics and observed windows explicit.'],
  ['Explain', 'Return structured facts, derived values and recommendations.'],
  ['Submit', 'Run bounded write tools only after the target and action are confirmed.'],
] as const

export const installSteps = [
  ['Evaluate once', 'Run uvx gsc-mcp-tools without changing a project environment.'],
  ['Install persistently', 'Run uv tool install gsc-mcp-tools and point the MCP client at the installed executable.'],
  ['Verify access', 'Run gsc-cli list, then verify each configured provider separately.'],
] as const

export const evidenceStates = [
  ['Observed', 'API responses and fetched public-page data.'],
  ['Derived', 'Calculations tied to an explicit observed window.'],
  ['Requested', 'A provider accepted a submission. Crawl and indexation remain unproven.'],
] as const

export const faqs = [
  {
    question: 'Does one Bing API key work for every site?',
    answer: 'One Bing Webmaster API key can access the verified sites visible to that Bing account. Every tool call still names its target site. IndexNow uses a different key verified on each target host.',
  },
  {
    question: 'Do I need every Google API enabled?',
    answer: 'No. Configure the provider families you use. Search Console credentials cover the core search workflows. GA4, CrUX and eligible Indexing API workflows require their own optional configuration.',
  },
  {
    question: 'Does a successful submission mean the page is indexed?',
    answer: 'No. An accepted submission proves only that the provider accepted the request. Crawl and indexation must be measured separately in a later comparable check.',
  },
  {
    question: 'Can I use the server from Claude and Codex?',
    answer: 'Yes. Search Console MCP runs over stdio and can be configured in Claude, Codex and other compatible MCP clients. The executable path and configuration format depend on the client.',
  },
  {
    question: 'Where do credentials live?',
    answer: 'Credentials stay in the MCP server environment or the client configuration. The public website never receives them, and prompts should not contain secret values.',
  },
] as const
```

- [ ] **Step 4: Create semantic components**

Use these component boundaries and markup contracts:

`SiteHeader.astro`:

```astro
<a class="skip-link" href="#main-content">Skip to main content</a>
<header class="site-header">
  <div class="container header-inner">
    <a class="wordmark" href="/" aria-label="Search Console MCP home">
      <span aria-hidden="true">&gt;_</span> Search Console MCP
    </a>
    <nav aria-label="Primary navigation">
      <a href="#capabilities">Capabilities</a>
      <a href="#install">Install</a>
      <a href="#safety">Safety</a>
      <a href="#faq">FAQ</a>
    </nav>
    <button class="theme-toggle" type="button" data-theme-toggle aria-label="Switch to dark theme">
      <span aria-hidden="true" data-theme-icon>◐</span>
    </button>
  </div>
</header>
```

`Hero.astro` accepts `toolCount: number` and renders the exact command as a button-owned data value:

```astro
---
interface Props { toolCount: number }
const { toolCount } = Astro.props
const command = 'uvx gsc-mcp-tools'
---
<section class="hero" aria-labelledby="hero-title">
  <div class="hero-grid">
    <div>
      <p class="kicker">Google + Bing + SEO analytics</p>
      <h1 id="hero-title">Search data your AI assistant can inspect, compare and act on safely.</h1>
      <p class="hero-copy">Search Console MCP connects Claude, Codex and other MCP clients to Google Search Console, Bing Webmaster Tools, GA4, CrUX, IndexNow and public-page audits.</p>
      <div class="hero-actions">
        <button class="button button-primary" type="button" data-copy-command={command}>Copy install command</button>
        <a class="button button-secondary" href="#install">View installation path</a>
      </div>
      <p class="copy-status" data-copy-status role="status" aria-live="polite"></p>
    </div>
    <div class="terminal" aria-label="Example command and request">
      <div class="terminal-bar" aria-hidden="true"><span></span><span></span><span></span></div>
      <code><span class="terminal-prompt">$</span> {command}</code>
      <p>&gt; Compare this site's Google and Bing visibility. Keep each provider's position semantics separate.</p>
      <small>{toolCount} registered tools, structured JSON output</small>
    </div>
  </div>
</section>
```

`ProofStrip.astro` accepts the generated product object and renders four `<li>` facts. `ProviderCoverage.astro`, `Workflow.astro`, `InstallPath.astro`, `EvidenceSafety.astro` and `Faq.astro` map their matching arrays from `content.ts` inside semantic `<section>` elements. `ProviderCoverage.astro` ends with the visible sentence `Google and Bing position semantics remain separate.`. `Faq.astro` uses one native `<details data-faq-item>` per item. `SiteFooter.astro` renders the five destinations from `siteLinks` with descriptive labels.

Each mapped collection uses a stable key from `id`, title or question and preserves the exact copy in `content.ts`. Do not duplicate these strings inside components.

- [ ] **Step 5: Compose the page and expose FAQ data**

Replace `site/src/pages/index.astro` with imports for every component, `product.json`, `faqs` and `siteLinks`. Render this order:

```astro
<BaseLayout {title} {description}>
  <SiteHeader />
  <main id="main-content">
    <Hero toolCount={product.toolCount} />
    <ProofStrip {product} />
    <ProviderCoverage />
    <Workflow />
    <InstallPath />
    <EvidenceSafety />
    <Faq />
  </main>
  <SiteFooter />
</BaseLayout>
```

- [ ] **Step 6: Apply the BoldGuy tokens and responsive composition**

Replace the baseline CSS with the approved tokens and these invariant rules:

```css
:root {
  color-scheme: light;
  --bg-primary: #f5f0eb;
  --bg-secondary: #fef7f0;
  --bg-tertiary: #f0e8df;
  --surface-elevated: #ffffff;
  --border: #d4cdc5;
  --border-light: #e8dfd6;
  --text-primary: #1a1207;
  --text-secondary: #4a3f31;
  --text-muted: #6b6053;
  --accent: #c2410c;
  --accent-hover: #9a3412;
  --success: #16a34a;
  --provider-google: #4285f4;
  --provider-bing: #008373;
  --font-sans: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen, Ubuntu, sans-serif;
  --font-mono: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, "Liberation Mono", monospace;
  --max-width: 75rem;
}

[data-theme="dark"] {
  color-scheme: dark;
  --bg-primary: #0a0a0a;
  --bg-secondary: #141414;
  --bg-tertiary: #1e1e1e;
  --surface-elevated: #141414;
  --border: #2a2a2a;
  --border-light: #1e1e1e;
  --text-primary: #e5e5e5;
  --text-secondary: #a3a3a3;
  --text-muted: #8a8a8a;
  --accent: #f97316;
  --accent-hover: #fb923c;
  --success: #22c55e;
}

* { box-sizing: border-box; }
html { scroll-padding-top: 4.5rem; }
body {
  margin: 0;
  overflow-wrap: anywhere;
  background: var(--bg-primary);
  color: var(--text-primary);
  font: 400 1rem/1.6 var(--font-sans);
}
.container { width: min(100% - 3rem, var(--max-width)); margin-inline: auto; }
section { padding-block: 5rem; }
h1 {
  max-width: 15ch;
  margin: 0;
  font-size: clamp(2.45rem, 6vw, 4.7rem);
  line-height: 0.98;
  letter-spacing: -0.05em;
}
:focus-visible { outline: 2px solid var(--accent); outline-offset: 3px; }
.button, button, summary { min-height: 44px; }
.terminal { background: #101318; color: #f3f4f6; border: 1px solid #2a2f38; border-radius: 12px; }

@media (max-width: 48rem) {
  .container { width: min(100% - 2rem, var(--max-width)); }
  section { padding-block: 3rem; }
  .hero-grid { grid-template-columns: 1fr; }
  .hero-actions { display: grid; }
  .hero-actions > * { width: 100%; }
  .provider-grid, .workflow-list, .install-grid { grid-template-columns: 1fr; }
  .proof-list { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    scroll-behavior: auto !important;
    transition-duration: 0.01ms !important;
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
  }
}
```

Add focused rules for header, hero grid, proof list, provider cards, workflow connectors, install steps, evidence states, FAQ disclosures and footer. Use the approved 8 px control radius, 12 px card radius, 1 px borders and restrained shadows. Only provider cards may use `--provider-google` and `--provider-bing` as top-border labels.

- [ ] **Step 7: Verify content and rendering**

Run from `site/`: `pnpm check && pnpm build && pnpm test:dist`

Expected: type checks, build and all content assertions pass.

- [ ] **Step 8: Commit the complete static page**

```bash
git add -- site/src/data/content.ts site/src/components site/src/pages/index.astro site/src/styles/global.css site/tests/dist-content.test.mjs
git commit -m "feat(site): build BoldGuy product landing page"
```

---

### Task 4: Theme, Copy Action and Browser Accessibility

**Files:**
- Create: `site/src/scripts/interactions.ts`
- Create: `site/playwright.config.ts`
- Create: `site/tests/site.spec.ts`
- Create: `site/tests/site.spec.ts-snapshots/`
- Modify: `site/src/layouts/BaseLayout.astro`
- Modify: `site/src/components/SiteHeader.astro`
- Modify: `site/src/styles/global.css`

**Interfaces:**
- Consumes: `[data-theme-toggle]`, `[data-theme-icon]`, `[data-copy-command]`, `[data-copy-status]` hooks from Task 3.
- Produces: saved `theme` value `light` or `dark`; status strings `Command copied.` and `Copy failed. Select the command manually.`.

- [ ] **Step 1: Write Playwright behavior and accessibility tests**

Create `site/playwright.config.ts`:

```typescript
import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './tests',
  testMatch: 'site.spec.ts',
  fullyParallel: false,
  use: {
    baseURL: 'http://127.0.0.1:4321',
    trace: 'retain-on-failure',
  },
  webServer: {
    command: 'pnpm preview --host 127.0.0.1 --port 4321',
    port: 4321,
    reuseExistingServer: !process.env.CI,
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
})
```

Create `site/tests/site.spec.ts` with these tests:

```typescript
import AxeBuilder from '@axe-core/playwright'
import { expect, test } from '@playwright/test'

test('copies the install command and announces success', async ({ page, context }) => {
  await context.grantPermissions(['clipboard-read', 'clipboard-write'])
  await page.goto('/')
  await page.getByRole('button', { name: 'Copy install command' }).click()
  await expect(page.getByRole('status')).toHaveText('Command copied.')
  expect(await page.evaluate(() => navigator.clipboard.readText())).toBe('uvx gsc-mcp-tools')
})

test('keeps the command visible when clipboard access fails', async ({ page }) => {
  await page.addInitScript(() => {
    Object.defineProperty(navigator, 'clipboard', {
      value: { writeText: () => Promise.reject(new Error('denied')) },
      configurable: true,
    })
  })
  await page.goto('/')
  await page.getByRole('button', { name: 'Copy install command' }).click()
  await expect(page.getByRole('status')).toHaveText('Copy failed. Select the command manually.')
  await expect(page.getByText('uvx gsc-mcp-tools', { exact: true })).toBeVisible()
})

test('uses the operating-system theme and persists a manual choice', async ({ page }) => {
  await page.emulateMedia({ colorScheme: 'dark' })
  await page.goto('/')
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark')
  await page.getByRole('button', { name: 'Switch to light theme' }).click()
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'light')
  await page.reload()
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'light')
})

test('still switches theme when localStorage throws', async ({ page }) => {
  await page.addInitScript(() => {
    Storage.prototype.getItem = () => { throw new Error('blocked') }
    Storage.prototype.setItem = () => { throw new Error('blocked') }
  })
  await page.goto('/')
  await page.getByRole('button', { name: /Switch to/ }).click()
  await expect(page.locator('html')).toHaveAttribute('data-theme', /light|dark/)
})

test('has no serious or critical axe violations', async ({ page }) => {
  await page.goto('/')
  const results = await new AxeBuilder({ page }).analyze()
  const blockers = results.violations.filter(({ impact }) => impact === 'serious' || impact === 'critical')
  expect(blockers).toEqual([])
})

test('keeps the mobile document contained and controls large enough', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/')
  const dimensions = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    clientWidth: document.documentElement.clientWidth,
    heights: [...document.querySelectorAll('a, button, summary')].map((node) => node.getBoundingClientRect().height),
  }))
  expect(dimensions.scrollWidth).toBeLessThanOrEqual(dimensions.clientWidth)
  expect(dimensions.heights.every((height) => height >= 44)).toBe(true)
})

test('shows a visible keyboard focus', async ({ page }) => {
  await page.goto('/')
  await page.keyboard.press('Tab')
  const skipLink = page.getByRole('link', { name: 'Skip to main content' })
  await expect(skipLink).toBeFocused()
  expect(await skipLink.evaluate((node) => getComputedStyle(node).outlineWidth)).toBe('2px')
})

for (const theme of ['light', 'dark'] as const) {
  for (const viewport of [{ width: 390, height: 844 }, { width: 1440, height: 1000 }]) {
    test(`matches ${theme} ${viewport.width}px baseline`, async ({ page }) => {
      await page.setViewportSize(viewport)
      await page.addInitScript((selectedTheme) => localStorage.setItem('theme', selectedTheme), theme)
      await page.goto('/')
      await expect(page).toHaveScreenshot(`${theme}-${viewport.width}.png`, {
        fullPage: true,
        animations: 'disabled',
      })
    })
  }
}
```

- [ ] **Step 2: Install Chromium and confirm behavior tests fail**

Run from `site/`: `pnpm exec playwright install chromium`

Run from `site/`: `pnpm build && pnpm test:e2e`

Expected: interaction and visual tests fail because the scripts and snapshots are absent.

- [ ] **Step 3: Add pre-paint theme boot and interaction loading**

Add this inline script inside `BaseLayout.astro` `<head>` before styles can paint:

```astro
<script is:inline>
  (() => {
    let saved = null
    try { saved = localStorage.getItem('theme') } catch {}
    const systemDark = matchMedia('(prefers-color-scheme: dark)').matches
    document.documentElement.dataset.theme = saved === 'light' || saved === 'dark'
      ? saved
      : systemDark ? 'dark' : 'light'
  })()
</script>
```

Import the browser module at the end of `<body>`:

```astro
<script>
  import '../scripts/interactions'
</script>
```

- [ ] **Step 4: Implement copy and theme behavior**

Create `site/src/scripts/interactions.ts`:

```typescript
type Theme = 'light' | 'dark'

const root = document.documentElement
const themeButton = document.querySelector<HTMLButtonElement>('[data-theme-toggle]')
const themeIcon = document.querySelector<HTMLElement>('[data-theme-icon]')

function currentTheme(): Theme {
  return root.dataset.theme === 'dark' ? 'dark' : 'light'
}

function syncThemeControl(): void {
  const next = currentTheme() === 'dark' ? 'light' : 'dark'
  if (themeButton) themeButton.setAttribute('aria-label', `Switch to ${next} theme`)
  if (themeIcon) themeIcon.textContent = currentTheme() === 'dark' ? '☀' : '◐'
}

themeButton?.addEventListener('click', () => {
  const next: Theme = currentTheme() === 'dark' ? 'light' : 'dark'
  root.dataset.theme = next
  try { localStorage.setItem('theme', next) } catch {}
  syncThemeControl()
})

syncThemeControl()

document.querySelectorAll<HTMLButtonElement>('[data-copy-command]').forEach((button) => {
  button.addEventListener('click', async () => {
    const status = document.querySelector<HTMLElement>('[data-copy-status]')
    try {
      await navigator.clipboard.writeText(button.dataset.copyCommand ?? '')
      if (status) status.textContent = 'Command copied.'
    } catch {
      if (status) status.textContent = 'Copy failed. Select the command manually.'
    }
  })
})
```

- [ ] **Step 5: Complete keyboard and mobile CSS**

Make the skip link visible on focus, keep desktop navigation available above 768 px, use a native `<details>` navigation below 768 px, and ensure every link's padded hit area reaches 44 px. Do not hide focus outlines. Add `scroll-margin-top: 4.5rem` to every anchored section.

- [ ] **Step 6: Create and inspect visual baselines**

Run from `site/`: `pnpm build && pnpm test:e2e --update-snapshots`

Inspect all four files under `site/tests/site.spec.ts-snapshots/` at original resolution. Reject any overflow, clipped focus, illegible contrast, duplicated H1, broken connector or off-brand provider color.

Run from `site/`: `pnpm test:e2e`

Expected: behavior, axe, responsive and screenshot tests pass without updating snapshots.

- [ ] **Step 7: Commit interactions and reviewed screenshots**

```bash
git add -- site/src/scripts/interactions.ts site/playwright.config.ts site/tests/site.spec.ts site/tests/site.spec.ts-snapshots site/src/layouts/BaseLayout.astro site/src/components/SiteHeader.astro site/src/styles/global.css
git commit -m "test(site): verify accessible interactions and layouts"
```

---

### Task 5: SEO Contract and Public Assets

**Files:**
- Create: `site/tests/dist-seo.test.mjs`
- Create: `site/public/CNAME`
- Create: `site/public/favicon.svg`
- Create: `site/public/og-image.png`
- Create: `site/public/robots.txt`
- Modify: `site/src/layouts/BaseLayout.astro`
- Modify: `site/src/pages/index.astro`

**Interfaces:**
- Consumes: `product` and `faqs` from earlier tasks.
- Produces: canonical metadata, social metadata, `SoftwareApplication` JSON-LD, `FAQPage` JSON-LD, favicon, social image, sitemap, robots file and CNAME.

- [ ] **Step 1: Write the built SEO contract test**

Create `site/tests/dist-seo.test.mjs`:

```javascript
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
  assert.match(html, /<meta name="twitter:card" content="summary_large_image"/)
  assert.equal((html.match(/<h1[ >]/g) ?? []).length, 1)
})

test('keeps structured data aligned with generated and visible content', () => {
  const entries = jsonLdEntries()
  const software = entries.find((entry) => entry['@type'] === 'SoftwareApplication')
  const faq = entries.find((entry) => entry['@type'] === 'FAQPage')
  assert.equal(software.softwareVersion, product.version)
  assert.equal(software.name, 'Search Console MCP')
  assert.equal(faq.mainEntity.length, (html.match(/<details data-faq-item/g) ?? []).length)
  for (const entity of faq.mainEntity) {
    assert.match(html, new RegExp(entity.name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')))
    assert.match(html, new RegExp(entity.acceptedAnswer.text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')))
  }
})

test('publishes crawl files for the canonical host', async () => {
  assert.equal((await readFile(new URL('CNAME', dist), 'utf8')).trim(), 'search-console.bruniaux.com')
  assert.match(await readFile(new URL('robots.txt', dist), 'utf8'), /Sitemap: https:\/\/search-console\.bruniaux\.com\/sitemap-index\.xml/)
  const sitemapFiles = (await readdir(dist)).filter((name) => /^sitemap.*\.xml$/.test(name))
  const sitemapText = (await Promise.all(sitemapFiles.map((name) => readFile(new URL(name, dist), 'utf8')))).join('\n')
  assert.match(sitemapText, /https:\/\/search-console\.bruniaux\.com\//)
})

test('does not leak local paths or development origins', () => {
  assert.doesNotMatch(html, /\/Users\/|localhost|127\.0\.0\.1/)
})
```

- [ ] **Step 2: Run the SEO test and confirm missing assets and schema**

Run from `site/`: `pnpm build && node --test tests/dist-seo.test.mjs`

Expected: failures name missing CNAME, robots, Twitter metadata and structured data.

- [ ] **Step 3: Add exact public text assets**

Create `site/public/CNAME`:

```text
search-console.bruniaux.com
```

Create `site/public/robots.txt`:

```text
User-agent: *
Allow: /

Sitemap: https://search-console.bruniaux.com/sitemap-index.xml
```

Create `site/public/favicon.svg` as a square BoldGuy mark with a `#0a0a0a` background, a `#f97316` 2 px rounded border, and a white `>_` monospace glyph. The SVG must include `role="img"` and `<title>Search Console MCP</title>`.

- [ ] **Step 4: Generate the social image with the image skill**

Load the `imagegen` skill and create `site/public/og-image.png` at 1200 by 630 using this prompt:

```text
Create a 1200x630 social preview for Search Console MCP. Dark neutral #0a0a0a background, thin orange #f97316 technical lines, warm white typography, restrained BoldGuy terminal aesthetic. Large title "Search Console MCP". Subtitle "Google, Bing and SEO analytics for AI assistants". Show a simple left-to-right flow: Connect, Measure, Compare, Explain, Submit. No company logos, no gradients, no glassmorphism, no fake metrics, no tiny text. High contrast and generous margins.
```

Inspect the image at original resolution. Reject misspelled text, clipped text, fake provider logos, low contrast or decorative detail that competes with the title.

- [ ] **Step 5: Add structured data and complete head metadata**

In `index.astro`, derive both JSON-LD objects from existing data:

```typescript
const softwareJsonLd = {
  '@context': 'https://schema.org',
  '@type': 'SoftwareApplication',
  name: 'Search Console MCP',
  applicationCategory: 'DeveloperApplication',
  operatingSystem: 'Cross-platform',
  softwareVersion: product.version,
  url: 'https://search-console.bruniaux.com/',
  downloadUrl: siteLinks.pypi,
  codeRepository: product.repository,
  license: siteLinks.license,
}

const faqJsonLd = {
  '@context': 'https://schema.org',
  '@type': 'FAQPage',
  mainEntity: faqs.map(({ question, answer }) => ({
    '@type': 'Question',
    name: question,
    acceptedAnswer: { '@type': 'Answer', text: answer },
  })),
}
```

Pass `jsonLd={[softwareJsonLd, faqJsonLd]}` to `BaseLayout`. Add favicon, `og:site_name`, image alternative text, `twitter:card`, `twitter:title`, `twitter:description` and `twitter:image` tags in `BaseLayout`.

- [ ] **Step 6: Verify the complete local artifact**

The existing `test:dist` glob runs both `dist-content.test.mjs` and `dist-seo.test.mjs`.

Run from `site/`: `pnpm check && pnpm build && pnpm test:dist && pnpm test:e2e`

Expected: all type, build, content, SEO, interaction, accessibility and visual checks pass.

- [ ] **Step 7: Commit SEO and public assets**

```bash
git add -- site/tests/dist-seo.test.mjs site/public/CNAME site/public/favicon.svg site/public/og-image.png site/public/robots.txt site/src/layouts/BaseLayout.astro site/src/pages/index.astro
git commit -m "feat(site): add SEO contract and social assets"
```

---

### Task 6: Isolated GitHub Pages Workflow

**Files:**
- Create: `tests/test_site_workflow.py`
- Create: `.github/workflows/site.yml`

**Interfaces:**
- Consumes: root Python project, `site/pnpm-lock.yaml`, `site/package.json`, static site tests.
- Produces: GitHub Pages artifact from `site/dist`; public `deployment.json` with `sha` and `runId`; deployment URL output.

- [ ] **Step 1: Write workflow boundary tests**

Create `tests/test_site_workflow.py`:

```python
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "site.yml"


def workflow_text() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def test_site_workflow_has_isolated_triggers_and_permissions():
    text = workflow_text()
    assert 'branches: ["main"]' in text
    for path in ("site/**", "pyproject.toml", "src/gsc_mcp/**", ".github/workflows/site.yml"):
        assert path in text
    assert "pages: write" in text
    assert "id-token: write" in text
    assert "pypi" not in text.lower()


def test_site_workflow_verifies_before_uploading():
    text = workflow_text()
    assert text.index("pytest tests/test_site_product_data.py") < text.index("pnpm verify")
    assert text.index("pnpm verify") < text.index("actions/upload-pages-artifact")
    assert "site/dist/deployment.json" in text
    assert "site/dist/" in text


def test_site_workflow_uses_locked_toolchains():
    text = workflow_text()
    assert 'python-version: "3.11"' in text
    assert 'node-version: "22"' in text
    assert "version: 9" in text
    assert "pnpm install --frozen-lockfile" in text
    assert "playwright install --with-deps chromium" in text
```

- [ ] **Step 2: Run the test and confirm the workflow is absent**

Run: `pytest tests/test_site_workflow.py -q`

Expected: failures identify the missing `.github/workflows/site.yml`.

- [ ] **Step 3: Create the Pages workflow**

Create `.github/workflows/site.yml`:

```yaml
name: Deploy Search Console MCP site

on:
  push:
    branches: ["main"]
    paths:
      - "site/**"
      - "pyproject.toml"
      - "src/gsc_mcp/**"
      - ".github/workflows/site.yml"
  workflow_dispatch:

concurrency:
  group: search-console-mcp-pages
  cancel-in-progress: false

jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install Python project
        run: python -m pip install ".[dev]"

      - name: Verify product data exporter
        run: pytest tests/test_site_product_data.py -q

      - name: Setup pnpm
        uses: pnpm/action-setup@v4
        with:
          version: 9

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: "22"
          cache: pnpm
          cache-dependency-path: site/pnpm-lock.yaml

      - name: Install site dependencies
        working-directory: site
        run: pnpm install --frozen-lockfile

      - name: Install Chromium
        working-directory: site
        run: pnpm exec playwright install --with-deps chromium

      - name: Verify and build site
        working-directory: site
        run: pnpm verify

      - name: Record deployment provenance
        run: >-
          printf '{"sha":"%s","runId":"%s"}\n'
          "$GITHUB_SHA" "$GITHUB_RUN_ID"
          > site/dist/deployment.json

      - name: Configure Pages
        uses: actions/configure-pages@v5

      - name: Upload Pages artifact
        uses: actions/upload-pages-artifact@v3
        with:
          path: site/dist/

  deploy:
    needs: build
    runs-on: ubuntu-latest
    permissions:
      pages: write
      id-token: write
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    outputs:
      page_url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - name: Deploy to GitHub Pages
        id: deployment
        uses: actions/deploy-pages@v4
```

- [ ] **Step 4: Run workflow and full local verification**

Run: `pytest tests/test_site_workflow.py tests/test_site_product_data.py -q`

Expected: all site infrastructure tests pass.

Run from `site/`: `pnpm verify`

Expected: the complete site verification passes from the locked dependency graph.

Run: `pytest -q`

Expected: the full Python suite passes.

- [ ] **Step 5: Commit the isolated delivery workflow**

```bash
git add -- .github/workflows/site.yml tests/test_site_workflow.py
git commit -m "ci(site): deploy verified Astro artifact to Pages"
```

---

### Task 7: Deploy, Verify the Custom Domain and Expose the Public Entry Point

**Files:**
- Modify after public verification: `README.md`
- Modify after public verification: `pyproject.toml`

**Interfaces:**
- Consumes: successful `site.yml` run, DNS control for `bruniaux.com`, public `deployment.json`.
- Produces: verified `https://search-console.bruniaux.com/`; README website link; PyPI homepage metadata for the next package release.

- [ ] **Step 1: Freeze the local and remote candidates before push**

Run:

```bash
git status --short
git log --oneline origin/main..HEAD
git diff origin/main...HEAD --stat
```

Expected: only the approved specification, plan and site commits are ahead of `origin/main`; unrelated untracked Bing files remain unstaged.

- [ ] **Step 2: Push the exact branch and verify its remote SHA**

Run: `git push origin main`

Then run:

```bash
git rev-parse HEAD
git ls-remote origin refs/heads/main
```

Expected: local and remote SHA values match exactly.

- [ ] **Step 3: Enable GitHub Pages through GitHub Actions**

In repository Settings, Pages, set Source to **GitHub Actions**. Do not create or expose deployment secrets; the workflow uses GitHub's short-lived Pages identity token.

Trigger `Deploy Search Console MCP site` if the main push did not start it. Verify the build and deploy jobs both target the pushed SHA.

- [ ] **Step 4: Configure and verify the subdomain**

Before changing DNS, record the current result:

```bash
dig +short CNAME search-console.bruniaux.com
dig +short A search-console.bruniaux.com
```

Create this DNS record in the authoritative DNS provider:

```text
Type: CNAME
Name: search-console
Target: florianbruniaux.github.io
```

Do not create an additional A or AAAA record for the same hostname. Verify the returned CNAME before treating DNS as complete:

```bash
dig +short CNAME search-console.bruniaux.com
```

Expected: `florianbruniaux.github.io.`

- [ ] **Step 5: Verify public content, HTTPS and deployment provenance**

Run:

```bash
curl -fsSI https://search-console.bruniaux.com/
curl -fsS https://search-console.bruniaux.com/deployment.json
curl -fsS https://search-console.bruniaux.com/robots.txt
curl -fsS https://search-console.bruniaux.com/sitemap-index.xml
```

Expected:

- homepage returns HTTP 200 over HTTPS;
- `deployment.json.sha` equals the remote `main` SHA;
- `robots.txt` names the canonical sitemap;
- sitemap contains `https://search-console.bruniaux.com/`.

Open the public page at 390 px and 1440 px in light and dark mode. Recheck copy, theme, navigation, focus and FAQ disclosure against the local baselines.

- [ ] **Step 6: Add the verified public entry points**

Only after Step 5 passes, change `[project.urls]` in `pyproject.toml` to:

```toml
[project.urls]
Homepage = "https://search-console.bruniaux.com/"
Documentation = "https://search-console.bruniaux.com/#install"
Repository = "https://github.com/FlorianBruniaux/google-search-console-mcp"
```

Add this row near the top of the README navigation and Documentation table:

```markdown
| Explore the public product site | [Search Console MCP website](https://search-console.bruniaux.com/) |
```

Do not change the package version. These metadata changes reach PyPI with the next package release; the website itself is already live through Pages.

- [ ] **Step 7: Rebuild against the changed package metadata**

Run: `pytest tests/test_site_product_data.py -q`

Confirm that `test_export_matches_repository_sources` still expects the GitHub repository URL. No homepage field is added to product JSON.

Run from `site/`: `pnpm verify`

Run: `python -m pip install --upgrade build twine`

Run: `python -m build && python -m twine check dist/*`

Expected: exporter, site and package metadata checks pass. This build is local verification and does not publish a new PyPI version.

- [ ] **Step 8: Commit and push the verified public links**

```bash
git add -- README.md pyproject.toml
git commit -m "docs: expose Search Console MCP website"
git push origin main
```

Verify the new remote SHA separately with `git ls-remote origin refs/heads/main`.

- [ ] **Step 9: Record evidence limits**

Report the Pages workflow URL, deployed SHA, public URL and local verification results. Keep these states explicit:

- GitHub Pages deployment: verified only when the workflow and SHA match.
- Public behavior: verified only for the exercised browsers and viewports.
- Google and Bing indexation: `UNKNOWN` until their webmaster tools report the URL.
- Search ranking and conversion impact: `UNKNOWN` until comparable measurements exist.

---

## Rollback

Use `git revert` for committed site changes. Do not rewrite `main` history.

1. Record the current remote SHA and live `deployment.json`.
2. Confirm no newer Pages deployment or DNS edit was made by another writer.
3. Revert the faulty site commit or contiguous site commit range.
4. Push the revert and wait for `site.yml` to deploy the reverted artifact.
5. Verify the public `deployment.json`, homepage, robots and sitemap against the revert SHA.
6. Restore the exact DNS preimage recorded in Task 7 only if the hostname itself must be withdrawn. Do not delete a DNS record whose live value changed after the recorded preimage.
7. Keep workflow logs and verification output after rollback.

If the failed release created `search-console.bruniaux.com` from an absent DNS record and no concurrent writer changed it, remove only that exact CNAME. If coordination cannot exclude another writer, stop for manual DNS reconciliation.

## Final Whole-Branch Review

After all tasks pass, run a fresh whole-branch review against the approved design spec. The reviewer checks:

- every spec success criterion maps to a test or named public check;
- `.github/workflows/publish.yml` is byte-identical to the base commit;
- no secret or credential value entered `site/`, screenshots, workflow logs or generated assets;
- the BoldGuy design remains distinct from the Claude Code brand;
- public claims match the current README, provider guides and generated product data;
- the branch contains no unrelated handoff or Bing plan files.

The branch is ready only when the review has no blocking finding and all fresh verification commands pass.
