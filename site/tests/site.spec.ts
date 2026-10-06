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
  await page.getByRole('link', { name: /Google data/ }).click()
  await expect(navigation).not.toBeVisible()
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
    test(`has no serious or critical axe violations in ${theme} at ${width}px`, async ({ page }) => {
      await page.setViewportSize({ width, height: 1000 })
      await page.addInitScript((value) => localStorage.setItem('theme', value), theme)
      await page.goto('/')
      for (const open of [false, true]) {
        if (open) {
          if (width === 390) await page.getByRole('button', { name: 'Open navigation' }).click()
          await page.getByRole('button', { name: 'Analyze' }).click()
        }
        const results = await new AxeBuilder({ page }).analyze()
        const blockers = results.violations.filter(({ impact }) => impact === 'serious' || impact === 'critical')
        expect(blockers, JSON.stringify(blockers, null, 2)).toEqual([])
      }
    })
  }
}

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
