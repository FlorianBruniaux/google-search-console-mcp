# Public website

Astro publishes the English and French landing pages, HTML sitemaps, updates pages and Starlight documentation.

- [HTML sitemap component](src/components/DiscoveryPage.astro) groups public documentation from the generated collection. The publication allowlist stays in [prepare-doc-content.mjs](scripts/prepare-doc-content.mjs).
- [Updates page](src/pages/updates.astro) and [homepage banner](src/components/UpdatesBanner.astro) reuse the [canonical changelog](../CHANGELOG.md) and its [French summary](content/fr/docs/changelog.md). They distinguish unreleased source changes from released versions.
- The banner date comes from `<!-- unreleased-updated: YYYY-MM-DD -->` inside a nonempty Unreleased section. Update that date when adding changes. When Unreleased is empty, the banner shows the first dated release instead. Build time never becomes an update date.
- Update the French summary alongside the canonical changelog and refresh its source hash in [manifest.json](content/fr/manifest.json). Run `pnpm verify:translations` to detect stale summaries.

Run `pnpm verify` from this directory with the project Python environment active. It checks content, translations, types, generated pages, navigation, accessibility and browser screenshots. Review intentionally changed screenshots before accepting new baselines.

Public routes: `/sitemap/`, `/fr/sitemap/`, `/updates/`, `/fr/updates/`. Links are available from the resource menu, landing footer and documentation footer.
