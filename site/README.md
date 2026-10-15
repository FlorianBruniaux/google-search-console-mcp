# Public website

Astro publishes the English and French landing pages, HTML sitemaps, updates pages and Starlight documentation.

- [HTML sitemap component](src/components/DiscoveryPage.astro) groups public documentation from the generated collection. The publication allowlist stays in [prepare-doc-content.mjs](scripts/prepare-doc-content.mjs).
- [Updates page](src/pages/updates.astro) and [homepage banner](src/components/UpdatesBanner.astro) reuse the [canonical changelog](../CHANGELOG.md) and its [French summary](content/fr/docs/changelog.md). They distinguish unreleased source changes from released versions.
- The banner date comes from `<!-- unreleased-updated: YYYY-MM-DD -->` inside a nonempty Unreleased section. Update that date when adding changes. When Unreleased is empty, the banner shows the first dated release instead. Build time never becomes an update date.
- Update the French summary alongside the canonical changelog and refresh its source hash in [manifest.json](content/fr/manifest.json). Run `pnpm verify:translations` to detect stale summaries.

Run `pnpm verify` from this directory with the project Python environment active. It checks content, translations, types, generated pages, navigation, accessibility and browser screenshots. Review intentionally changed screenshots before accepting new baselines.

Public routes: `/sitemap/`, `/fr/sitemap/`, `/updates/`, `/fr/updates/`. Links are available from the resource menu, landing footer and documentation footer.

## Manual deployment

Repository policy permits owner-requested manual workflow runs. Pushes and merges do not publish the website. The site workflow accepts `workflow_dispatch` only, and both jobs require owner actor ID `3902606`, matching Python CI. A manual run on a reviewed branch builds and verifies the site; the publication job also requires `refs/heads/main` and a successful build.

After merging reviewed changes, the owner publishes `main` with:

```sh
gh workflow run site.yml --repo FlorianBruniaux/google-search-console-mcp --ref main
```

Follow the resulting run until both `build` and `deploy` succeed. Check the public `/deployment.json` against the intended commit and run ID, then verify the affected pages in HTTP and a browser. A successful build alone does not establish publication.

The automatic [run 38735231104](https://github.com/FlorianBruniaux/google-search-console-mcp/actions/runs/38735231104) failed before any job with `Event 'push' is not allowed to trigger Actions workflows.` The manual [run 38735368301](https://github.com/FlorianBruniaux/google-search-console-mcp/actions/runs/38735368301) built and published the same commit successfully. The correction removes the prohibited trigger without changing repository permissions or bypassing its execution policy.
