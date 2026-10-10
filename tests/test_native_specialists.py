"""Native roles consume acquired sources; model attempts are independently bounded."""
import copy
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from gsc_mcp.audit_runtime import AuditBudgetExceeded, AuditSession
from gsc_mcp import native_audit


def session(tmp_path, limit=5):
    return AuditSession(dict(run_id='native', site='sc-domain:example.com',
        bing_site='https://example.com/', ledger_path=str(tmp_path / 'run.sqlite'),
        max_provider_attempts=3, max_tool_calls=10, max_native_calls=limit,
        allowed_tools=['indexing_evidence_matrix']))


def packet():
    return {'run': {'site': 'sc-domain:example.com'}, 'observations': [
        {'tool': 'get_capabilities', 'arguments': {}, 'result': {'tools': 96}},
        {'tool': 'indexing_evidence_matrix', 'arguments': {'site': 'sc-domain:example.com'},
         'result': {'current_indexing_status': 'unknown', 'clicks': None}}]}


def report():
    return {'claims': [{'text': 'Current indexing remains unknown.', 'status': 'unavailable',
        'source_refs': ['/observations/1/result/current_indexing_status']}]}


def pipeline(source, run, **changes):
    return native_audit.run_specialists(source, session=run, host='codex', model='caller-model',
        roles=['gsc-indexing-auditor', 'gsc-sitemap-auditor'], **changes)


def test_native_reservations_survive_failure_restart_and_concurrent_sessions(tmp_path):
    first, reopened = session(tmp_path, 3), session(tmp_path, 3)
    def attempt(index):
        try:
            (first if index % 2 else reopened).reserve_native()
            return True
        except AuditBudgetExceeded:
            return False
    with ThreadPoolExecutor(max_workers=8) as pool:
        assert sum(pool.map(attempt, range(30))) == 3
    assert session(tmp_path, 3).status()['native_attempts'] == 3
    assert reopened.status()['provider_attempts'] == 0
    with pytest.raises(ValueError, match='configuration'):
        session(tmp_path, 4)


def test_shared_sources_keep_original_indices_and_cannot_be_mutated(tmp_path, monkeypatch):
    source, seen = packet(), []
    original = copy.deepcopy(source)
    def invoke(value, **options):
        seen.append((options['role'], copy.deepcopy(value)))
        value['observations'][1]['result']['clicks'] = 999
        return report()
    monkeypatch.setattr(native_audit, 'run_native', invoke)
    result = pipeline(source, session(tmp_path))
    assert source == original
    assert [item[0] for item in seen] == ['gsc-indexing-auditor', 'gsc-sitemap-auditor', 'author', 'reviewer']
    assert all(value['observations'][1]['result']['clicks'] is None for _, value in seen)
    assert seen[0][1]['role_scope']['observation_indices'] == [1]
    assert 'specialists' in seen[2][1]
    assert 'draft' in seen[3][1]
    assert result['native_status'] == 'draft_and_review_returned; semantic_quality_unverified'
    assert result['run']['native_attempts'] == 4
    assert result['run']['provider_attempts'] == result['run']['tool_calls'] == 0


def test_missing_and_failed_sources_are_visible_without_model_cost(tmp_path, monkeypatch):
    seen = []
    monkeypatch.setattr(native_audit, 'run_native', lambda value, **kw: seen.append(kw['role']) or report())
    source = packet()
    source['observations'].append({'tool': 'traffic_drops', 'arguments': {},
        'result': {'status': 'unavailable', 'reason': 'source_call_failed'}})
    result = native_audit.run_specialists(source, session=session(tmp_path), host='codex', model='caller-model',
        roles=['gsc-schema-auditor', 'gsc-traffic-doctor'])
    assert seen == ['author', 'reviewer']
    assert result['specialists'][0]['status'] == 'unavailable'
    assert result['specialists'][0]['reason'] == 'no_matching_observations'
    assert result['specialists'][1]['reason'] == 'no_usable_observations'
    assert result['run']['native_attempts'] == 2


def test_budget_preserves_author_and_review_slots_and_resume_does_not_reset(tmp_path, monkeypatch):
    seen = []
    monkeypatch.setattr(native_audit, 'run_native', lambda value, **kw: seen.append(kw['role']) or report())
    run = session(tmp_path, 2)
    result = pipeline(packet(), run)
    assert seen == ['author', 'reviewer']
    assert all(item['reason'] == 'native_budget_reserved_for_synthesis_review' for item in result['specialists'])
    again = pipeline(packet(), session(tmp_path, 2))
    assert seen == ['author', 'reviewer']
    assert again['native_status'] == 'unavailable; observations_retained'
    assert again['run']['native_attempts'] == 2


def test_failed_specialist_counts_and_does_not_hide_other_results(tmp_path, monkeypatch):
    def invoke(value, **options):
        if options['role'] == 'gsc-indexing-auditor':
            raise RuntimeError('secret host output')
        return report()
    monkeypatch.setattr(native_audit, 'run_native', invoke)
    result = pipeline(packet(), session(tmp_path))
    assert result['specialists'][0]['status'] == 'unavailable'
    assert result['specialists'][1]['status'] == 'returned; semantic_quality_unverified'
    assert result['native_status'] == 'partial; semantic_quality_unverified'
    assert result['run']['native_attempts'] == 4
    assert 'secret host output' not in json.dumps(result)


def test_specialist_cannot_cite_outside_selected_observations(tmp_path, monkeypatch):
    def invoke(value, **options):
        if options['role'].startswith('gsc-'):
            return {'claims': [{'text': 'Tools imply indexing.', 'status': 'supported',
                'source_refs': ['/observations/0/result/tools']}]}
        return report()
    monkeypatch.setattr(native_audit, 'run_native', invoke)
    result = pipeline(packet(), session(tmp_path))
    assert all(item['status'] == 'unavailable' for item in result['specialists'])
    assert result['native_status'] == 'partial; semantic_quality_unverified'
    with pytest.raises(ValueError, match='scope'):
        native_audit.validate_report({'claims': [{'text': 'All sources', 'status': 'supported',
            'source_refs': ['/observations']}]}, packet(), observation_indices=[1])


def test_parallel_roles_obey_concurrency_bound_and_keep_result_order(tmp_path, monkeypatch):
    lock = threading.Lock()
    active = peak = 0
    def invoke(value, **options):
        nonlocal active, peak
        if options['role'].startswith('gsc-'):
            with lock:
                active += 1
                peak = max(peak, active)
            time.sleep(0.02)
            with lock: active -= 1
        return report()
    monkeypatch.setattr(native_audit, 'run_native', invoke)
    result = native_audit.run_specialists(packet(), session=session(tmp_path), host='codex', model='caller-model',
        roles=['gsc-indexing-auditor', 'gsc-sitemap-auditor', 'gsc-page-analyst'], max_workers=2)
    assert peak == 2
    assert [item['role'] for item in result['specialists']] == [
        'gsc-indexing-auditor', 'gsc-sitemap-auditor', 'gsc-page-analyst']
    assert result['run']['native_attempts'] == 5


@pytest.mark.parametrize('changes', [
    {'roles': ['unknown']}, {'roles': ['gsc-indexing-auditor'] * 2},
    {'max_workers': 0}, {'max_workers': 5}, {'max_workers': True},
    {'model': ''}, {'host': 'none'},
])
def test_invalid_native_options_fail_before_model_dispatch(tmp_path, monkeypatch, changes):
    seen = []
    monkeypatch.setattr(native_audit, 'run_native', lambda *args, **kw: seen.append(kw))
    options = dict(host='codex', model='caller-model', roles=[])
    options.update(changes)
    with pytest.raises(ValueError):
        native_audit.run_specialists(packet(), session=session(tmp_path), **options)
    assert seen == []


def test_role_prompt_uses_projected_boundaries_with_both_native_hosts(tmp_path):
    executable = tmp_path / 'fake-host'
    log = tmp_path / 'prompts.jsonl'
    executable.write_text('#!/usr/bin/env python3\nimport json,sys\nfrom pathlib import Path\n'
        + f'with Path({str(log)!r}).open("a") as f: f.write(json.dumps(sys.stdin.read())+"\\n")\n'
        + f'report={report()!r}\n'
        + 'if "--output-last-message" in sys.argv:\n'
        + ' Path(sys.argv[sys.argv.index("--output-last-message")+1]).write_text(json.dumps(report))\n'
        + 'else: print(json.dumps({"structured_output":report}))\n')
    executable.chmod(0o700)
    for host in ('claude', 'codex'):
        value = packet()
        value['role_scope'] = {'observation_indices': [1]}
        native_audit.run_native(value, host=host, executable=executable, model='caller-model', role='gsc-indexing-auditor')
    prompts = [json.loads(line) for line in log.read_text().splitlines()]
    assert len(prompts) == 2
    assert all('sample' in prompt and 'site-wide' in prompt for prompt in prompts)
    assert all('UNKNOWN' in prompt and 'null' in prompt for prompt in prompts)
    assert all('Load the' not in prompt and 'model: sonnet' not in prompt for prompt in prompts)


def test_cli_preflights_native_options_before_acquisition_and_records_roles(tmp_path):
    import os
    from pathlib import Path
    import subprocess
    import sys
    script = Path(__file__).resolve().parents[1] / 'scripts/run_bounded_audit.py'
    config = dict(session(tmp_path, 3).config)
    config['allowed_tools'] = ['indexing_evidence_matrix']
    # New immutable run config; do not reuse the first run's identity.
    config['run_id'] = 'cli'
    config_file = tmp_path / 'config.json'
    config_file.write_text(json.dumps(config))
    requests = tmp_path / 'requests.json'
    requests.write_text(json.dumps([{'tool': 'indexing_evidence_matrix', 'arguments': {
        'site': config['site'], 'urls': ['https://example.com/page']}}]))
    output = tmp_path / 'output.json'
    command = [sys.executable, str(script), '--config', str(config_file), '--requests', str(requests),
               '--output', str(output), '--host', 'codex', '--specialist', 'gsc-indexing-auditor']
    rejected = subprocess.run(command, capture_output=True, text=True)
    assert rejected.returncode == 2
    assert AuditSession(config).status()['tool_calls'] == 0
    executable = tmp_path / 'codex'
    executable.write_text('#!/usr/bin/env python3\nimport json,sys\nfrom pathlib import Path\n'
        'sys.stdin.read()\n'
        'Path(sys.argv[sys.argv.index("--output-last-message")+1]).write_text(json.dumps({"claims":[{'
        '"text":"Indexing unavailable", "status":"unavailable", "source_refs":["/observations/0/result/rows/0/current_indexing_status"]}]}))\n')
    executable.chmod(0o700)
    child = subprocess.run([*command, '--model', 'caller-model'], capture_output=True, text=True,
        env={**os.environ, 'PATH': f'{tmp_path}:{os.environ["PATH"]}'})
    assert child.returncode == 0, child.stderr
    result = json.loads(output.read_text())
    assert result['specialists'][0]['role'] == 'gsc-indexing-auditor'
    assert result['specialists'][0]['status'].startswith('returned')
    assert result['run']['native_attempts'] == 3
    assert result['run']['provider_attempts'] == 0
    assert result['run']['tool_calls'] == 1
    assert output.stat().st_mode & 0o777 == 0o600


@pytest.mark.parametrize('failure', ['malformed_status', 'malformed_claude_envelope', 'oversized_reports'])
def test_cli_retains_observations_and_other_branches_after_invalid_model_output(tmp_path, failure):
    import os
    from pathlib import Path
    import subprocess
    import sys
    script = Path(__file__).resolve().parents[1] / 'scripts/run_bounded_audit.py'
    config = dict(session(tmp_path, 10).config, run_id='failure-cli',
        allowed_tools=['get_search_analytics', 'compare_search_periods', 'indexing_evidence_matrix'])
    config_file = tmp_path / 'config.json'; config_file.write_text(json.dumps(config))
    requests = tmp_path / 'requests.json'
    requests.write_text(json.dumps([{'tool': name, 'arguments': {'site': config['site']}}
        for name in config['allowed_tools']]))
    output = tmp_path / 'output.json'
    count = tmp_path / 'count'
    host = 'claude' if failure == 'malformed_claude_envelope' else 'codex'
    executable = tmp_path / host
    executable.write_text('#!/usr/bin/env python3\nimport json,sys\nfrom pathlib import Path\n'
        + f'counter=Path({str(count)!r})\n'
        + 'n=int(counter.read_text())+1 if counter.exists() else 1\ncounter.write_text(str(n))\n'
        + 'packet=json.loads(sys.stdin.read().split("SOURCE_PACKET:\\n",1)[1].rsplit("\\nEND_SOURCE_PACKET",1)[0])\n'
        + 'index=packet.get("role_scope",{}).get("observation_indices",[0])[0]\n'
        + f'failure={failure!r}\n'
        + 'text="x"*1100000 if failure=="oversized_reports" else "Indexing unavailable"\n'
        + 'status=[] if n==1 and failure=="malformed_status" else "unavailable"\n'
        + 'report={"claims":[{"text":text,"status":status,"source_refs":[f"/observations/{index}/result/current_indexing_status"]}]}\n'
        + 'if "--output-last-message" in sys.argv:\n'
        + ' Path(sys.argv[sys.argv.index("--output-last-message")+1]).write_text(json.dumps(report))\n'
        + 'else: print(json.dumps([] if n==1 else {"structured_output":report}))\n')
    executable.chmod(0o700)
    # Controlled acquisition boundary; the actual CLI and fake native processes
    # still exercise report isolation and byte limits without provider access.
    code = '''import json,runpy,sys
from gsc_mcp.registry import TOOLS
def source(site): return json.dumps({'current_indexing_status':'unknown'})
for name in ('get_search_analytics','compare_search_periods','indexing_evidence_matrix'): TOOLS[name]=source
sys.argv=sys.argv[1:]
runpy.run_path(sys.argv[0],run_name='__main__')
'''
    roles = [role for role in native_audit.ROLE_PROFILES if role != 'gsc-schema-auditor']
    options = [sys.executable, '-c', code, str(script), '--config', str(config_file),
        '--requests', str(requests), '--output', str(output), '--host', host, '--model', 'caller-model']
    for role in roles: options.extend(['--specialist', role])
    child = subprocess.run(options, capture_output=True, text=True,
        env={**os.environ, 'PATH': f'{tmp_path}:{os.environ["PATH"]}'})
    assert child.returncode == 0, child.stderr
    result = json.loads(output.read_text())
    assert len(result['observations']) == 3
    assert all(row['result']['current_indexing_status'] == 'unknown' for row in result['observations'])
    assert len(result['specialists']) == 8
    assert result['specialists'][0]['status'] == 'unavailable'
    assert result['native_status'] in {'partial; semantic_quality_unverified', 'unavailable; observations_retained'}
    assert result['run']['native_attempts'] == 10
    assert result['run']['provider_attempts'] == 0
    assert int(count.read_text()) == 10
    assert output.stat().st_size < 2_000_000
    if failure != 'oversized_reports':
        assert all(row['status'].startswith('returned') for row in result['specialists'][1:])
        assert result['native_execution']['author_status'].startswith('returned')
        assert result['native_execution']['reviewer_status'].startswith('returned')
