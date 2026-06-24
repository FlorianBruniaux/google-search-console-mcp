---
description: Step-by-step workflow for adding a new MCP tool to gsc-mcp. Ensures correct output contract, retry decoration, server registration, and test scaffolding. Based on the "Adding a new tool" section in CLAUDE.md.
argument-hint: "<tool_name> [module]  # e.g. 'keyword_gaps seo' or just 'crawl_budget'"
---

# Add Tool

Guided workflow for adding a tool to gsc-mcp without missing any registration step.

## Usage

```
/add-tool keyword_gaps seo          # Add to existing seo.py
/add-tool crawl_budget technical    # Add to technical.py
/add-tool video_indexing            # Claude selects the module
```

## Phase 1: Plan

1. Parse `$ARGUMENTS` to extract tool name and target module (if given)
2. Read `src/gsc_mcp/tools/` to identify which module fits this tool
3. Read `src/gsc_mcp/server.py` to understand the import style
4. Read `src/gsc_mcp/properties.py` to locate `_ALL_TOOLS`
5. Present the plan and confirm with the user before writing any code

## Phase 2: Implement

### Step 1: Write the function

In `src/gsc_mcp/tools/<module>.py`:

```python
def <tool_name>(
    site: str,
    # params with type hints and defaults
) -> str:
    """One-line summary.

    Full description of what this tool does, data lag if applicable,
    row limits, and the fields returned in the response.
    """
    svc = get_searchconsole_service()
    # implementation
    data = {}
    return json.dumps(with_meta(data, tool="<tool_name>", params={"site": site}))
```

Rules for this step:

- Apply `@with_retry()` if calling a Google API directly
- Always use `with_meta()` in the return value (never return raw JSON)
- Add type hints to every parameter
- The docstring becomes the MCP tool description, so make it clear and useful

### Step 2: Register in server.py

```python
# Add import at the top:
from gsc_mcp.tools.<module> import <tool_name>

# Add registration below the existing registrations:
mcp.tool()(<tool_name>)
```

### Step 3: Update properties.py

```python
# Add to _ALL_TOOLS (alphabetical order):
_ALL_TOOLS = [
    ...,
    "<tool_name>",
    ...
]
```

Update the count in `get_capabilities` docstring. If there were 36 tools, change to 37.

### Step 4: Write tests

In `tests/test_<module>.py`, add at minimum:

```python
def test_<tool_name>_returns_expected_structure():
    # Arrange: wire up mock_gsc_service from conftest
    # Act: call the tool
    # Assert: verify _meta block + core result fields
    result = json.loads(<tool_name>(site="sc-domain:example.com"))
    assert "_meta" in result
    assert result["_meta"]["tool"] == "<tool_name>"
```

See `tests/conftest.py` and existing test files for mocking patterns.

## Phase 3: Verify

```bash
# Verify imports work cleanly
.venv/bin/python -c "from gsc_mcp.server import mcp; print('import OK')"

# Run the full test suite
.venv/bin/pytest tests/ -q

# Confirm the tool appears in capabilities
.venv/bin/python -c "
import json
from gsc_mcp.tools.properties import get_capabilities
caps = json.loads(get_capabilities())
print(len(caps['tools']), 'tools registered')
"
```

## Completion Checklist

- [ ] Function implemented in correct module with full type hints
- [ ] `@with_retry()` applied if the function calls a Google API directly
- [ ] `with_meta()` wrapper in the return value
- [ ] Docstring present on the function
- [ ] Imported and registered in `server.py`
- [ ] Added to `_ALL_TOOLS` in `properties.py` (alphabetical)
- [ ] `get_capabilities` docstring count updated
- [ ] Tests written and passing
- [ ] `CHANGELOG.md` updated under `[Unreleased]`
