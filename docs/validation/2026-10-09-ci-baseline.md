# U00: Python CI baseline, 2026-10-09

Baseline commit: `a4b26364346ce2215e07a34963319303ed04334e` (remote main reference supplied for this audit). Validation ran in the managed `codex/audit-evidence-foundation` worktree. No production timezone implementation or timezone test was changed.

## Environment failure and declared-dependency validation

The original Python executable, `/Users/florianbruniaux/.pyenv/versions/3.13.0/bin/python`, had no installed `tzdata`. The supplied original-checkout suite result was 1648 passed and one failure: `tests/test_change_impact.py::test_valid_iana_event_works_without_system_timezone_database`. Its log is `/private/tmp/gsc-u00-original-baseline.log`.

The focused test reproduced that failure against the managed worktree source using explicit `PYTHONPATH`. The subprocess deliberately sets `PYTHONTZPATH=""`; its traceback shows `ModuleNotFoundError: No module named 'tzdata'`, then `ZoneInfoNotFoundError` for `Europe/Paris`. The repository already declares `tzdata>=2024.1` in `pyproject.toml`; `uv.lock` resolves `tzdata==2026.5`. This was a local environment missing a declared runtime dependency, not evidence of a source regression. The test was retained unchanged.

`uv` was unavailable in PATH. A fresh temporary isolated Python 3.13.0 environment was created at `/private/tmp/gsc-u00-validation`, then installed from the managed worktree with `python -m pip install '.[dev]' build twine`. This is an installation of the declared dependencies, not a frozen-lock reproduction. Installed versions included `tzdata==2026.5` and `pytest==9.1.1`. No global Python packages were changed.

| Check | Result | Local evidence |
| --- | --- | --- |
| Focused test with original interpreter and managed source | Failed with missing `tzdata` | `/private/tmp/gsc-u00-timezone-red.log` |
| Same focused test in isolated declared-dependency environment | 1 passed | `/private/tmp/gsc-u00-timezone-green.log` |
| Full managed-source Python suite | 1649 passed in 14.40s | `/private/tmp/gsc-u00-full-suite.log` |
| Build wheel and sdist | Successful, version 1.3.1 | `/private/tmp/gsc-u00-build.log`, `/private/tmp/gsc-u00-dist/` |
| `twine check` on both distributions | Both PASSED | Observed command output |
| Installed-wheel `gsc-cli list` outside checkout | Exit 0, lists available tools | `/private/tmp/gsc-u00-wheel-cli-list.txt` |
| Workflow static validation | `actionlint` 1.7.12 exit 0 | `.github/workflows/ci.yml` |

Full-suite command:

```sh
PYTHONPATH=/Users/florianbruniaux/.codex/worktrees/audit-evidence-first/google-search-console-mcp/src /private/tmp/gsc-u00-validation/bin/python -m pytest -q -p no:cacheprovider
```

The installed-wheel smoke uses `/private/tmp/gsc-u00-wheel-smoke/bin/gsc-cli` from `/private/tmp`. Its module import resolved into that environment's `site-packages`. It tests CLI discovery without Google credentials or API requests. An extra diagnostic attempted to parse the default CLI listing as JSON and failed because the default listing is text; the smoke itself exited successfully and the rerun retained the text output.

## Added premerge workflow

`.github/workflows/ci.yml` adds a standalone nonpublishing Python 3.11 job that installs the project and dev dependencies, runs the entire Python suite, builds wheel and sdist, checks distributions, and smoke-tests the installed wheel outside checkout. Existing PyPI publishing and Pages workflows were not changed.

Automatic PR jobs require actor ID `3902606`, PR author ID `3902606`, and a head repository equal to the current repository. Nonowner actors, bot-authored PRs and fork PRs therefore do not automatically start the Python runner job. The owner can manually dispatch the workflow on a selected repository branch after reviewing its code. Dispatch does not accept a fork checkout or arbitrary shell input. This gate is a runner-budget policy, not a sandbox for untrusted reviewed code.

Permissions are limited to `contents: read`; checkout sets `persist-credentials: false`. No secrets, publishing credentials, deployment permissions, `pull_request_target`, or privileged checkout are requested. A workflow concurrency group keyed by PR number or branch cancels stale runs. The job has a 15-minute limit.

## Evidence limits

The workflow is statically valid locally. Remote GitHub Actions execution, actor-gate evaluation on real events, Python 3.11 runner behavior and branch-protection configuration are **UNKNOWN** here. This audit did not configure or assert active branch protection. Owner gating intentionally skips other PRs; those skipped jobs are not evidence that their code was tested. A manual dispatch runs its selected branch revision and is not automatically a required PR merge check.

The full baseline suite was captured before other workers' production-code changes. The new workflow and concurrent documentation edits do not demonstrate Google API behavior, live deployment, indexing, analytics outcomes or causal SEO impact.

## Integration follow-up

U04 adds controlled-host workflow tests that require Node. The final workflow explicitly installs Node 22 so these tests run rather than skip on a runner without Node. The historical baseline above predates these tests. Final integrated results are recorded in [first delivery set validation](2026-10-09-first-delivery-set.md).
