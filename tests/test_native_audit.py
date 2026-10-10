import importlib
import json

import pytest


def native():
    assert importlib.util.find_spec('gsc_mcp.native_audit'), 'native adapter is not implemented'
    return importlib.import_module('gsc_mcp.native_audit')


def packet():
    return {'run': {'site': 'sc-domain:example.com', 'provider_attempts': 0},
            'observations': [{'tool': 'indexing_evidence_matrix', 'result': {'rows': [{'current_indexing_status': 'unknown'}]}}]}


def test_packet_validation_rejects_missing_references_and_unavailable_as_fact():
    api = native()
    with pytest.raises(ValueError, match='reference'):
        api.validate_report({'claims': [{'text': 'Indexed', 'status': 'supported', 'source_refs': ['/missing']}]}, packet())
    with pytest.raises(ValueError):
        api.validate_report({'claims': [{'text': 'Indexed', 'status': 'supported', 'source_refs': []}]}, packet())
    report = {'claims': [{'text': 'Current indexing is unknown.', 'status': 'unavailable', 'source_refs': ['/observations/0/result/rows/0/current_indexing_status']}]}
    assert api.validate_report(report, packet()) == report


def test_claude_adapter_transmits_sources_without_enabling_tools(tmp_path):
    api = native()
    executable = tmp_path / 'fake-claude'
    log = tmp_path / 'arguments.json'
    executable.write_text('#!/usr/bin/env python3\nimport json,sys\nfrom pathlib import Path\n'
                          + f'Path({str(log)!r}).write_text(json.dumps({{"args":sys.argv[1:],"stdin":sys.stdin.read()}}))\n'
                          + 'print(json.dumps({"structured_output":{"claims":[{"text":"Unavailable","status":"unavailable","source_refs":["/observations/0/result/rows/0/current_indexing_status"]}]}}))\n')
    executable.chmod(0o700)
    report = api.run_native(packet(), host='claude', executable=str(executable), model='caller-model')
    invocation = json.loads(log.read_text())
    args = invocation['args']
    assert args[args.index('--tools') + 1] == ''
    assert '--strict-mcp-config' in args
    assert args[args.index('--effort') + 1] == 'high'
    assert 'current_indexing_status' in invocation['stdin']
    assert report['claims'][0]['status'] == 'unavailable'


def test_codex_adapter_uses_high_reasoning_and_private_final_output(tmp_path):
    api = native()
    executable = tmp_path / 'fake-codex'
    executable.write_text('#!/usr/bin/env python3\nimport json,sys\nfrom pathlib import Path\n'
        'assert "read-only" in sys.argv and "--ignore-user-config" in sys.argv\n'
        'assert "model_reasoning_effort=\\\"high\\\"" in sys.argv\n'
        'sys.stdin.read()\n'
        'Path(sys.argv[sys.argv.index("--output-last-message")+1]).write_text(json.dumps({"claims":[{"text":"Unavailable","status":"unavailable","source_refs":["/observations/0/result/rows/0/current_indexing_status"]}]}))\n')
    executable.chmod(0o700)
    report = api.run_native(packet(), host='codex', executable=str(executable), model='caller-model')
    assert report['claims'][0]['status'] == 'unavailable'


def test_native_failure_is_not_a_reviewed_or_healthy_report(tmp_path):
    api = native()
    executable = tmp_path / 'failed'
    executable.write_text('#!/bin/sh\nexit 7\n'); executable.chmod(0o700)
    with pytest.raises(RuntimeError, match='unavailable'):
        api.run_native(packet(), host='claude', executable=str(executable), model='caller-model')


def test_reviewer_cannot_use_the_draft_as_factual_evidence():
    api = native()
    source = packet()
    source['draft'] = {'claims': [{'text': 'Indexed', 'status': 'supported', 'source_refs': ['/observations/0/result/rows/0/current_indexing_status']}]}
    report = {'claims': [{'text': 'Indexed', 'status': 'supported', 'source_refs': ['/draft/claims/0/text']}]}
    with pytest.raises(ValueError, match='observation'):
        api.validate_report(report, source)
    report['claims'][0]['source_refs'].append('/observations/0/result/rows/0/current_indexing_status')
    # References are now source-bound; semantic truth still requires evaluation.
    assert api.validate_report(report, source) == report
