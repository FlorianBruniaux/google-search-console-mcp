"""Offline behavior checks for bounded audit acquisition preflight."""
import importlib.util
import json
import os
from pathlib import Path
import stat
import sys

import pytest

from gsc_mcp.audit_runtime import AuditSession


@pytest.fixture
def runner():
    script = Path(__file__).resolve().parents[1] / 'scripts/run_bounded_audit.py'
    spec = importlib.util.spec_from_file_location('bounded_audit_runner', script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def inputs(tmp_path, tool='get_capabilities', arguments=None):
    settings = dict(run_id='cli-case', site='sc-domain:example.com',
                    ledger_path=str(tmp_path / 'run.sqlite'), max_provider_attempts=1,
                    max_tool_calls=1, allowed_tools=[tool])
    config_path = tmp_path / 'config.json'
    config_path.write_text(json.dumps(settings))
    plan_path = tmp_path / 'requests.json'
    plan_path.write_text(json.dumps([{'tool': tool, 'arguments': arguments or {}}]))
    return settings, ['--config', str(config_path), '--requests', str(plan_path)]


@pytest.mark.parametrize('previous_guard', [None, '0'])
def test_runner_blocks_browser_flow_before_acquisition(tmp_path, monkeypatch, runner, previous_guard):
    from gsc_mcp.registry import TOOLS
    if previous_guard is None:
        monkeypatch.delenv('GSC_NO_BROWSER', raising=False)
    else:
        monkeypatch.setenv('GSC_NO_BROWSER', previous_guard)
    def source(site):
        return json.dumps({'site': site, 'no_browser': os.environ.get('GSC_NO_BROWSER')})
    monkeypatch.setitem(TOOLS, 'get_search_analytics', source)
    settings, args = inputs(tmp_path, 'get_search_analytics', {'site': 'sc-domain:example.com'})
    output = tmp_path / 'output.json'
    monkeypatch.setattr(sys, 'argv', ['run_bounded_audit.py', *args, '--output', str(output)])
    runner.main()
    packet = json.loads(output.read_text())
    assert packet['observations'][0]['result'] == {'site': 'sc-domain:example.com', 'no_browser': '1'}
    assert packet['run']['provider_attempts'] == 0
    assert stat.S_IMODE(output.stat().st_mode) == 0o600


@pytest.mark.parametrize('destination', ['missing_parent', 'parent_is_file', 'existing_file', 'existing_symlink', 'broken_symlink'])
def test_runner_rejects_invalid_output_before_acquisition(tmp_path, monkeypatch, runner, destination):
    settings, args = inputs(tmp_path)
    output = tmp_path / 'output.json'
    if destination == 'missing_parent':
        output = tmp_path / 'missing' / 'output.json'
    elif destination == 'parent_is_file':
        parent = tmp_path / 'file'
        parent.write_text('keep-parent')
        output = parent / 'output.json'
    elif destination == 'existing_file':
        output.write_text('keep-output')
    elif destination == 'existing_symlink':
        target = tmp_path / 'target.json'
        target.write_text('keep-target')
        output.symlink_to(target)
    else:
        output.symlink_to(tmp_path / 'absent.json')
    monkeypatch.setattr(sys, 'argv', ['run_bounded_audit.py', *args, '--output', str(output)])
    with pytest.raises(SystemExit) as stopped:
        runner.main()
    assert stopped.value.code == 2
    assert AuditSession(settings).status()['tool_calls'] == 0
    if destination == 'existing_file':
        assert output.read_text() == 'keep-output'
    if destination in {'existing_symlink', 'broken_symlink'}:
        assert output.is_symlink()
    if destination == 'existing_symlink':
        assert output.read_text() == 'keep-target'
