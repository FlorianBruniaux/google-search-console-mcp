import AxeBuilder from '@axe-core/playwright'
import { expect, test } from '@playwright/test'

for (const locale of [{ path: '/', report: '/docs/examples/cc-guide-live-audit/' }, { path: '/fr/', report: '/fr/docs/examples/cc-guide-live-audit/' }]) {
  test(`opens the real SEO case and downloads its recorded evidence on ${locale.path}`, async ({ page }) => {
    await page.goto(`${locale.path}#real-example`)
    const example = page.locator('#real-example')
    await expect(example).toBeVisible()
    await expect(example).toContainText('cc.bruniaux.com')
    const evidence = example.locator('a[download]')
    const response = await page.request.get(await evidence.getAttribute('href') ?? '')
    expect(response.ok()).toBe(true)
    const trace = await response.json()
    expect(trace.transport).toBe('live MCP calls from Codex')
    expect(trace.callCount).toBe(trace.calls.length)
    expect(trace.scope.changesApplied).toBe(false)
    const total = trace.calls.find((call: { tool: string }) => call.tool === 'get_advanced_search_analytics').response.rows[0]
    expect(trace.summary.current.clicks).toBe(total.clicks)
    expect(trace.summary.current.impressions).toBe(total.impressions)
    await example.locator(`a[href="${locale.report}"]`).click()
    await expect(page).toHaveURL(locale.report)
    await expect(page.locator('main')).toContainText('2026-10-07')
  })
}

for (const locale of [
  { name: 'English', path: '/', copy: 'Copy prompt', success: 'Prompt copied.', problems: ['I’m new to SEO: where do I start?', 'My traffic is dropping', 'I want better search rankings', 'My pages are hard to find'] },
  { name: 'French', path: '/fr/', copy: 'Copier le prompt', success: 'Prompt copié.', problems: ['Je débute en SEO : par où commencer ?', 'Mon trafic baisse', 'Je veux mieux me positionner', 'Mes pages sont peu visibles'] },
]) {
  for (const width of [390, 1440]) {
    test(`SEO routing opens ${locale.name} at ${width}px and copies the selected prompt`, async ({ page, context }) => {
      await context.grantPermissions(['clipboard-read', 'clipboard-write'])
      await page.setViewportSize({ width, height: 1000 })
      await page.goto(locale.path)
      const routes = page.getByRole('region', { name: locale.name === 'French' ? 'Un problème, une analyse, des correctifs.' : 'One problem, one analysis, actionable fixes.' })
      const ids = ['getting-started', 'traffic', 'rankings', 'indexing']
      for (let index = 0; index < ids.length; index += 1) {
        const detail = page.locator(`#seo-${ids[index]}`)
        await expect(detail).not.toHaveAttribute('open')
        await routes.getByRole('link', { name: locale.problems[index], exact: true }).click()
        await expect(page).toHaveURL(`${locale.path}#seo-${ids[index]}`)
        await expect(detail).toHaveAttribute('open', '')
        await expect(detail.locator('summary')).toBeFocused()
        await expect(detail.getByRole('button', { name: locale.copy, exact: true })).toBeVisible()
        const prompt = await detail.locator('pre').innerText()
        expect(prompt).toContain('https://example.com')
        expect(prompt).toContain('Search Console MCP')
        expect(prompt).toContain('gsc-mcp-tools')
        expect(prompt).toContain('get_capabilities')
        expect(prompt).toContain('list_properties')
        expect(prompt).toContain('https://github.com/FlorianBruniaux/google-search-console-mcp/blob/main/docs/installation.md')
        expect(prompt).toContain('https://github.com/FlorianBruniaux/google-search-console-mcp/blob/main/docs/google-setup.md')
        const guide = ['quick-audit', 'traffic-drop', 'keyword-opportunities', 'indexing-issues'][index]
        const source = `https://github.com/FlorianBruniaux/google-search-console-mcp/blob/main/examples/${guide}.md`
        expect(prompt).toContain(source)
        await expect(detail.getByRole('link', { name: locale.name === 'French' ? 'Voir le scénario sur GitHub' : 'View the workflow on GitHub', exact: true })).toHaveAttribute('href', source)
        await expect(detail.getByRole('link', { name: locale.name === 'French' ? 'Installer le MCP' : 'Install the MCP', exact: true })).toHaveAttribute('href', `${locale.path}docs/installation/`)
        await expect(detail.getByRole('link', { name: locale.name === 'French' ? 'Connecter Google' : 'Connect Google', exact: true })).toHaveAttribute('href', `${locale.path}docs/google-setup/`)
        await detail.getByRole('button', { name: locale.copy, exact: true }).click()
        await expect(detail.getByRole('status')).toHaveText(locale.success)
        expect(await page.evaluate(() => navigator.clipboard.readText())).toBe(prompt)
        await expect(page.locator('#hero-copy-status')).toBeEmpty()
      }
    })
  }
}

test('SEO routing opens a direct link and reopens the same selected route', async ({ page }) => {
  await page.goto('/#seo-getting-started')
  const detail = page.locator('#seo-getting-started')
  await expect(detail).toHaveAttribute('open', '')
  await detail.locator('summary').click()
  await expect(detail).not.toHaveAttribute('open')
  const route = page.getByRole('region', { name: 'One problem, one analysis, actionable fixes.' })
    .getByRole('link', { name: 'I’m new to SEO: where do I start?', exact: true })
  await route.focus()
  await route.press('Enter')
  await expect(detail).toHaveAttribute('open', '')
  await expect(detail.locator('summary')).toBeFocused()
})

test('SEO routing keeps the French prompt selectable when clipboard access fails', async ({ page }) => {
  await page.addInitScript(() => Object.defineProperty(navigator, 'clipboard', {
    value: { writeText: () => Promise.reject(new Error('denied')) }, configurable: true,
  }))
  await page.goto('/fr/#seo-traffic')
  const detail = page.locator('#seo-traffic')
  await detail.getByRole('button', { name: 'Copier le prompt', exact: true }).click()
  await expect(detail.getByRole('status')).toHaveText('Échec de la copie. Sélectionnez le prompt manuellement.')
  await expect(detail.locator('pre')).toBeVisible()
  await expect(page.locator('#hero-copy-status')).toBeEmpty()
})

test('SEO routing remains readable without JavaScript', async ({ browser }) => {
  const context = await browser.newContext({ javaScriptEnabled: false, viewport: { width: 390, height: 1000 } })
  try {
    const page = await context.newPage()
    await page.goto('/fr/')
    const detail = page.locator('#seo-getting-started')
    await detail.locator('summary').click()
    await expect(detail.locator('pre')).toBeVisible()
    await expect(detail.locator('pre')).toContainText('https://example.com')
  } finally {
    await context.close()
  }
})

test('copies the install command and announces success', async ({ page, context }) => {
  await context.grantPermissions(['clipboard-read', 'clipboard-write'])
  await page.goto('/')
  const hero = page.locator('.hero')
  await hero.getByRole('button', { name: 'Copy uvx command' }).click()
  await expect(hero.getByRole('status')).toHaveText('Command copied.')
  expect(await page.evaluate(() => navigator.clipboard.readText())).toBe('uvx gsc-mcp-tools')
})

test('switches the complete landing between English and French', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('link', { name: 'FR', exact: true }).click()
  await expect(page).toHaveURL('/fr/')
  await expect(page.locator('html')).toHaveAttribute('lang', 'fr')
  await expect(page.getByRole('heading', { level: 1 })).toContainText('Améliorez votre référencement')
  await expect(page.getByRole('link', { name: 'Documentation', exact: true }).first()).toHaveAttribute('href', '/fr/docs/')
  await page.getByRole('link', { name: 'EN', exact: true }).click()
  await expect(page).toHaveURL('/')
  await expect(page.locator('html')).toHaveAttribute('lang', 'en')
})

test('localizes interactive feedback and controls on the French landing', async ({ page, context }) => {
  await context.grantPermissions(['clipboard-read', 'clipboard-write'])
  await page.goto('/fr/')
  const hero = page.locator('.hero')
  await hero.getByRole('button', { name: 'Copier la commande uvx' }).click()
  await expect(hero.getByRole('status')).toHaveText('Commande copiée.')
  await expect(page.getByRole('button', { name: 'Passer au thème sombre' })).toBeVisible()
  await page.setViewportSize({ width: 390, height: 844 })
  const menu = page.locator('#mobile-menu-toggle')
  await expect(menu).toHaveAttribute('aria-label', 'Ouvrir la navigation')
  await menu.click()
  await expect(page.getByRole('dialog', { name: 'Navigation principale' })).toBeVisible()
  await expect(menu).toHaveAttribute('aria-label', 'Fermer la navigation')
})

test('copies every visible command and updates only its local status', async ({ page, context }) => {
  await context.grantPermissions(['clipboard-read', 'clipboard-write'])
  await page.goto('/')
  const copyControls = page.locator('[data-copy-command]')
  await expect(copyControls).toHaveCount(5)

  for (let index = 0; index < 5; index += 1) {
    await page.goto('/')
    const button = copyControls.nth(index)
    const command = await button.getAttribute('data-copy-command')
    const statusId = await button.getAttribute('aria-controls')
    expect(command).toBeTruthy()
    expect(statusId).toBeTruthy()
    await button.click()
    await expect(page.locator(`#${statusId}`)).toHaveText('Command copied.')
    expect(await page.evaluate(() => navigator.clipboard.readText())).toBe(command)
    await expect(page.locator('[data-copy-status]').filter({ hasNotText: 'Command copied.' })).toHaveCount(4)
  }
})

test('keeps the failed command visible and isolates its error feedback', async ({ page }) => {
  await page.addInitScript(() => {
    Object.defineProperty(navigator, 'clipboard', {
      value: { writeText: () => Promise.reject(new Error('denied')) },
      configurable: true,
    })
  })
  await page.goto('/')
  const verification = page.locator('#install-verify')
  await verification.getByRole('button', { name: 'Copy verification command' }).click()
  await expect(verification.getByRole('status')).toHaveText('Copy failed. Select the command manually.')
  await expect(verification.getByText('gsc-cli list', { exact: true })).toBeVisible()
  await expect(page.locator('[data-copy-status]').filter({ hasNotText: 'Copy failed. Select the command manually.' })).toHaveCount(4)
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
  await page.emulateMedia({ colorScheme: 'light' })
  await page.goto('/')
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'light')
  await page.getByRole('button', { name: 'Switch to dark theme' }).click()
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark')
  await expect(page.getByRole('button', { name: 'Switch to light theme' })).toBeVisible()
})

test('keeps one desktop intent panel open and restores trigger focus', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 1000 })
  await page.goto('/')
  const analyze = page.getByRole('button', { name: 'Analyze' })
  const start = page.getByRole('button', { name: 'Start' })
  await analyze.click()
  await expect(analyze).toHaveAttribute('aria-expanded', 'true')
  await start.click()
  await expect(analyze).toHaveAttribute('aria-expanded', 'false')
  await expect(start).toHaveAttribute('aria-expanded', 'true')
  await page.keyboard.press('Escape')
  await expect(start).toHaveAttribute('aria-expanded', 'false')
  await expect(start).toBeFocused()
})

test('enters a desktop panel with ArrowDown and closes on outside click', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 1000 })
  await page.goto('/')
  const resources = page.getByRole('button', { name: 'Resources' })
  await resources.focus()
  await page.keyboard.press('ArrowDown')
  await expect(page.getByRole('link', { name: /Open the repository/ })).toBeFocused()
  await page.mouse.click(10, 900)
  await expect(resources).toHaveAttribute('aria-expanded', 'false')
})

test('keeps the compact desktop install action at least 44px high', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 1000 })
  await page.goto('/')
  const install = page.locator('.header-install')
  await expect(install).toBeVisible()
  const box = await install.boundingBox()
  expect(box).not.toBeNull()
  expect(box!.height).toBeGreaterThanOrEqual(44)
})

test('opens a contained mobile dialog and restores menu focus', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/')
  const menu = page.getByRole('button', { name: 'Open navigation' })
  await menu.click()
  const navigation = page.getByRole('dialog', { name: 'Primary navigation' })
  await expect(navigation).toBeVisible()
  await expect(navigation).toHaveAttribute('aria-modal', 'true')
  await expect(page.locator('body')).toHaveAttribute('data-nav-open', '')
  await expect(page.getByRole('button', { name: 'Close navigation' }).last()).toBeFocused()
  await page.keyboard.press('Shift+Tab')
  await expect(page.getByRole('button', { name: /Switch to/ })).toBeFocused()
  await page.keyboard.press('Tab')
  await expect(navigation.getByRole('button', { name: 'Close navigation' })).toBeFocused()
  await expect(page.locator('body')).toHaveCSS('overflow', 'hidden')
  await page.locator('[data-nav-backdrop]').click({ position: { x: 10, y: 10 } })
  await expect(navigation).not.toBeVisible()
  await expect(menu).toBeFocused()
  await menu.click()
  await page.getByRole('button', { name: 'Analyze' }).click()
  const googleLink = page.getByRole('link', { name: /Google data/ })
  await googleLink.focus()
  await page.keyboard.press('Enter')
  await expect(navigation).not.toBeVisible()
  const destination = page.locator('#provider-google')
  await expect(destination).toBeFocused()
  await expect(destination).toHaveAttribute('tabindex', '-1')
  await menu.focus()
  await expect(destination).not.toHaveAttribute('tabindex', '-1')
})

test('restores mobile menu focus after keyboard activation of an external link', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/')
  const menu = page.getByRole('button', { name: 'Open navigation' })
  await menu.focus()
  await page.keyboard.press('Enter')
  const navigation = page.getByRole('dialog', { name: 'Primary navigation' })
  const repository = navigation.getByRole('link', { name: 'GitHub (opens in a new tab)', exact: true })
  await expect(repository).toHaveAttribute('target', '_blank')
  // Cancel only the browser destination; the site's click handler still runs.
  await repository.evaluate((link) => link.addEventListener('click', (event) => event.preventDefault(), { once: true }))
  await repository.focus()
  await expect(repository).toBeFocused()
  await page.keyboard.press('Enter')
  await expect(navigation).not.toBeVisible()
  await expect(menu).toBeVisible()
  await expect(menu).toBeFocused()
  await expect(page).toHaveURL('/')
})

test('clears mobile navigation state when crossing to desktop', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/')
  await page.getByRole('button', { name: 'Open navigation' }).click()
  await expect(page.getByRole('dialog', { name: 'Primary navigation' })).toBeVisible()
  await page.setViewportSize({ width: 1440, height: 1000 })
  await expect(page.locator('body')).not.toHaveAttribute('data-nav-open', '')
  await expect(page.getByRole('button', { name: 'Analyze' })).toHaveAttribute('aria-expanded', 'false')
  await expect(page.locator('#primary-navigation')).not.toHaveAttribute('aria-modal', 'true')
  await page.setViewportSize({ width: 390, height: 844 })
  await expect(page.getByRole('navigation', { name: 'Primary navigation' })).not.toBeVisible()
})

test('closes the mobile drawer with Escape and its close button', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/')
  const menu = page.getByRole('button', { name: 'Open navigation' })
  await menu.click()
  await page.keyboard.press('Escape')
  await expect(page.getByRole('dialog')).toHaveCount(0)
  await expect(menu).toBeFocused()
  await menu.click()
  await page.getByRole('dialog').getByRole('button', { name: 'Close navigation' }).click()
  await expect(menu).toBeFocused()
  await expect(page.locator('body')).not.toHaveAttribute('data-nav-open', '')
})

test('neutralizes motion when reduced motion is requested', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' })
  await page.goto('/')
  const motion = await page.getByRole('button', { name: 'Switch to dark theme' }).evaluate((node) => ({
    transition: getComputedStyle(node).transitionDuration,
    animation: getComputedStyle(node).animationDuration,
    scroll: getComputedStyle(document.documentElement).scrollBehavior,
  }))
  expect(parseFloat(motion.transition)).toBeLessThanOrEqual(0.00001)
  expect(parseFloat(motion.animation)).toBeLessThanOrEqual(0.00001)
  expect(motion.scroll).toBe('auto')
})

for (const theme of ['light', 'dark'] as const) {
  for (const width of [390, 1440]) {
    test(`has no undocumented axe violations in ${theme} at ${width}px`, async ({ page }) => {
      await page.setViewportSize({ width, height: 1000 })
      await page.addInitScript((value) => localStorage.setItem('theme', value), theme)
      await page.goto('/')
      for (const open of [false, true]) {
        if (open) {
          if (width === 390) await page.getByRole('button', { name: 'Open navigation' }).click()
          await page.getByRole('button', { name: 'Analyze' }).click()
        }
        const results = await new AxeBuilder({ page }).analyze()
        expect(results.violations, JSON.stringify(results.violations, null, 2)).toEqual([])
      }
    })
  }
}

for (const theme of ['light', 'dark'] as const) {
  for (const width of [390, 1440]) {
    test(`has no undocumented axe violations in French ${theme} at ${width}px`, async ({ page }) => {
      await page.setViewportSize({ width, height: 1000 })
      await page.addInitScript((value) => localStorage.setItem('theme', value), theme)
      await page.goto('/fr/')
      const results = await new AxeBuilder({ page }).analyze()
      expect(results.violations, JSON.stringify(results.violations, null, 2)).toEqual([])
    })
  }
}

for (const width of [390, 768, 800, 1024, 1280, 1440]) {
  test(`contains the document without horizontal overflow at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 })
    await page.goto('/')
    const metrics = await page.evaluate(() => ({
      scrollWidth: document.documentElement.scrollWidth,
      clientWidth: document.documentElement.clientWidth,
      heroColumns: getComputedStyle(document.querySelector<HTMLElement>('.hero-grid')!).gridTemplateColumns.split(' ').length,
    }))
    expect(metrics.scrollWidth).toBeLessThanOrEqual(metrics.clientWidth)
    expect(metrics.heroColumns).toBe(width <= 800 ? 1 : 2)
    if (width < 1024) {
      await expect(page.getByRole('button', { name: 'Open navigation' })).toBeVisible()
      await expect(page.locator('#primary-navigation')).not.toBeVisible()
    } else {
      await expect(page.getByRole('button', { name: 'Analyze' })).toBeVisible()
      await expect(page.getByRole('button', { name: 'Open navigation' })).not.toBeVisible()
    }
  })
}

for (const width of [390, 768, 800, 1024, 1280, 1440]) {
  test(`contains the French landing without horizontal overflow at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 })
    await page.goto('/fr/')
    const metrics = await page.evaluate(() => ({
      scrollWidth: document.documentElement.scrollWidth,
      clientWidth: document.documentElement.clientWidth,
    }))
    expect(metrics.scrollWidth).toBeLessThanOrEqual(metrics.clientWidth)
  })
}

test('distinguishes an open FAQ item beyond its icon', async ({ page }) => {
  await page.goto('/')
  const item = page.locator('[data-faq-item]').first()
  const closedBorder = await item.evaluate((node) => getComputedStyle(node).borderLeftWidth)
  await item.locator('summary').click()
  await expect(item).toHaveAttribute('open', '')
  const openBorder = await item.evaluate((node) => getComputedStyle(node).borderLeftWidth)
  expect(openBorder).not.toBe(closedBorder)
})

test('keeps the mobile document contained and controls large enough', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/')
  await page.getByRole('button', { name: 'Open navigation' }).click()
  await expect(page.getByRole('dialog')).toBeVisible()
  await page.getByRole('button', { name: 'Analyze' }).click()
  const dimensions = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    clientWidth: document.documentElement.clientWidth,
    targets: [...document.querySelectorAll('a, button, summary')]
      .filter((node) => node.getClientRects().length > 0)
      .map((node) => ({ text: node.textContent, height: node.getBoundingClientRect().height, width: node.getBoundingClientRect().width })),
  }))
  expect(dimensions.scrollWidth).toBeLessThanOrEqual(dimensions.clientWidth)
  expect(dimensions.targets.filter(({ height, width }) => height < 44 || width < 44)).toEqual([])
})

test('shows a visible keyboard focus', async ({ page }) => {
  await page.goto('/')
  await page.keyboard.press('Tab')
  const skipLink = page.getByRole('link', { name: 'Skip to main content' })
  await expect(skipLink).toBeFocused()
  expect(await skipLink.evaluate((node) => getComputedStyle(node).outlineWidth)).toBe('2px')
})

test('navigates the bilingual documentation without leaving the site', async ({ page }) => {
  await page.goto('/docs/')
  await expect(page.getByRole('heading', { level: 1, name: 'Search Console MCP documentation' })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Search' })).toBeEnabled()
  await page.getByRole('banner').getByLabel('Select language').selectOption('/fr/docs/')
  await expect(page).toHaveURL('/fr/docs/')
  await expect(page.getByRole('heading', { level: 1, name: 'Documentation Search Console MCP' })).toBeVisible()
  await expect(page.locator('html')).toHaveAttribute('lang', 'fr')
})

test('keeps the editorial profile and paired language route available', async ({ page }) => {
  await page.goto('/docs/editorial-audit/')
  await expect(page.locator('main')).toContainText('anti-ai-editorial')
  await expect(page.locator('main')).toContainText('repeated_paragraph_start')
  await page.getByRole('banner').getByLabel('Select language').selectOption('/fr/docs/editorial-audit/')
  await expect(page).toHaveURL('/fr/docs/editorial-audit/')
  await expect(page.getByRole('heading', { level: 1, name: 'Audit éditorial et réécriture fidèle' })).toBeVisible()
  await expect(page.locator('main')).toContainText('not_assessed')
})

test('returns from the documentation to the product home', async ({ page }) => {
  await page.goto('/fr/docs/')
  const brand = page.getByRole('banner').getByRole('link', { name: 'Accueil du site Search Console MCP' })
  await expect(brand).toHaveAttribute('href', '/fr/')
  await expect(brand.getByText('← Accueil')).toBeVisible()
  await brand.click()
  await expect(page).toHaveURL('/fr/')
  await expect(page.getByRole('heading', { level: 1 })).toContainText('Améliorez votre référencement')
})

for (const route of ['/docs/examples/quick-audit/', '/fr/docs/']) {
  for (const theme of ['light', 'dark'] as const) {
    for (const width of [390, 1440]) {
      test(`keeps documentation typography readable on ${route} in ${theme} at ${width}px`, async ({ page }) => {
        await page.setViewportSize({ width, height: 1000 })
        await page.addInitScript((selectedTheme) => localStorage.setItem('starlight-theme', selectedTheme), theme)
        await page.goto(route)

        const sizes = await page.evaluate(() => {
          const fontSize = (selector: string) => {
            const element = document.querySelector<HTMLElement>(selector)
            if (!element) throw new Error(`Missing typography target: ${selector}`)
            return Number.parseFloat(getComputedStyle(element).fontSize)
          }

          return {
            title: fontSize('main h1'),
            section: fontSize('.sl-markdown-content h2'),
            pagination: fontSize('.pagination-links .link-title'),
            body: fontSize('.sl-markdown-content p'),
          }
        })

        expect(sizes.title).toBeLessThanOrEqual(44)
        expect(sizes.section).toBeLessThanOrEqual(28)
        expect(sizes.pagination).toBeLessThanOrEqual(18)
        expect(sizes.body).toBe(16)
      })
    }
  }
}

for (const route of ['/docs/', '/docs/installation/', '/docs/examples/quick-audit/', '/docs/editorial-audit/', '/fr/docs/', '/fr/docs/installation/', '/fr/docs/examples/quick-audit/', '/fr/docs/editorial-audit/']) {
  test(`keeps ${route} accessible and contained on mobile`, async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 })
    await page.goto(route)
    const metrics = await page.evaluate(() => ({
      scrollWidth: document.documentElement.scrollWidth,
      clientWidth: document.documentElement.clientWidth,
    }))
    expect(metrics.scrollWidth).toBeLessThanOrEqual(metrics.clientWidth)
    await page.waitForFunction(() => [...document.querySelectorAll<HTMLElement>('.expressive-code pre')]
      .every((block) => block.scrollWidth <= block.clientWidth || block.tabIndex === 0))
    const results = await new AxeBuilder({ page }).analyze()
    expect(results.violations, JSON.stringify(results.violations, null, 2)).toEqual([])
  })
}

test.describe('local visual baselines', () => {
  test.skip(!!process.env.CI, 'Reviewed Chromium/macOS baselines are only compared locally.')

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

  for (const theme of ['light', 'dark'] as const) {
    for (const viewport of [{ width: 390, height: 844 }, { width: 1440, height: 1000 }]) {
      test(`matches French ${theme} ${viewport.width}px baseline`, async ({ page }) => {
        await page.setViewportSize(viewport)
        await page.addInitScript((selectedTheme) => localStorage.setItem('theme', selectedTheme), theme)
        await page.goto('/fr/')
        await expect(page).toHaveScreenshot(`fr-${theme}-${viewport.width}.png`, {
          fullPage: true,
          animations: 'disabled',
        })
      })
    }
  }

  test('matches the open desktop menu baseline', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 1000 })
    await page.goto('/')
    await page.getByRole('button', { name: 'Analyze' }).click()
    await expect(page).toHaveScreenshot('menu-analyze-1440.png', { animations: 'disabled' })
  })

  test('matches the open mobile drawer baseline', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 })
    await page.goto('/')
    await page.getByRole('button', { name: 'Open navigation' }).click()
    await expect(page).toHaveScreenshot('menu-mobile-390.png', { animations: 'disabled' })
  })

  test('matches the open FAQ baseline', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 1000 })
    await page.goto('/')
    const faq = page.locator('#faq')
    await faq.locator('[data-faq-item]').first().locator('summary').click()
    await expect(faq).toHaveScreenshot('faq-open-1440.png', { animations: 'disabled' })
  })

  test('matches the mobile install feedback baseline', async ({ page, context }) => {
    await context.grantPermissions(['clipboard-read', 'clipboard-write'])
    await page.setViewportSize({ width: 390, height: 844 })
    await page.addInitScript(() => localStorage.setItem('theme', 'dark'))
    await page.goto('/')
    const verification = page.locator('#install-verify')
    await verification.getByRole('button', { name: 'Copy verification command' }).click()
    await expect(verification).toHaveScreenshot('install-feedback-dark-390.png', { animations: 'disabled' })
  })

  for (const locale of [{ route: '/docs/', name: 'docs-en' }, { route: '/fr/docs/', name: 'docs-fr' }]) {
    for (const viewport of [{ width: 390, height: 844 }, { width: 1440, height: 1000 }]) {
      test(`matches ${locale.name} ${viewport.width}px baseline`, async ({ page }) => {
        await page.setViewportSize(viewport)
        await page.addInitScript(() => localStorage.setItem('starlight-theme', 'light'))
        await page.goto(locale.route)
        await expect(page).toHaveScreenshot(`${locale.name}-${viewport.width}.png`, {
          fullPage: true,
          animations: 'disabled',
          maxDiffPixels: viewport.width === 390 ? 200 : 0,
        })
      })
    }
  }
})
