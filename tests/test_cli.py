"""Tests for gsc-cli (src/gsc_mcp/cli.py).

These tests are RED until cli.py is created — importing from gsc_mcp.cli raises
ImportError at collection time. Once cli.py exists they should all go GREEN.

Mock strategy: patch the service-getter functions at the call site in tools/
modules (e.g. gsc_mcp.tools.analytics.get_searchconsole_service), not in auth.py
or cli.py, so the test is independent of how cli.py wires things up.
"""

import json
import os

import pytest

from gsc_mcp.cli import main  # ImportError = RED before cli.py exists
from gsc_mcp.registry import TOOLS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _tool_to_cmd(name: str) -> str:
    """Convert function name to CLI subcommand name (underscores to dashes)."""
    return name.replace("_", "-")


def _minimal_gsc_rows_response():
    return {"rows": []}


def _minimal_inspection_response():
    return {
        "inspectionResult": {
            "indexStatusResult": {
                "verdict": "PASS",
                "robotsTxtState": "ALLOWED",
                "indexingState": "INDEXED_AND_SERVING",
                "pageFetchState": "SUCCESSFUL",
                "googleCanonical": "https://example.com/",
                "userCanonical": "https://example.com/",
            }
        }
    }


# ---------------------------------------------------------------------------
# 1. list command
# ---------------------------------------------------------------------------

def test_list_command(capsys):
    exit_code = main(["list"])
    assert exit_code == 0
    captured = capsys.readouterr()
    for name in TOOLS:
        cmd = _tool_to_cmd(name)
        assert cmd in captured.out, f"Command {cmd!r} (tool {name!r}) missing from `gsc-cli list` output"


# ---------------------------------------------------------------------------
# 2. All 43 subparsers build without crash (--help exits 0)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("tool_name", sorted(TOOLS.keys()))
def test_all_tools_build_without_crash(tool_name):
    cmd = _tool_to_cmd(tool_name)
    with pytest.raises(SystemExit) as exc_info:
        main([cmd, "--help"])
    assert exc_info.value.code == 0, (
        f"`gsc-cli {cmd} --help` exited with code {exc_info.value.code} (expected 0)"
    )


# ---------------------------------------------------------------------------
# 3. Dispatch: get-search-analytics
# ---------------------------------------------------------------------------

def test_dispatch_get_search_analytics(mock_gsc_service, monkeypatch, capsys):
    mock_gsc_service.searchanalytics().query().execute.return_value = _minimal_gsc_rows_response()
    monkeypatch.setattr(
        "gsc_mcp.tools.analytics.get_searchconsole_service",
        lambda: mock_gsc_service,
    )
    exit_code = main(["get-search-analytics", "--site", "https://example.com/", "--days", "7"])
    assert exit_code == 0
    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert "_meta" not in result


# ---------------------------------------------------------------------------
# 4. Int coercion via --days flag
# ---------------------------------------------------------------------------

def test_int_coercion(mock_gsc_service, monkeypatch, capsys):
    executed = {}

    def fake_execute():
        executed["called"] = True
        return _minimal_gsc_rows_response()

    mock_gsc_service.searchanalytics().query().execute.side_effect = fake_execute
    monkeypatch.setattr(
        "gsc_mcp.tools.analytics.get_searchconsole_service",
        lambda: mock_gsc_service,
    )
    exit_code = main(["get-search-analytics", "--site", "https://example.com/", "--days", "14"])
    assert exit_code == 0
    assert executed.get("called"), "searchanalytics was never called"


# ---------------------------------------------------------------------------
# 5. list[str] flag with action=append (--urls repeated)
# ---------------------------------------------------------------------------

def test_list_str_flag_repeated(mock_gsc_service, monkeypatch, capsys):
    mock_gsc_service.urlInspection().index().inspect().execute.return_value = (
        _minimal_inspection_response()
    )
    monkeypatch.setattr(
        "gsc_mcp.tools.inspection.get_searchconsole_service",
        lambda: mock_gsc_service,
    )
    exit_code = main([
        "batch-url-inspection",
        "--urls", "https://a.com/",
        "--urls", "https://b.com/",
        "--site", "https://example.com/",
    ])
    assert exit_code == 0
    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert result["count"] == 2


# ---------------------------------------------------------------------------
# 6. ga4_funnel --steps parses list[dict] from JSON string
# ---------------------------------------------------------------------------

def test_ga4_funnel_steps_json(monkeypatch):
    """Argument parsing must succeed (the list[dict] mapper works)."""
    # If parsing fails, argparse raises SystemExit(2); we want 0 or 1 (execution error)
    monkeypatch.setenv("GA4_PROPERTY_ID", "123456789")
    monkeypatch.setattr(
        "gsc_mcp.tools.ga4.get_ga4_property_id",
        lambda override=None: "properties/123456789",
    )

    from unittest.mock import MagicMock
    mock_alpha = MagicMock()
    mock_alpha.run_funnel_report.return_value = MagicMock(funnel_table=MagicMock(rows=[]))
    monkeypatch.setattr("gsc_mcp.tools.ga4.get_alpha_ga4_service", lambda: mock_alpha)

    steps_json = '[{"name":"signup","event":"sign_up"},{"name":"purchase","event":"purchase"}]'
    try:
        exit_code = main([
            "ga4-funnel",
            "--steps", steps_json,
            "--start-date", "28daysAgo",
            "--end-date", "today",
        ])
        # Any exit code is fine as long as it's not 2 (which would indicate arg parse failure)
        assert exit_code != 2, "exit code 2 = argparse failure; list[dict] mapping is broken"
    except SystemExit as e:
        assert e.code != 2, "SystemExit(2) = argparse failure; list[dict] mapping is broken"


# ---------------------------------------------------------------------------
# 7. _meta hidden by default
# ---------------------------------------------------------------------------

def test_meta_hidden_by_default(mock_gsc_service, monkeypatch, capsys):
    mock_gsc_service.searchanalytics().query().execute.return_value = _minimal_gsc_rows_response()
    monkeypatch.setattr(
        "gsc_mcp.tools.analytics.get_searchconsole_service",
        lambda: mock_gsc_service,
    )
    main(["get-search-analytics", "--site", "https://example.com/"])
    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert "_meta" not in result, "_meta should be hidden by default"


# ---------------------------------------------------------------------------
# 8. --meta flag keeps _meta
# ---------------------------------------------------------------------------

def test_meta_flag_keeps_meta(mock_gsc_service, monkeypatch, capsys):
    mock_gsc_service.searchanalytics().query().execute.return_value = _minimal_gsc_rows_response()
    monkeypatch.setattr(
        "gsc_mcp.tools.analytics.get_searchconsole_service",
        lambda: mock_gsc_service,
    )
    main(["get-search-analytics", "--site", "https://example.com/", "--meta"])
    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert "_meta" in result, "--meta flag should preserve _meta in output"


# ---------------------------------------------------------------------------
# 9. RuntimeError → exit 2
# ---------------------------------------------------------------------------

def test_runtime_error_exits_2(monkeypatch):
    def _raise():
        raise RuntimeError("No credentials: GSC_SERVICE_ACCOUNT_PATH not set")

    monkeypatch.setattr(
        "gsc_mcp.tools.analytics.get_searchconsole_service",
        _raise,
    )
    exit_code = main(["get-search-analytics", "--site", "https://example.com/"])
    assert exit_code == 2


# ---------------------------------------------------------------------------
# 10. GSC_NO_BROWSER is set by main()
# ---------------------------------------------------------------------------

def test_no_browser_env_set(monkeypatch, capsys):
    monkeypatch.delenv("GSC_NO_BROWSER", raising=False)
    main(["list"])
    assert os.environ.get("GSC_NO_BROWSER") == "1", (
        "main() must set GSC_NO_BROWSER=1 at startup"
    )


# ---------------------------------------------------------------------------
# 11. --property-id flag is forwarded to get_ga4_property_id
# ---------------------------------------------------------------------------

def test_property_id_flag_propagated(monkeypatch, capsys):
    received = {}

    def fake_get_property_id(override=None):
        received["override"] = override
        return "properties/987654321"

    monkeypatch.setenv("GA4_PROPERTY_ID", "123456789")
    monkeypatch.setattr("gsc_mcp.tools.ga4.get_ga4_property_id", fake_get_property_id)

    from unittest.mock import MagicMock
    mock_client = MagicMock()
    mock_client.run_report.return_value = MagicMock(rows=[])
    monkeypatch.setattr("gsc_mcp.tools.ga4.get_ga4_service", lambda: mock_client)

    main(["ga4-organic-landing-pages", "--property-id", "987654321"])
    assert received.get("override") == "987654321", (
        f"--property-id was not forwarded; received: {received}"
    )
