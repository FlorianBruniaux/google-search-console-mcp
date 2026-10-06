# Bilingual Documentation Portal Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task by task. Steps use checkbox syntax for progress tracking.

**Goal:** Publish the repository's user documentation as a searchable English and French Starlight portal without exposing internal files or duplicating canonical English content.

**Architecture:** A deterministic preparation script maps an explicit source allowlist into Starlight's generated content collection. English stays canonical in the repository. French pages live under `site/content/fr/` and carry source-hash metadata. The existing Astro landing remains custom and links into the documentation routes.

**Tech stack:** Astro 5.17.1, Starlight 0.37.7, TypeScript, Node test runner, Playwright, axe-core, GitHub Pages.

**Spec:** `docs/superpowers/specs/2026-10-06-bilingual-docs-portal-design.md`

## Global constraints

- [x] Preserve unrelated untracked files and stage only scoped paths.
- [x] Never recursively publish Markdown. Every public source must be allowlisted.
- [x] Keep `docs/superpowers/`, `docs/machine-readable/`, and `docs/validation/` outside the public build.
- [x] Keep English routes under `/docs/` and French routes under `/fr/docs/`.
- [x] Do not claim deployment, crawl, indexation, or traffic without separate proof.

## Task 1: Lock the publication boundary

**Files:**

- Create: `site/scripts/prepare-doc-content.mjs`
- Create: `site/tests/doc-content-source.test.mjs`
- Create: `site/content/en/index.md`
- Create: `site/content/en/evidence-and-safety.md`
- Modify: `site/package.json`
- Modify: `.gitignore`

- [x] Write a failing Node test for the complete route set, rejected internal paths, missing sources, and broken mapped links.
- [x] Implement an explicit source-to-route manifest and generated-directory cleanup.
- [x] Normalize frontmatter, remove duplicate source H1 headings, and rewrite known internal Markdown links.
- [x] Add preparation to `dev`, `check`, and `build` scripts.
- [x] Prove that a clean generation contains no excluded path.

## Task 2: Add the Starlight shell

**Files:**

- Modify: `site/package.json`
- Modify: `site/pnpm-lock.yaml`
- Modify: `site/astro.config.mjs`
- Create: `site/src/content.config.ts`
- Create: `site/src/components/docs/SiteTitle.astro`
- Create: `site/src/styles/starlight-overrides.css`
- Modify: `site/tests/dist-content.test.mjs`
- Modify: `site/tests/dist-seo.test.mjs`

- [x] Add failing distribution tests for representative EN/FR routes, language metadata, sitemap entries, and canonical links.
- [x] Install Starlight 0.37.7, the latest Astro 5-compatible release, and configure English root plus French locale.
- [x] Configure explicit sidebars for Start, Use, Understand, and Project.
- [x] Adapt Starlight tokens to the BoldGuy system without replacing native accessible behavior.
- [x] Build and prove the expected route tree.

## Task 3: Publish the maintained French edition

**Files:**

- Create: `site/content/fr/manifest.json`
- Create: `site/content/fr/**/*.md`
- Modify: `site/tests/doc-content-source.test.mjs`

- [x] Add failing tests for route parity, manifest coverage, canonical-source links, and recorded hashes.
- [x] Translate every page linked from the primary sidebar, preserving literal commands and identifiers.
- [x] Translate all eight scenario examples and add task-oriented cross-links.
- [x] Report stale hashes in normal preparation and fail them in `verify:translations`.
- [x] Verify that no French page silently substitutes an unpublished internal source.

## Task 4: Move landing navigation onto the site

**Files:**

- Modify: `site/src/data/content.ts`
- Modify: `site/src/data/navigation.ts`
- Modify: `site/src/components/SiteHeader.astro`
- Modify: `site/src/components/SiteFooter.astro`
- Modify: `site/tests/site.spec.ts`
- Modify: `site/tests/dist-content.test.mjs`

- [x] Add failing tests asserting that documentation links are internal and GitHub remains the source destination.
- [x] Replace seven GitHub Markdown links with public documentation routes.
- [x] Add visible Docs and Documentation FR entries in the header and footer.
- [x] Keep repository, PyPI, portfolio, and ecosystem links external with explicit semantics.

## Task 5: Add bounded visual guidance

**Files:**

- Create: `site/public/images/docs/*.webp`
- Create: `docs/assets/gemini/native/*.jpg`
- Create: `docs/assets/gemini/prompts/*.md`
- Modify: English and French portal pages using the visuals
- Modify: `site/tests/doc-content-source.test.mjs`

- [x] Build exact labels, states, and arrows as semantic HTML and CSS inside the documentation pages.
- [x] Generate two conceptual Gemini illustrations with one successful call per illustration.
- [x] Keep native outputs outside the public build and publish optimized WebP assets only.
- [x] Add descriptive alt text, captions, and mobile-safe presentation.
- [x] Test asset existence and reject images without alt text or captions.

## Task 6: Verify and deliver

**Files:**

- Modify: `README.md`
- Modify: `CHANGELOG.md`
- Modify: `site/tests/site.spec.ts`
- Modify: `docs/superpowers/plans/README.md`

- [x] Run documentation source tests and translation freshness verification.
- [x] Run Astro check, production build, distribution tests, Playwright, axe, and visual snapshots.
- [x] Run the full Python test suite and `git diff --check`.
- [x] Inspect representative EN/FR pages at 390 and 1440 px.
- [x] Commit with explicit pathspecs.
- [ ] Push the feature branch and main only with user authorization, then verify the remote SHA and GitHub Pages deployment separately.

## Acceptance evidence

- [x] `/docs/`, `/docs/installation/`, `/docs/examples/`, and `/docs/evidence-and-safety/` return built HTML.
- [x] Matching `/fr/docs/` routes return French content with `lang="fr"`.
- [x] Search, sidebar, page table of contents, theme control, and language navigation work by keyboard.
- [x] No landing documentation link defaults to a GitHub Markdown blob.
- [x] No internal plan, machine-readable export, or raw validation report appears in `site/dist` or the sitemap.
- [ ] Public deployment proof is tied to the intended commit; indexing remains `UNKNOWN`.
