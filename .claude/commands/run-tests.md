---
description: Run the gsc-mcp pytest suite with failure diagnosis. Optionally filter to a single module. Diagnoses common mocking failures automatically.
argument-hint: "[module]  # e.g. 'analytics', 'ga4', 'crux' or empty for all tests"
---

# Run Tests

Run the pytest suite for gsc-mcp, with optional module filter.

## Usage

```
/run-tests              # All tests
/run-tests analytics    # Only tests/test_analytics.py
/run-tests ga4          # Only tests/test_ga4.py
```

## Steps

1. Parse `$ARGUMENTS` for optional module name

2. Run the appropriate command:

```bash
# All tests, quiet output
.venv/bin/pytest tests/ -q

# Single module, verbose
.venv/bin/pytest tests/test_<module>.py -v

# Filter by test name
.venv/bin/pytest tests/ -k "test_batch" -v
```

3. Report the result:
   - Total: passed / failed / skipped counts
   - On failures: exact assertion message and file:line for each failure
   - On all pass: confirm with the test count

## On Failure

For each failing test, diagnose before suggesting a fix.

**Wrong patch path**: `patch("gsc_mcp.auth.get_searchconsole_service")` fails because the mock doesn't reach the call site. Fix is to patch at the module that imports the function, e.g. `gsc_mcp.tools.analytics.get_searchconsole_service`.

**Missing GA4 fixture**: `GA4_PROPERTY_ID` not set in test environment. Fix is to add `monkeypatch.setenv("GA4_PROPERTY_ID", "123456789")` in an `autouse` fixture (see `tests/test_ga4.py`).

**httpx context manager not wired**: `AttributeError: __enter__` on the mock. Fix is to set `mock_client.__enter__ = MagicMock(return_value=mock_client)` and `mock_client.__exit__ = MagicMock(return_value=False)`.

**sitemap_audit double mock**: this tool patches both `httpx.Client` and `get_search_analytics`. Patching only one of them leaves the other calling the real implementation.
