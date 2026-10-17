"""Offline regressions for incomplete native turns and session-state ceilings.

These are normalized CLI-envelope fixtures, not new Claude/Codex measurements.
"""
import json
import os
import sys
from pathlib import Path

import pytest

from gsc_mcp import native_audit, native_process
from gsc_mcp.audit_runtime import AuditSession


pytestmark = pytest.mark.skipif(sys.platform not in {'darwin', 'linux'}, reason='POSIX native runner')

SOURCE = {'observations': [{'tool': 'indexing_evidence_matrix', 'result': {'value': None}}]}
REPORT = {'claims': [{'text': 'Unknown', 'status': 'unavailable', 'source_refs': ['/observations/0']}]}


def events(report=REPORT, *, thread='original-thread', complete=True):
    rows = [{'type': 'thread.started', 'thread_id': thread}, {'type': 'turn.started'},
            {'type': 'item.completed', 'item': {'id': 'message', 'type': 'agent_message',
                                              'text': json.dumps(report)}}]
    if complete:
        rows.append({'type': 'turn.completed', 'usage': {'input_tokens': 1, 'output_tokens': 1}})
    return rows


def local_host(tmp_path, *, rows, file_report=None, prelude=''):
    executable = tmp_path / 'local-codex'
    source = ('import json, sys\nfrom pathlib import Path\nsys.stdin.read()\n' + prelude + '\n'
              + f'rows={rows!r}\nfile_report={file_report!r}\n'
              + 'if file_report is not None:\n'
              + ' Path(sys.argv[sys.argv.index("--output-last-message")+1]).write_text(json.dumps(file_report))\n'
              + 'for row in rows: print(json.dumps(row), flush=True)\n')
    executable.write_text(f'#!{sys.executable}\n' + source)
    executable.chmod(0o700)
    return str(executable)


def invoke(executable):
    return native_audit.run_native(SOURCE, host='codex', model='local-fixture', executable=executable)


def test_codex_can_commit_session_wal_larger_than_report_ceiling(tmp_path):
    # A small final report must not fail because the host commits its state first.
    prelude = '''import sqlite3
connection = sqlite3.connect('host.sqlite')
connection.execute('PRAGMA journal_mode=WAL')
connection.execute('PRAGMA wal_autocheckpoint=0')
connection.execute('CREATE TABLE state (value BLOB)')
connection.executemany('INSERT INTO state VALUES (?)', [(b'x' * 8192,)] * 400)
connection.commit()
assert connection.execute('SELECT count(*) FROM state').fetchone()[0] == 400
assert Path('host.sqlite-wal').stat().st_size > 2000000
'''
    assert invoke(local_host(tmp_path, rows=events(), file_report=REPORT, prelude=prelude)) == REPORT


def test_completed_stdout_report_recovers_missing_last_message_file(tmp_path):
    assert invoke(local_host(tmp_path, rows=events())) == REPORT


def test_zero_exit_and_report_file_do_not_complete_a_codex_turn(tmp_path):
    with pytest.raises(ValueError, match='codex_turn_incomplete'):
        invoke(local_host(tmp_path, rows=events(complete=False), file_report=REPORT))


def test_failed_turn_does_not_promote_existing_report_or_echo_backend_error(tmp_path):
    rows = events()[:-1] + [{'type': 'turn.failed', 'error': {'message': 'private-backend-detail'}}]
    with pytest.raises(ValueError, match='codex_turn_failed') as caught:
        invoke(local_host(tmp_path, rows=rows, file_report=REPORT))
    assert 'private-backend-detail' not in str(caught.value)


def test_completed_stream_cannot_promote_a_different_last_message_file(tmp_path):
    with pytest.raises(ValueError, match='codex_report_mismatch'):
        invoke(local_host(tmp_path, rows=events({'claims': []}), file_report=REPORT))


def test_resume_checks_original_thread_before_accepting_completed_report():
    stream = b'\n'.join(json.dumps(row).encode() for row in events())
    assert native_audit.parse_codex_response(stream, expected_thread_id='original-thread') == REPORT
    with pytest.raises(ValueError, match='codex_thread_mismatch'):
        native_audit.parse_codex_response(stream, expected_thread_id='different-thread')


def test_resumed_tool_result_is_not_a_report_without_turn_completion():
    rows = [{'type': 'thread.started', 'thread_id': 'original-thread'}, {'type': 'turn.started'},
            {'type': 'item.completed', 'item': {'id': 'tool', 'type': 'mcp_tool_call',
              'status': 'completed', 'result': {'content': [{'type': 'text', 'text': json.dumps(REPORT)}]}}}]
    stream = b'\n'.join(json.dumps(row).encode() for row in rows)
    with pytest.raises(ValueError, match='codex_turn_incomplete'):
        native_audit.parse_codex_response(stream, expected_thread_id='original-thread')


def test_incomplete_reports_retain_sources_and_consumed_attempts(tmp_path, monkeypatch):
    executable = local_host(tmp_path, rows=events(complete=False), file_report=REPORT)
    monkeypatch.setattr(native_audit.shutil, 'which', lambda host: executable)
    config = dict(run_id='incomplete-native', site='sc-domain:example.com',
                  ledger_path=str(tmp_path / 'run.sqlite'), max_native_calls=3,
                  max_tool_calls=1, max_provider_attempts=1, allowed_tools=['indexing_evidence_matrix'])
    result = native_audit.run_specialists(SOURCE, session=AuditSession(config), host='codex',
                                        model='local-fixture', roles=['gsc-indexing-auditor'])
    assert result['observations'] == SOURCE['observations']
    assert result['native_status'] == 'unavailable; observations_retained'
    assert result['specialists'][0]['failure_reason'] == 'codex_turn_incomplete'
    assert AuditSession(config).status()['native_attempts'] == 3
    assert AuditSession(config).status()['provider_attempts'] == 0


def test_separate_state_ceiling_keeps_stdout_and_stderr_bounded(tmp_path):
    for descriptor in [1, 2]:
        with pytest.raises(ValueError, match='output byte budget'):
            native_process.run_bounded([sys.executable, '-c', f'import os,time; os.write({descriptor}, b"x" * 8193); time.sleep(5)'],
                input_bytes=b'', cwd=tmp_path, output_path=tmp_path / 'final.json', timeout=5,
                limit=8192, regular_file_limit=32768)


def test_parent_stderr_capture_is_private_exclusive_and_bounded(tmp_path):
    log = tmp_path / 'diagnostic.txt'
    with pytest.raises(ValueError, match='output byte budget'):
        native_process.run_bounded([sys.executable, '-c', 'import os,time; os.write(2, b"x" * 8193); time.sleep(5)'],
            input_bytes=b'', cwd=tmp_path, output_path=tmp_path / 'final.json', timeout=5,
            limit=8192, regular_file_limit=32768, stderr_path=log)
    assert log.stat().st_size <= 8192
    assert log.stat().st_mode & 0o777 == 0o600
    original = log.read_bytes()
    with pytest.raises(FileExistsError):
        native_process.run_bounded([sys.executable, '-c', 'raise SystemExit(7)'],
            input_bytes=b'', cwd=tmp_path, output_path=tmp_path / 'final.json', timeout=5, stderr_path=log)
    assert log.read_bytes() == original


@pytest.mark.parametrize('tail,code', [
    ([{'type': 'item.completed', 'item': {'id': 'tool', 'type': 'mcp_tool_call', 'status': 'completed'}},
      {'type': 'turn.completed'}], 'codex_final_report_missing'),
    ([{'type': 'item.started', 'item': {'id': 'tool', 'type': 'mcp_tool_call', 'status': 'in_progress'}},
      {'type': 'turn.completed'}], 'codex_turn_incomplete'),
    ([{'type': 'turn.completed'},
      {'type': 'item.started', 'item': {'id': 'tool', 'type': 'mcp_tool_call', 'status': 'in_progress'}}],
     'codex_event_stream_invalid'),
])
def test_later_work_cannot_promote_an_earlier_json_message(tail, code):
    stream = b'\n'.join(json.dumps(row).encode() for row in events(complete=False) + tail)
    with pytest.raises(ValueError, match=code):
        native_audit.parse_codex_response(stream)


def test_separate_state_allowance_does_not_accept_an_oversized_final(tmp_path):
    with pytest.raises(ValueError, match='output byte budget'):
        native_process.run_bounded([sys.executable, '-c',
            'from pathlib import Path; import time; Path("final.json").write_bytes(b"x" * 9000); time.sleep(5)'],
            input_bytes=b'', cwd=tmp_path, output_path=tmp_path / 'final.json', timeout=5,
            limit=8192, regular_file_limit=32768)
    # The larger per-file ceiling is distinct from report acceptance.
    assert 8192 <= (tmp_path / 'final.json').stat().st_size <= 32768


def test_separate_state_allowance_remains_kernel_bounded(tmp_path):
    with pytest.raises((ValueError, RuntimeError)):
        native_process.run_bounded([sys.executable, '-c',
            'import os; fd=os.open("session-state",os.O_CREAT|os.O_WRONLY,0o600); '
            'os.write(fd,b"x" * 65536); os.write(fd,b"x")'],
            input_bytes=b'', cwd=tmp_path, output_path=tmp_path / 'final.json', timeout=5,
            limit=8192, regular_file_limit=32768)
    assert (tmp_path / 'session-state').stat().st_size == 32768


def test_completed_tool_error_requires_a_later_final_assistant_message():
    begin = events(complete=False)[:2]
    tool = {'id': 'tool', 'type': 'mcp_tool_call', 'status': 'failed'}
    rows = begin + [{'type': 'item.started', 'item': {**tool, 'status': 'in_progress'}},
                    {'type': 'item.completed', 'item': tool}] + events()[2:]
    stream = b'\n'.join(json.dumps(row).encode() for row in rows)
    assert native_audit.parse_codex_response(stream, expected_thread_id='original-thread') == REPORT
