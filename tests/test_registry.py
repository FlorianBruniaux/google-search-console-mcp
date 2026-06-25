"""Tests for the central tool registry.

These tests must FAIL (RED) before registry.py exists, then pass (GREEN) after.
Run pytest tests/test_registry.py to verify.
"""

from gsc_mcp.registry import TOOLS
from gsc_mcp.tools.properties import _ALL_TOOLS


def test_registry_count():
    """The registry must expose exactly 43 tools."""
    assert len(TOOLS) == 43, f"Expected 43 tools, got {len(TOOLS)}"


def test_registry_names_match_all_tools():
    """Tool names in the registry must exactly match _ALL_TOOLS in properties.py."""
    assert set(TOOLS) == set(_ALL_TOOLS), (
        f"Registry/properties mismatch.\n"
        f"In registry only: {set(TOOLS) - set(_ALL_TOOLS)}\n"
        f"In _ALL_TOOLS only: {set(_ALL_TOOLS) - set(TOOLS)}"
    )


def test_registry_values_are_callable():
    """Every entry in TOOLS must be a callable (Python function)."""
    for name, fn in TOOLS.items():
        assert callable(fn), f"TOOLS[{name!r}] is not callable: {fn!r}"


def test_registry_keys_match_function_names():
    """Dict keys must match the actual __name__ of each function."""
    for key, fn in TOOLS.items():
        assert fn.__name__ == key, (
            f"Key mismatch: TOOLS[{key!r}] -> fn.__name__={fn.__name__!r}"
        )
