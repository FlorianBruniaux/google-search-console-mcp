# Bilingual documentation portal design

| Field | Value |
| --- | --- |
| Status | Approved in chat |
| Date | 2026-10-06 |
| Repository | `FlorianBruniaux/google-search-console-mcp` |
| Public URL | `https://search-console.bruniaux.com/` |

## Decision

Extend the existing Astro site with a Starlight documentation portal. English remains the canonical documentation and is served under `/docs/`. A maintained French edition is served under `/fr/docs/`. The existing product landing page remains at `/` and keeps its current custom BoldGuy interface.

The English portal is generated at build time from an explicit allowlist spanning the repository files under `docs/`, `examples/`, `CHANGELOG.md`, and `LICENSE`, plus two portal-only source pages under `site/content/en/`: the documentation home and the evidence-and-safety guide. The generated Starlight collection is not edited by hand. French source files are maintained separately under `site/content/fr/`, use the same route names as the English edition, and are copied into the generated collection by the same build step.

## Product goal

Readers must be able to install, configure, understand, and operate Search Console MCP without leaving the public website for routine documentation. GitHub remains the source-code destination, not the default reading interface.

The portal must help a reader complete five paths:

1. Install the package without creating duplicate long-running MCP processes.
2. Configure Google Search Console and optional Google services.
3. Configure Bing Webmaster Tools and understand the separate IndexNow key.
4. Run a first bounded audit or one of the scenario prompts.
5. Interpret observed, derived, requested, crawled, and indexed states without conflating them.

## Audience and language model

English is canonical because the package, source documentation, CLI, tool names, and error messages are currently written in English. French is a maintained user-facing edition, not an automatic browser translation.

The public routes are:

- English: `/docs/…`
- French: `/fr/docs/…`

Starlight's locale selector associates pages by matching route names. A missing French translation may use Starlight's explicit English fallback notice, but the initial release must provide French versions for every page linked from the primary documentation navigation.

The custom landing page remains English. Its header, menu, footer, and calls to action link to the English portal. The portal itself exposes the language selector and a visible link back to the product landing page.

## Published information architecture

### Start

- `/docs/` and `/fr/docs/`: task-oriented documentation home.
- `/docs/installation/` and `/fr/docs/installation/`: installation, upgrades, client setup, process limits, and verification.
- `/docs/google-setup/` and `/fr/docs/google-setup/`: Google credentials and optional GA4 or CrUX setup.
- `/docs/bing-setup/` and `/fr/docs/bing-setup/`: Bing account key, verified sites, and IndexNow separation.

### Use

- `/docs/prompts/` and `/fr/docs/prompts/`: first audit prompts.
- `/docs/examples/` and `/fr/docs/examples/`: scenario index.
- Matching pages for `quick-audit`, `google-bing-comparison`, `full-audit`, `keyword-opportunities`, `page-deep-dive`, `traffic-drop`, `indexing-issues`, and `content-brief`.

### Understand

- `/docs/architecture/` and `/fr/docs/architecture/`: server, providers, data boundaries, and write tools.
- `/docs/evidence-and-safety/` and `/fr/docs/evidence-and-safety/`: user-facing evidence vocabulary and mutation safeguards.

### Project

- `/docs/changelog/` and `/fr/docs/changelog/`: full canonical release history in English and a maintained French release summary.
- `/docs/license/` and `/fr/docs/license/`: MIT license and a plain-language usage note. The license text itself stays unmodified.

## Excluded content

The portal must not publish these repository areas:

- `docs/superpowers/`
- `docs/machine-readable/`
- `docs/validation/`
- raw audit evidence, canary outputs, local credentials, or environment files
- internal implementation plans and session handoffs

The user-facing evidence and safety page may summarize stable product contracts. It must not expose a raw validation report as a public navigation destination.

## Source synchronization

`site/scripts/prepare-doc-content.mjs` owns the generated Starlight collection.

It performs these operations:

1. Empty only `site/src/content/docs/`, which is generated and ignored by Git.
2. Create the English route tree from an explicit allowlist of canonical repository files and portal-only English source pages.
3. Add validated Starlight frontmatter and remove the duplicate source H1.
4. Rewrite known relative Markdown links to their public documentation routes.
5. Copy the French source tree from `site/content/fr/` to matching `fr/docs/` routes.
6. Fail if an allowlisted source is missing, a rewritten internal link has no mapped route, or a primary French page is missing.

The script may not discover and publish all Markdown files recursively. The allowlist is the publication boundary.

The build commands run documentation preparation before Astro type checking, development, and production builds. A clean checkout must produce the same route set without committing generated Markdown.

## French maintenance contract

French pages are written for clarity rather than generated during the build. Code, environment-variable names, CLI commands, JSON keys, tool names, and provider error strings remain literal.

Every French page carries:

- the same route identifier as its English source;
- a visible link to the canonical English page;
- a `lastUpdated` date;
- a source reference in a build-only manifest.

`site/content/fr/manifest.json` maps each French page to its canonical source. The preparation test fails when a required route is absent from the manifest. Source hashes are recorded when the French page is reviewed. A changed English hash does not silently fail the public build; it produces a visible stale-translation report in the test output and fails the release verification command until the manifest is refreshed.

## Starlight integration

Use `@astrojs/starlight` `0.42.5`, verified from the npm registry on 2026-10-06, with the existing Astro `5.17.1` project.

Configuration requirements:

- Root locale: English, `lang: en`.
- French locale: `fr`, `lang: fr`.
- Built-in Pagefind search enabled for production builds.
- Explicit sidebar groups matching the information architecture above.
- GitHub social link retained as a source-code destination.
- Custom `SiteTitle` component linking English pages to `/` and French pages to `/fr/docs/`.
- Existing favicon and canonical site URL retained.
- Existing sitemap integration must include all public documentation routes.

The default Starlight header, mobile navigation, language selector, search, sidebar, table of contents, pagination, and theme control remain responsible for their native behavior. Only the site title and visual tokens are overridden.

## BoldGuy visual adaptation

`site/src/styles/starlight-overrides.css` maps Starlight semantic variables to the existing site tokens:

- warm light backgrounds and neutral dark backgrounds;
- orange accent for active links, focus, and primary actions;
- system UI and monospace stacks already used by the landing page;
- thin borders, restrained shadows, and 8 to 12 px radii;
- terminal blocks that stay dark in both themes;
- 44 px interactive targets and a visible 2 px focus ring.

Documentation content remains left aligned with readable line length. Desktop shows sidebar, main article, and table of contents. Mobile uses Starlight's native navigation drawer and mobile table of contents.

## Visual content

Use Gemini for two conceptual editorial illustrations only:

1. `search-evidence-map`: three visually distinct evidence streams, Google search data, Bing search data, and public-page signals, converging on a bounded AI assistant workspace.
2. `guarded-action-loop`: an assistant reading evidence, comparing providers, explaining limits, and asking for confirmation before one bounded submission.

The images contain no body text, numbers, product claims, logos, API keys, or exact arrows that readers must interpret. Their meaning is supplied by adjacent HTML headings, captions, and alt text. This avoids treating stochastic image text as documentation.

Exact provider boundaries and evidence states are rendered with deterministic HTML and CSS, not baked into raster images.

Each final visual must:

- pass full-size visual inspection;
- remain legible at article width and on a 390 px viewport;
- use the BoldGuy warm light palette with a dark technical surface;
- be exported as an optimized WebP while preserving the native Gemini output for audit outside the public build;
- include descriptive alt text and a caption;
- avoid decorative duplication on narrow screens when it would push the task content below the fold.

The automatic attempt ceiling is two Gemini calls per visual. A recurring text, cropping, or composition defect stops further paid retries.

## Landing-page corrections

Replace GitHub Markdown destinations with public documentation routes for:

- installation;
- Google setup;
- Bing setup;
- starter prompts and examples;
- changelog;
- architecture;
- evidence and safety.

GitHub and PyPI remain external links. The MIT license may be read on the public documentation page, with the repository file linked as the legal source.

Add a `Docs` destination to the header and footer. The landing page must expose the French documentation entry without pretending that the landing itself is translated.

## SEO and structured content

Every documentation page must have:

- a unique title and description;
- a self-referencing canonical URL;
- correct `lang` value;
- English/French locale association generated by Starlight;
- one visible H1 supplied by Starlight;
- crawlable internal links to the next relevant task;
- inclusion in the XML sitemap unless explicitly excluded.

The documentation portal makes no ranking, traffic, crawl, or indexation guarantee. Deployment and an HTTP 200 do not prove indexing.

## Accessibility and responsive acceptance

The release is accepted when:

- keyboard users can reach search, language, sidebar, table of contents, copy controls, and links;
- focus remains visible in light and dark themes;
- headings follow a valid hierarchy;
- code blocks scroll without causing document-level overflow;
- tables have their own horizontal overflow container;
- there is no document-level horizontal overflow at 390, 768, 1024, or 1440 px;
- automated axe checks report no violations on the documentation home, one setup page, one example, and their French equivalents;
- the two themes render correctly at 390 and 1440 px;
- all primary tap targets measure at least 44 px.

## Verification boundary

Local acceptance requires:

- documentation preparation tests;
- Astro check and production build;
- rendered route and link tests against `site/dist`;
- Playwright navigation, search, locale, responsive, theme, and accessibility tests;
- visual snapshots for the English and French documentation homes;
- full Python test suite because the build exporter remains part of deployment;
- `git diff --check`.

Production acceptance requires:

- GitHub Pages workflow success for the intended commit;
- public HTTP checks for representative English and French routes;
- public asset checks for both Gemini illustrations;
- `deployment.json` matching the deployed commit;
- sitemap entries for the documentation routes.

Search-engine indexing and user engagement remain unknown until measured separately.

## Rollback

The implementation stays within `site/`, the documentation plan/spec indexes, and landing-page link data. A revert of the documentation commits returns the site to the one-page build. The GitHub Pages custom domain and workflow remain valid because the landing page continues to build at the same origin.
