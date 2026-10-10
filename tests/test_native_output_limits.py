"""Harmless local child processes, not real Claude/Codex provider validation."""
import importlib
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from gsc_mcp import native_audit
from gsc_mcp.audit_runtime import AuditSession


pytestmark = pytest.mark.skipif(sys.platform not in {'darwin', 'linux'}, reason='POSIX native runner')


def runner():
    assert importlib.util.find_spec('gsc_mcp.native_process'), 'bounded native process runner missing'
    return importlib.import_module('gsc_mcp.native_process')


def run_child(tmp_path, source, *, timeout=3, limit=8192):
    return runner().run_bounded([sys.executable, '-c', source], input_bytes=b'source packet',
        cwd=tmp_path, output_path=tmp_path / 'final.json', timeout=timeout, limit=limit)


@pytest.mark.parametrize('descriptor', [1, 2])
def test_stream_overflow_stops_before_child_can_finish_and_spools_no_logs(tmp_path, descriptor):
    # Missing live limits permits the marker; waiting until exit is insufficient.
    with pytest.raises(ValueError, match='output byte budget'):
        run_child(tmp_path, f'''import os, time
from pathlib import Path
for i in range(1000):
    os.write({descriptor}, b'secret-output' * 1000)
Path('finished').touch()
time.sleep(10)
''')
    assert not (tmp_path / 'finished').exists()
    assert not (tmp_path / 'stdout.json').exists()
    assert not (tmp_path / 'stderr.log').exists()


def test_final_file_is_kernel_bounded_even_if_child_catches_write_error(tmp_path):
    with pytest.raises(ValueError, match='output byte budget'):
        run_child(tmp_path, '''import os, time
fd = os.open('final.json', os.O_WRONLY | os.O_CREAT, 0o600)
try:
    while True: os.write(fd, b'x' * 65536)
except OSError: pass
time.sleep(10)
''')
    assert (tmp_path / 'final.json').stat().st_size == 8192


def test_timeout_kills_descendant_and_reaps_direct_child(tmp_path):
    started = time.monotonic()
    with pytest.raises(RuntimeError, match='TimeoutExpired'):
        run_child(tmp_path, '''import os, subprocess, sys, time
from pathlib import Path
Path('parent.pid').write_text(str(os.getpid()))
child = subprocess.Popen([sys.executable, '-c', "import time; from pathlib import Path; time.sleep(1); Path('escaped').touch(); time.sleep(5)"])
Path('child.pid').write_text(str(child.pid))
time.sleep(10)
''', timeout=0.3)
    assert time.monotonic() - started < 2
    parent = int((tmp_path / 'parent.pid').read_text())
    with pytest.raises(ProcessLookupError):
        os.kill(parent, 0)
    time.sleep(1)
    assert not (tmp_path / 'escaped').exists()


def test_timeout_also_applies_when_child_closes_streams(tmp_path):
    with pytest.raises(RuntimeError, match='TimeoutExpired'):
        run_child(tmp_path, 'import os,time; os.close(1); os.close(2); time.sleep(10)', timeout=0.2)


def test_parent_exit_does_not_leave_descendant_running(tmp_path):
    run_child(tmp_path, '''import subprocess, sys
subprocess.Popen([sys.executable, '-c', "import time; from pathlib import Path; time.sleep(1); Path('escaped').touch()"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
''')
    time.sleep(1)
    assert not (tmp_path / 'escaped').exists()


def test_bounded_capture_accepts_exact_stream_limit_and_discards_stderr(tmp_path):
    result = run_child(tmp_path, "import os; os.write(1, b'x' * 8192); os.write(2, b'y' * 8192)")
    assert result == b'x' * 8192
    assert list(tmp_path.iterdir()) == []


def test_concurrent_launchers_do_not_change_parent_file_limit(tmp_path):
    import resource
    before = resource.getrlimit(resource.RLIMIT_FSIZE)
    def invoke(index):
        root = tmp_path / str(index)
        root.mkdir()
        return run_child(root, "import resource; print(resource.getrlimit(resource.RLIMIT_FSIZE)[1])", limit=8192 + index)
    with ThreadPoolExecutor(max_workers=4) as pool:
        assert list(pool.map(invoke, range(4))) == [b'8192\n', b'8193\n', b'8194\n', b'8195\n']
    assert resource.getrlimit(resource.RLIMIT_FSIZE) == before


def test_launcher_preserves_lower_inherited_soft_limit_in_isolated_interpreter(tmp_path):
    helper = runner().__file__
    source = f'''import resource, runpy, sys
from pathlib import Path
run_bounded = runpy.run_path({helper!r})['run_bounded']
resource.setrlimit(resource.RLIMIT_FSIZE, (4096, resource.RLIM_INFINITY))
output = run_bounded([sys.executable, '-c', 'import resource; print(resource.getrlimit(resource.RLIMIT_FSIZE))'],
    input_bytes=b'packet', cwd={str(tmp_path)!r}, output_path=Path({str(tmp_path / 'final.json')!r}),
    timeout=3, limit=8192)
assert resource.getrlimit(resource.RLIMIT_FSIZE) == (4096, resource.RLIM_INFINITY)
sys.stdout.buffer.write(output)
'''
    result = subprocess.run([sys.executable, '-I', '-c', source], capture_output=True, timeout=5)
    assert result.returncode == 0, result.stderr
    assert result.stdout == b'(4096, 4096)\n'


def make_host(tmp_path, source):
    executable = tmp_path / 'local-host'
    executable.write_text(f'#!{sys.executable}\n' + source)
    executable.chmod(0o700)
    return str(executable)


@pytest.mark.parametrize('host', ['claude', 'codex'])
def test_native_parses_successful_host_envelope(tmp_path, host):
    executable = make_host(tmp_path, '''import json, sys
from pathlib import Path
assert 'SOURCE_PACKET:' in sys.stdin.read()
report = {'claims': [{'text': 'Unknown', 'status': 'unavailable', 'source_refs': ['/observations/0']}]}
if '--output-last-message' in sys.argv:
    Path(sys.argv[sys.argv.index('--output-last-message') + 1]).write_text(json.dumps(report))
else: print(json.dumps({'structured_output': report}))
''')
    result = native_audit.run_native({'observations': [{}]}, host=host, executable=executable, model='local-fixture')
    assert result['claims'][0]['text'] == 'Unknown'


def test_overflow_preserves_sources_and_durable_attempts(tmp_path, monkeypatch):
    executable = make_host(tmp_path, "import os,json\nfor i in range(1000): os.write(2, b'secret-output' * 1000)\nprint(json.dumps({'structured_output': {'claims': []}}))\n")
    monkeypatch.setattr(native_audit.shutil, 'which', lambda host: executable)
    config = dict(run_id='output-overflow', site='sc-domain:example.com', bing_site='https://example.com/',
        ledger_path=str(tmp_path / 'run.sqlite'), max_native_calls=3,
        max_provider_attempts=2, max_tool_calls=2, allowed_tools=['indexing_evidence_matrix'])
    source = {'observations': [{'tool': 'indexing_evidence_matrix', 'result': {'value': None}}]}
    result = native_audit.run_specialists(source, session=AuditSession(config), host='claude',
        model='local-fixture', roles=['gsc-indexing-auditor'])
    assert result['observations'] == source['observations']
    assert result['specialists'][0]['status'] == 'unavailable'
    assert result['native_status'] == 'unavailable; observations_retained'
    assert AuditSession(config).status()['native_attempts'] == 3
    assert 'secret-output' not in json.dumps(result)


def test_unsupported_platform_refuses_before_launch(tmp_path, monkeypatch):
    api = runner()
    monkeypatch.setattr(api.sys, 'platform', 'win32')
    with pytest.raises(RuntimeError, match='unsupported platform'):
        run_child(tmp_path, "from pathlib import Path; Path('launched').touch()")
    assert not (tmp_path / 'launched').exists()
