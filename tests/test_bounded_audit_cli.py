"""Offline behavior checks for bounded audit acquisition preflight."""
import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess
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


def test_interrupted_analysis_can_restart_from_saved_sources_without_reacquisition(tmp_path, monkeypatch, runner):
    from gsc_mcp import native_audit
    from tests.test_native_recovery import local_host, events, REPORT

    settings, args = inputs(tmp_path, 'indexing_evidence_matrix',
                            {'site': 'sc-domain:example.com', 'urls': ['https://example.com/page']})
    output = tmp_path / 'interrupted.json'
    checkpoint = tmp_path / 'interrupted.json.sources.json'
    # An interrupted invocation consumes one slot; recovery may use only the remaining two.
    settings['max_native_calls'] = 3
    (tmp_path / 'config.json').write_text(json.dumps(settings))
    interrupted_runner = tmp_path / 'interrupt.py'
    interrupted_runner.write_text(
        'import os, runpy, signal\n'
        f'module = runpy.run_path({runner.__file__!r})\n'
        'def interrupt(packet, *, session, **kwargs):\n'
        '    session.reserve_native()\n'
        '    os.kill(os.getpid(), signal.SIGKILL)\n'
        'module["main"].__globals__["run_specialists"] = interrupt\n'
        'module["main"]()\n')
    child = subprocess.run([sys.executable, str(interrupted_runner), *args, '--output', str(output),
                            '--host', 'codex', '--model', 'local-fixture'],
                           env=dict(os.environ, PYTHONPATH=str(Path(runner.__file__).resolve().parents[1] / 'src')),
                           capture_output=True, timeout=30)
    assert child.returncode == -9, child.stderr.decode()
    assert checkpoint.exists(), 'Acquired sources must survive an interrupted native invocation'
    assert not output.exists()
    assert stat.S_IMODE(checkpoint.stat().st_mode) == 0o600
    saved = checkpoint.read_bytes()
    sources = json.loads(saved)['observations']
    assert len(sources) == 1

    def no_acquisition(*args, **kwargs):
        pytest.fail('Recovery must not invoke an acquisition tool')

    monkeypatch.setattr(AuditSession, 'call', no_acquisition)
    executable = local_host(tmp_path, rows=events(), file_report=REPORT)
    monkeypatch.setattr(native_audit.shutil, 'which', lambda host: executable)
    recovered = tmp_path / 'recovered.json'
    monkeypatch.setattr(sys, 'argv', ['runner', '--config', str(tmp_path / 'config.json'),
                                    '--resume-from', str(checkpoint), '--output', str(recovered),
                                    '--host', 'codex', '--model', 'local-fixture'])
    runner.main()
    result = json.loads(recovered.read_text())
    assert result['observations'] == sources
    assert result['draft'] == REPORT
    assert result['review'] == REPORT
    assert result['run']['tool_calls'] == 1
    assert result['run']['provider_attempts'] == 0
    assert result['run']['native_attempts'] == 3
    assert checkpoint.read_bytes() == saved

    # Another explicit recovery cannot reset the exhausted model budget.
    monkeypatch.setattr(sys, 'argv', [*sys.argv[:-6], '--output', str(tmp_path / 'exhausted.json'),
                                    '--host', 'codex', '--model', 'local-fixture'])
    runner.main()
    exhausted = json.loads((tmp_path / 'exhausted.json').read_text())
    assert exhausted['native_status'] == 'unavailable; observations_retained'
    assert exhausted['run']['native_attempts'] == 3


@pytest.mark.parametrize('fault', ['different_config', 'missing_ledger', 'wrong_site', 'bad_observation'])
def test_resume_rejects_incompatible_sources_before_native_launch(tmp_path, monkeypatch, runner, fault):
    settings, args = inputs(tmp_path)
    saved = tmp_path / 'saved.json'
    monkeypatch.setattr(sys, 'argv', ['runner', *args, '--output', str(saved)])
    runner.main()
    packet = json.loads(saved.read_text())
    if fault == 'different_config':
        settings['max_native_calls'] = 3
        (tmp_path / 'config.json').write_text(json.dumps(settings))
    elif fault == 'missing_ledger':
        Path(settings['ledger_path']).unlink()
    elif fault == 'wrong_site':
        packet['run']['site'] = 'sc-domain:other.example'
    else:
        packet['observations'][0].pop('result')
    saved.write_text(json.dumps(packet))
    def no_native(*args, **kwargs):
        pytest.fail('Invalid saved sources must fail before native dispatch')
    monkeypatch.setattr(runner, 'run_specialists', no_native)
    monkeypatch.setattr(sys, 'argv', ['runner', '--config', str(tmp_path / 'config.json'),
                                    '--resume-from', str(saved), '--output', str(tmp_path / 'new.json'),
                                    '--host', 'codex', '--model', 'local-fixture'])
    with pytest.raises(SystemExit) as stopped:
        runner.main()
    assert stopped.value.code == 2
    assert not (tmp_path / 'new.json').exists()
    if fault == 'missing_ledger':
        assert not Path(settings['ledger_path']).exists()


def test_existing_checkpoint_is_rejected_before_acquisition(tmp_path, monkeypatch, runner):
    def no_native(*args, **kwargs):
        pytest.fail('Checkpoint collision must be rejected before native dispatch')
    monkeypatch.setattr(runner, 'run_specialists', no_native)
    settings, args = inputs(tmp_path)
    output = tmp_path / 'output.json'
    checkpoint = tmp_path / 'output.json.sources.json'
    checkpoint.write_text('keep-checkpoint')
    monkeypatch.setattr(sys, 'argv', ['runner', *args, '--output', str(output),
                                    '--host', 'codex', '--model', 'local-fixture'])
    with pytest.raises(SystemExit):
        runner.main()
    assert AuditSession(settings).status()['tool_calls'] == 0
    assert checkpoint.read_text() == 'keep-checkpoint'
