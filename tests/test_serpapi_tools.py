import asyncio
import importlib
import importlib.util
import json

import pytest

from tests.test_serpapi_provider import KEY, report


def tools():
    assert importlib.util.find_spec('gsc_mcp.tools.serp') is not None, 'SerpApi tools are not implemented'
    return importlib.import_module('gsc_mcp.tools.serp')


def test_search_defaults_to_preview_without_key_or_store(monkeypatch, tmp_path):
    monkeypatch.delenv('SERPAPI_API_KEY', raising=False)
    monkeypatch.delenv('GSC_SERPAPI_ENABLED', raising=False)
    monkeypatch.setenv('GSC_SERPAPI_STORE_DIR', str(tmp_path / 'private'))
    result = json.loads(tools().serpapi_search('guide'))
    assert result['status'] == 'preview'
    assert result['credential_env_declared'] is False
    assert result['_meta']['tool'] == 'serpapi_search'
    assert not (tmp_path / 'private').exists()


def test_live_tool_needs_explicit_enable_key_and_request_id(monkeypatch, tmp_path):
    monkeypatch.setenv('GSC_SERPAPI_STORE_DIR', str(tmp_path / 'private'))
    monkeypatch.setenv('SERPAPI_API_KEY', KEY)
    monkeypatch.delenv('GSC_SERPAPI_ENABLED', raising=False)
    assert json.loads(tools().serpapi_search('guide', acquire=True, request_id='one'))['code'] == 'disabled'
    monkeypatch.setenv('GSC_SERPAPI_ENABLED', '1')
    assert json.loads(tools().serpapi_search('guide', acquire=True))['code'] == 'request_id_required'
    assert not (tmp_path / 'private').exists()


def test_import_preview_is_offline_redacted_and_does_not_claim_real_capture(monkeypatch):
    monkeypatch.setenv('SERPAPI_API_KEY', KEY)
    data = report(api_key=KEY)
    result = json.loads(tools().serpapi_import_preview(json.dumps(data), 'café + guide %2B'))
    assert result['status'] == 'success'
    assert result['delivery'] == 'caller_import'
    assert result['source_authenticity'] == 'unverified'
    assert KEY not in json.dumps(result)
    assert result['_meta']['evidence']['fields']['/status']['basis'] == 'rule'
    assert result['_meta']['evidence']['fields']['/actual_cost_usd']['basis'] is None


@pytest.mark.parametrize('value', ['[]', '{broken', 'null', '{"x":NaN}', 'x' * (1024 * 1024 + 1)],
                         ids=['array', 'malformed', 'null', 'nonfinite', 'oversized'])
def test_import_rejects_invalid_or_excessive_json(value):
    result = json.loads(tools().serpapi_import_preview(value, 'guide'))
    assert result['status'] == 'blocked'


def test_mcp_and_cli_discover_registered_serp_tools_without_acquisition(monkeypatch):
    from gsc_mcp.registry import TOOLS
    from gsc_mcp.tool_selection import select_tools
    monkeypatch.setenv('GSC_MCP_TOOL_FAMILIES', 'serp')
    selected, selection = select_tools(TOOLS)
    assert set(selected) == {'get_capabilities', 'list_properties', 'get_site_details',
                             'serpapi_search', 'serpapi_import_preview'}
    assert selection['families'] == ['core', 'serp']
    from gsc_mcp.tools.properties import get_capabilities
    caps = json.loads(get_capabilities())
    assert caps['engines']['serpapi']['runtime_qualified'] is False
    assert caps['engines']['serpapi']['tools'] == ['serpapi_import_preview', 'serpapi_search']


def test_existing_audit_budget_cannot_be_bypassed_by_serp_acquisition(monkeypatch, tmp_path):
    from gsc_mcp.audit_runtime import _CURRENT, READ_ONLY_TOOLS
    monkeypatch.setenv('GSC_SERPAPI_ENABLED', '1')
    monkeypatch.setenv('SERPAPI_API_KEY', KEY)
    monkeypatch.setenv('GSC_SERPAPI_STORE_DIR', str(tmp_path / 'private'))
    token = _CURRENT.set(object())
    try:
        result = json.loads(tools().serpapi_search('guide', acquire=True, request_id='one'))
    finally:
        _CURRENT.reset(token)
    assert result['code'] == 'unsupported_audit_acquisition'
    assert 'serpapi_search' not in READ_ONLY_TOOLS
    assert not (tmp_path / 'private').exists()


def test_real_mcp_discovery_and_preview_match_selected_capabilities():
    from tests.test_tool_selection import probe
    result = probe('serp')
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert set(data['names']) == {'get_capabilities', 'list_properties', 'get_site_details',
                                  'serpapi_search', 'serpapi_import_preview'}
    assert data['capabilities']['engines']['serpapi']['runtime_qualified'] is False


def test_cli_preview_exposes_boolean_flags_and_does_not_acquire(monkeypatch, tmp_path):
    import os
    from pathlib import Path
    import subprocess
    import sys
    monkeypatch.setenv('GSC_SERPAPI_ENABLED', '1')
    monkeypatch.setenv('SERPAPI_API_KEY', KEY)
    monkeypatch.setenv('GSC_SERPAPI_STORE_DIR', str(tmp_path / 'private'))
    env = {**os.environ, 'PYTHONPATH': str(Path(__file__).resolve().parents[1] / 'src')}
    result = subprocess.run([sys.executable, '-m', 'gsc_mcp.cli', 'serpapi-search',
                             '--query', 'café + guide %2B', '--device', 'mobile'],
                             env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert data['status'] == 'preview' and data['requested']['device'] == 'mobile'
    assert KEY not in result.stdout and not (tmp_path / 'private').exists()


def test_enabled_tool_without_credential_stops_before_storage(monkeypatch, tmp_path):
    monkeypatch.setenv('GSC_SERPAPI_ENABLED', '1')
    monkeypatch.delenv('SERPAPI_API_KEY', raising=False)
    monkeypatch.setenv('GSC_SERPAPI_STORE_DIR', str(tmp_path / 'private'))
    result = json.loads(tools().serpapi_search('guide', acquire=True, request_id='one'))
    assert result['code'] == 'credential_required'
    assert not (tmp_path / 'private').exists()


def test_preview_metadata_cannot_echo_the_declared_key(monkeypatch):
    monkeypatch.setenv('SERPAPI_API_KEY', KEY)
    result = tools().serpapi_search('guide ' + KEY)
    assert KEY not in result


def test_json_surrogate_is_rejected_instead_of_breaking_utf8_output():
    result = json.loads(tools().serpapi_import_preview('{"text":"\\ud800"}', 'guide'))
    assert result['status'] == 'blocked'
