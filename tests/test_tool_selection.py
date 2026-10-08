"""Actual MCP discovery/capability boundaries for startup family selection."""
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def probe(selection):
    env = {**os.environ, 'PYTHONPATH': str(ROOT / 'src')}
    if selection is None:
        env.pop('GSC_MCP_TOOL_FAMILIES', None)
    else:
        env['GSC_MCP_TOOL_FAMILIES'] = selection
    code = '''
import asyncio,json,os
from gsc_mcp.server import mcp
from gsc_mcp.registry import TOOLS
async def run():
    tools=await mcp.list_tools()
    os.environ['GSC_MCP_TOOL_FAMILIES']='bing'
    response=await mcp.call_tool('get_capabilities',{})
    if isinstance(response,tuple): response=response[0]
    caps=json.loads(response[0].text)
    print(json.dumps({'names':[t.name for t in tools],'catalogue_names':list(TOOLS),'capabilities':caps,
                     'bytes':len(json.dumps([t.model_dump(mode='json') for t in tools]).encode())}))
asyncio.run(run())
'''
    return subprocess.run([sys.executable, '-c', code], env=env, text=True, capture_output=True)


def test_selected_mcp_families_discovery_matches_frozen_capabilities():
    result = probe('sitemaps, links')
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert set(data['names']) == {
        'get_capabilities', 'list_properties', 'get_site_details', 'list_sitemaps',
        'submit_sitemap', 'sitemaps_delete', 'sitemaps_get', 'sitemap_audit',
        'internal_links_audit', 'link_targets_audit', 'link_equity_map',
    }
    caps = data['capabilities']
    assert set(caps['tools']) == set(data['names'])
    assert caps['total'] == 11
    assert caps['tool_selection']['families'] == ['core', 'links', 'sitemaps']
    assert caps['engines']['bing']['tools'] == []
    assert caps['engines']['indexnow']['tools'] == []


def test_unset_mcp_selection_preserves_full_catalogue():
    result = probe(None)
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert set(data['names']) == set(data['catalogue_names'])
    assert data['capabilities']['total'] == len(data['catalogue_names'])
    assert data['capabilities']['tool_selection']['mode'] == 'all'
    assert 'bing_query_stats' in data['names'] and 'indexnow_submit' in data['names']


def test_invalid_family_selection_fails_before_server_start():
    for value in ('', 'seo,', 'seo,typo'):
        result = probe(value)
        assert result.returncode != 0
        assert 'GSC_MCP_TOOL_FAMILIES' in result.stderr
        assert result.stdout == ''


def test_cli_catalogue_remains_full_when_mcp_is_restricted():
    env = {**os.environ, 'PYTHONPATH': str(ROOT / 'src'), 'GSC_MCP_TOOL_FAMILIES': 'sitemaps'}
    result = subprocess.run([sys.executable, '-m', 'gsc_mcp.cli', 'list'], env=env,
                            text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
    assert 'bing-query-stats' in result.stdout and 'ga4-funnel' in result.stdout
