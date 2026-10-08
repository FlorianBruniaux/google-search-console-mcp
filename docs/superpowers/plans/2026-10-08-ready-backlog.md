# Ready backlog implementation

Scope: issues #14, #15, #2, #3 and #8. Work starts from `02d1cdd42bfe72112b4e864e16b4f7398a8bbb0f` on `codex/backlog-ready-fixes`. Preserve unrelated untracked handoffs and the Bing plan. No package release or production deployment is part of this branch.

1. Fix `traffic_health_check`: use concrete equal dates; distinguish measured zero, empty, unknown and unavailable; gate ratios on known coverage and compatible filters. Add GA4 response coverage and timezone metadata. Own `cross.py`, `ga4.py`, and their regression tests.
2. Detect known challenge interstitials before schema validation. Preserve status, requested/final URL and detection reason; real-page metrics remain unavailable. Own a small shared challenge helper, `technical.py` and fixtures.
3. Inventory existing scores, verdicts and classifications. Add field-level method metadata through `with_meta`, preserving values and source identities. Tiers describe evidence methods, never probabilities or permission to act. Own `meta.py`, the evidence mapping and tests.
4. Mark fetched content untrusted in heading, internal-link, page-technical and schema tools. Add deterministic FR/EN signals and bounded samples without rewriting evidence or granting fetched instructions authority. Own a shared content-trust helper and those tool integrations.
5. Add `ga4_ai_referrals` using concrete dates, source identities, exact source matching, recorded-attribution limitations and coverage gates. Exclude unverified source candidates from confirmed totals. Synchronize registry, documentation and capability counts.

Tasks 1 and 2 run independently. Task 3's design runs alongside them; its implementation owns only shared metadata files. Task 4 follows task 2 to avoid conflicting edits to `technical.py`. Task 5 follows task 1's GA4 coverage contract. The root agent owns documentation and integration.

Validation: reproduce defects or missing contracts with failing tests before implementation; run targeted suites; run the full mocked Python suite after integration; verify bilingual documentation, build and browser behavior; request an independent review of the final diff; fix material review findings with regression tests. Live GA4 properties and the reported live SiteGround challenge are unverified unless separately reproduced.

Issues #4 and #5 remain gated on evaluation data in #6. Classifier backends #7 and citability scoring #9 remain deferred. This branch does not generate human evaluation labels.

Implementation and local verification completed. See [validation record](../../validation/2026-10-08-ready-backlog.md). Merge, package release and deployment remain pending.
