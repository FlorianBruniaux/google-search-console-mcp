# PR #27 integration with the SEO expert feedback release

## Scope

The `codex/audit-followup-tools` branch integrates main `a77fc1f54663028a05aa490f0265475f46f45fb2` into previous head `0fc22ff259828bb5ecd57ee5f70ae873363511d6`. This combines #20, #23 and #24 with the released 1.3.1 fixes (#28 through #34). It does not merge the PR, publish a release or deploy the site.

## Conflict decisions

- Keep both the unreleased draft/rewrite/change-follow-up entries and the published 1.3.1 feedback fixes in EN/FR changelogs.
- Preserve optional startup MCP-family selection, CLI JSON string lists and all SEO/Bing feedback changes.
- Document 87 source tools separately from the 85-tool published 1.3.1 package. The package version stays 1.3.1; unreleased examples require a source installation.
- Reconcile EN/FR overview and architecture content, refresh reviewed translation source hashes, and regenerate only the four conflicted documentation screenshots from the combined built site.

## Local validation

- `uv run --frozen --extra dev pytest -q`: 1,649 passed on Python 3.13.
- Separate environment, Python 3.11.15: the same 1,649 tests passed.
- Site: 5 documentation-source tests, translation verification, zero Astro diagnostics, 47 built pages and 23 distribution tests passed.
- All 86 Chromium scenarios passed on a separate local preview port, including comparison with reviewed documentation screenshots. Four screenshot updates were inspected at desktop/mobile widths in EN/FR.
- `uv build` rebuilt wheel and sdist; `twine check` passed. All 43 packaged Python modules match the combined source bytes.
- An isolated installed Python 3.11 wheel passed draft editorial, protected-literal rewrite and unavailable future-observation CLI workflows.
- The installed wheel passed MCP stdio initialization, `tools/list` and `get_capabilities`: the full catalogue has 87 tools and the `seo,editorial` profile has 14, with matching capabilities.
- Independent read-only review found no Critical/Important integration blocker. It checked shared parsing, field-level evidence, startup family snapshots, bilingual inventories and preservation of expert-feedback source/tests.

## Evidence limits and issue status

These checks validate local code, installed-package behavior and local browser scenarios. They do not establish live Google/Bing account accuracy, human editorial/semantic quality or SEO causality. Remote CI is separate and must be reported from an actual run, not inferred from these checks.

Issues #20, #23 and #24 remain open until PR #27 is merged. The #6 harness/guide is implemented, while authorized human annotations, a frozen held-out corpus and approved pre-tuning targets are still missing. Query work #4/#5 remains gated by those inputs; #22 needs its own page-pair corpus. Optional classifier #7 and readiness #9 remain deferred behind their documented evaluation gates.
