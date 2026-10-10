"""Human report labels must remain independent from report generation."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/eval_audit_reports.py'


def corpus():
    return {'schema_version': 1, 'corpus_id': 'synthetic-boundary', 'provenance': 'synthetic',
            'cases': [{'id': 'case', 'family_id': 'same-site', 'split': 'held_out',
                'track': 'report_fidelity', 'language': 'fr',
                'annotation': {'annotator': 'one', 'reviewer': 'two', 'source_authorization': 'synthetic fixture', 'disagreement_resolution': 'none'},
                'observations': {'clicks': None, 'site': 'sc-domain:example.com'},
                'claims': [{'id': 'c1', 'text': 'Traffic was measured at zero.', 'label': 'unsupported', 'source_refs': ['/clicks']},
                           {'id': 'c2', 'text': 'Traffic is unavailable.', 'label': 'supported', 'source_refs': ['/clicks']}]}]}


def evaluate(tmp_path, data, predictions=None, prepare=False):
    assert SCRIPT.exists(), 'audit report evaluator is not implemented'
    path = tmp_path / 'corpus.json'; path.write_text(json.dumps(data))
    args = [sys.executable, str(SCRIPT), '--dataset', str(path)]
    if prepare: args += ['--prepare']
    else:
        pred = tmp_path / 'predictions.json'; pred.write_text(json.dumps(predictions))
        args += ['--predictions', str(pred)]
    result = subprocess.run(args, capture_output=True, text=True)
    return result, json.loads(result.stdout) if result.returncode == 0 else None


def test_author_packet_does_not_expose_annotation_labels(tmp_path):
    result, packet = evaluate(tmp_path, corpus(), prepare=True)
    assert result.returncode == 0, result.stderr
    assert packet['cases'][0] == {'id': 'case', 'track': 'report_fidelity', 'language': 'fr',
                                  'observations': {'clicks': None, 'site': 'sc-domain:example.com'}}
    assert 'claims' not in packet['cases'][0]
    assert 'annotation' not in packet['cases'][0]


def test_synthetic_correct_predictions_do_not_approve_release(tmp_path):
    predictions = {'corpus_id': 'synthetic-boundary', 'split': 'held_out', 'reviewer': 'model-review',
                   'predictions': [{'case_id': 'case', 'claim_id': 'c1', 'label': 'supported'},
                                   {'case_id': 'case', 'claim_id': 'c2', 'label': 'supported'}]}
    result, report = evaluate(tmp_path, corpus(), predictions)
    assert result.returncode == 0, result.stderr
    assert report['correct'] == 1 and report['total'] == 2
    assert report['accuracy'] == 0.5
    assert report['release_gate'] == 'unavailable'
    assert report['by_track']['report_fidelity']['unsupported_as_supported'] == 1


@pytest.mark.parametrize('failure', ['self_review', 'family_leakage', 'missing_reference', 'duplicate_claim'])
def test_invalid_human_packet_fails_before_evaluation(tmp_path, failure):
    data = corpus()
    data['provenance'] = 'human'
    case = data['cases'][0]
    if failure == 'self_review': case['annotation']['reviewer'] = 'one'
    elif failure == 'family_leakage':
        second = json.loads(json.dumps(case)); second.update(id='other', split='tuning'); data['cases'].append(second)
    elif failure == 'missing_reference': case['claims'][0]['source_refs'] = ['/missing']
    elif failure == 'duplicate_claim': case['claims'].append(case['claims'][0])
    result, _ = evaluate(tmp_path, data, prepare=True)
    assert result.returncode != 0
