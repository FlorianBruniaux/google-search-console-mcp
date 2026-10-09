# Shared SEO playbooks, 2026-10-09

The 13 SEO playbooks now have one canonical source in `.agents/skills/`. Claude resolves each `SKILL.md` through its repository projection; its routing corpus resolves the same scenario files. `python-clean-code` remains the existing development skill outside this SEO change.

The review corrects nonexistent sorting/date/URL arguments, penalty and AI-loss claims, whole-site orphan extrapolation, mandatory scores, predicted click gains, and schema eligibility claims. The supported call inventory is checked against `registry.TOOLS`, including required inputs. Every provider observation retains its own source and window; optional family or provider failures remain unavailable.

## Reproduce

```sh
python -m pytest tests/test_shared_playbooks.py -q
node scripts/routing-eval.js --repo --host claude
node scripts/routing-eval.js --repo --host codex
```

The repository routing check reuses the installed router tokenizer/BM25 without writing its live indexes. Missing router modules cause an explicit failure; no router is installed automatically. Both host projections are inspected before calibration. The 224 supplied scenarios cover 13 targets; all meet the existing local F1 >= 0.6 eligibility gate. False positives remain visible in the calibration table. These numbers measure this authored routing corpus, not held-out routing accuracy or expert SEO judgment.

The combined installed global/project calibration also passes the 13 SEO targets (401 scenarios, 23 targets). The global `critique-plan` and `debugger` targets fail their gate; no global routing readiness or live index activation is claimed. Their configuration is not changed here.

Twenty-seven Python checks verify canonical resources, declared call signatures and seeded instruction boundaries. They do not execute a model. The existing controlled-host tests separately verify unknown indexing and unavailable branches reaching review. Native runtime execution and live index activation are not verified by these local checks. The complete global gate is not passing because of the two non-SEO targets above. Global configuration is outside this repository change.

Human diagnosis quality and independent semantic review remain gated by issue #6. No provider credentials or live SEO dataset were used. No external writes were made by a playbook.

Validation: the full mocked Python suite passes 1,810 tests; built-site checks pass 29 tests and documentation source checks pass 6 tests. Translation hashes match the updated canonical changelog.
