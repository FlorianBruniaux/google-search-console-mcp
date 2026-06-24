---
name: python-clean-code
description: Review Python code in the gsc-mcp codebase for clean code violations. Checks function size, single responsibility, type hints, naming, error handling patterns, and adherence to the project's module contracts. Use when refactoring a module or before code review.
allowed-tools: Read, Grep, Glob
---

# Python Clean Code Review

Reviews Python code in gsc-mcp for quality issues. Read-only analysis: produces a findings report, applies no fixes.

## When to use

Invoke before opening a PR, after adding a new tool, or when a module feels hard to read. Pass a file path or module name as the argument.

## Review Dimensions

### 1. Function Size and Focus

Flag any function exceeding 30 lines (excluding docstring and blank lines). A function that does more than one thing usually has a name with "and" in it, or a docstring that lists multiple behaviors. Each tool function in `tools/` should do exactly one thing: call the API, transform the response, and return the JSON string.

### 2. Type Hints

Every function signature must be fully annotated. Check for:
- Missing return type (`-> str:`, `-> None:`)
- Missing parameter types
- Use of `Any` without justification
- `list` and `dict` without subscripts where the shape is known (e.g. `list[dict]` not just `list`)

### 3. Naming

Private helpers must start with `_`. Constants at module level must be in `_SCREAMING_SNAKE_CASE`. Tool functions exposed to MCP must be lowercase with underscores. No abbreviations that require context to decode (`r` for `rows`; `svc` is acceptable because it appears consistently across the codebase).

### 4. Error Handling

Tool functions must not silently swallow exceptions. They may catch specific exceptions to convert them into user-friendly error messages, but they must not use bare `except:` or `except Exception:` without re-raising or returning a structured error response. Transient Google API errors belong in `retry.py`, not in tool functions.

### 5. Duplication

Check for logic duplicated across modules. Common candidates: date range calculation (already in `analytics._date_range`), URL normalization (already in `cross._normalize_url`), dimension filter construction (already in `ga4._build_dimension_filter`). If a function re-implements one of these, flag it.

### 6. Output Contract Compliance

Every public tool function must return `json.dumps(with_meta(...))`. Flag any function that:
- Returns raw `json.dumps({...})` without `with_meta`
- Returns a plain string or dict
- Nests the main data under a `"data"` key inside `with_meta`

### 7. Docstrings

MCP uses the function docstring as the tool description visible to the user. The docstring must be present, must describe what the tool does (not how), and must mention key parameters and any data lag (GSC has a 3-day lag by default).

## Output Format

```
## Clean Code Review: <file>

### Critical
- [function:line] [issue]: [why it matters]

### Improvement
- [function:line] [issue]: [suggested fix]

### Minor
- [function:line] [issue]

### Passed
- Type hints: complete on all public functions
- Output contract: all tools use with_meta
```

## Evidence Rule

Every finding must cite the exact function name and line number. Do not flag something as a violation without reading the code to confirm it.
