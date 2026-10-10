type Theme = 'light' | 'dark'

const desktopQuery = matchMedia('(min-width: 72rem)')
const siteHeader = document.querySelector<HTMLElement>('[data-site-header]')
const navigation = document.querySelector<HTMLElement>('#primary-navigation')
const menuButton = document.querySelector<HTMLButtonElement>('#mobile-menu-toggle')
const closeButton = document.querySelector<HTMLButtonElement>('[data-mobile-menu-close]')
const backdrop = document.querySelector<HTMLElement>('[data-nav-backdrop]')
const sections = [...document.querySelectorAll<HTMLDetailsElement>('[data-nav-section]')]
const focusableSelector = 'a[href], button:not([disabled]), summary, [tabindex]:not([tabindex="-1"])'

function setSectionOpen(section: HTMLDetailsElement, open: boolean): void {
  section.open = open
  section.querySelector<HTMLElement>('[data-nav-trigger]')?.setAttribute('aria-expanded', String(open))
}

function closeSections(except?: HTMLDetailsElement): void {
  sections.forEach((section) => {
    if (section !== except) setSectionOpen(section, false)
  })
}

function closeMobileNavigation(restoreFocus = true): void {
  if (!navigation || !menuButton || !backdrop) return
  document.body.removeAttribute('data-nav-open')
  menuButton.setAttribute('aria-expanded', 'false')
  menuButton.setAttribute('aria-label', menuButton.dataset.openLabel ?? 'Open navigation')
  navigation.removeAttribute('role')
  navigation.removeAttribute('aria-modal')
  backdrop.hidden = true
  closeSections()
  if (restoreFocus) menuButton.focus()
}

function openMobileNavigation(): void {
  if (!navigation || !menuButton || !backdrop) return
  document.body.setAttribute('data-nav-open', '')
  menuButton.setAttribute('aria-expanded', 'true')
  menuButton.setAttribute('aria-label', menuButton.dataset.closeLabel ?? 'Close navigation')
  navigation.setAttribute('role', 'dialog')
  navigation.setAttribute('aria-modal', 'true')
  navigation.setAttribute('aria-label', navigation.querySelector('nav')?.getAttribute('aria-label') ?? 'Primary navigation')
  backdrop.hidden = false
  closeButton?.focus()
}

function resetNavigation(): void {
  closeMobileNavigation(false)
  closeSections()
}

sections.forEach((section) => {
  const trigger = section.querySelector<HTMLElement>('[data-nav-trigger]')
  section.addEventListener('toggle', () => {
    if (section.open) closeSections(section)
    trigger?.setAttribute('aria-expanded', String(section.open))
  })
  trigger?.addEventListener('keydown', (event) => {
    if (event.key === 'ArrowDown' && desktopQuery.matches) {
      event.preventDefault()
      setSectionOpen(section, true)
      closeSections(section)
      section.querySelector<HTMLElement>('[data-nav-panel] a')?.focus()
    }
  })
})

menuButton?.addEventListener('click', () => {
  if (document.body.hasAttribute('data-nav-open')) closeMobileNavigation()
  else openMobileNavigation()
})
closeButton?.addEventListener('click', () => closeMobileNavigation())
backdrop?.addEventListener('click', () => closeMobileNavigation())
navigation?.querySelectorAll<HTMLAnchorElement>('a').forEach((link) => {
  link.addEventListener('click', () => {
    if (desktopQuery.matches) closeSections()
    else {
      const samePageTarget = link.origin === location.origin && link.pathname === location.pathname && link.hash
        ? document.getElementById(decodeURIComponent(link.hash.slice(1)))
        : null
      if (samePageTarget) {
        closeMobileNavigation(false)
        const needsTemporaryTabIndex = !samePageTarget.matches('a[href], button, input, select, textarea, [tabindex]')
        if (needsTemporaryTabIndex) {
          samePageTarget.setAttribute('tabindex', '-1')
          samePageTarget.addEventListener('blur', () => samePageTarget.removeAttribute('tabindex'), { once: true })
        }
        requestAnimationFrame(() => samePageTarget.focus())
      } else {
        closeMobileNavigation()
      }
    }
  })
})

document.addEventListener('click', (event) => {
  if (desktopQuery.matches && siteHeader && !siteHeader.contains(event.target as Node)) closeSections()
})

document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape') {
    if (!desktopQuery.matches && document.body.hasAttribute('data-nav-open')) {
      closeMobileNavigation()
      return
    }
    const openSection = sections.find((section) => section.open)
    if (openSection) {
      const trigger = openSection.querySelector<HTMLElement>('[data-nav-trigger]')
      setSectionOpen(openSection, false)
      trigger?.focus()
    }
  }

  if (event.key === 'Tab' && !desktopQuery.matches && document.body.hasAttribute('data-nav-open') && navigation) {
    const focusable = [...navigation.querySelectorAll<HTMLElement>(focusableSelector)].filter((node) => node.offsetParent !== null)
    const first = focusable.at(0)
    const last = focusable.at(-1)
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault()
      last?.focus()
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault()
      first?.focus()
    }
  }
})

desktopQuery.addEventListener('change', resetNavigation)

const root = document.documentElement
const themeButton = document.querySelector<HTMLButtonElement>('[data-theme-toggle]')

function currentTheme(): Theme {
  return root.dataset.theme === 'dark' ? 'dark' : 'light'
}

function syncThemeControl(): void {
  const next = currentTheme() === 'dark' ? 'light' : 'dark'
  if (themeButton) themeButton.setAttribute('aria-label', next === 'dark'
    ? themeButton.dataset.themeDarkLabel ?? 'Switch to dark theme'
    : themeButton.dataset.themeLightLabel ?? 'Switch to light theme')
}

themeButton?.addEventListener('click', () => {
  const next: Theme = currentTheme() === 'dark' ? 'light' : 'dark'
  root.dataset.theme = next
  try { localStorage.setItem('theme', next) } catch {}
  syncThemeControl()
})

syncThemeControl()

function revealSeoDetail(hash: string): boolean {
  const detail = document.getElementById(hash.slice(1))
  if (!(detail instanceof HTMLDetailsElement) || !detail.hasAttribute('data-seo-detail')) return false
  detail.open = true
  detail.querySelector('summary')?.focus({ preventScroll: true })
  detail.scrollIntoView({ block: 'start' })
  return true
}

document.addEventListener('click', (event) => {
  if (event.button || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey || !(event.target instanceof Element)) return
  const link = event.target.closest<HTMLAnchorElement>('a[href^="#seo-"]')
  if (!link || !revealSeoDetail(link.hash)) return
  event.preventDefault()
  if (location.hash !== link.hash) history.pushState(null, '', link.hash)
})
window.addEventListener('hashchange', () => revealSeoDetail(location.hash))
revealSeoDetail(location.hash)

document.querySelectorAll<HTMLButtonElement>('[data-copy-command], [data-copy-prompt]').forEach((button) => {
  button.addEventListener('click', async () => {
    const statusId = button.getAttribute('aria-controls')
    const status = statusId ? document.getElementById(statusId) : null
    try {
      await navigator.clipboard.writeText(button.dataset.copyPrompt ?? button.dataset.copyCommand ?? '')
      if (status) status.textContent = button.dataset.copyPrompt !== undefined
        ? root.lang === 'fr' ? 'Prompt copié.' : 'Prompt copied.'
        : root.lang === 'fr' ? 'Commande copiée.' : 'Command copied.'
    } catch {
      if (status) status.textContent = button.dataset.copyPrompt !== undefined
        ? root.lang === 'fr' ? 'Échec de la copie. Sélectionnez le prompt manuellement.' : 'Copy failed. Select the prompt manually.'
        : root.lang === 'fr' ? 'Échec de la copie. Sélectionnez la commande manuellement.' : 'Copy failed. Select the command manually.'
    }
  })
})
