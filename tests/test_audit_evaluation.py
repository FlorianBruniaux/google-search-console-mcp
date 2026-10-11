"""Human report labels must remain independent from report generation."""
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


def stratified_corpus():
    data = corpus()
    first = data['cases'][0]
    labels = ['supported', 'supported', 'unsupported', 'unresolved', 'unsupported']
    first['claims'] = [
        {'id': 'c' + str(i), 'text': 'Synthetic claim ' + str(i),
         'label': label, 'source_refs': ['/clicks']}
        for i, label in enumerate(labels, 1)
    ]
    second = json.loads(json.dumps(first))
    second.update(id='english', family_id='other-site', language='en',
                  track='traffic_diagnosis')
    second['claims'] = [
        {'id': 'c1', 'text': 'Synthetic English claim', 'label': 'supported',
         'source_refs': ['/clicks']},
        {'id': 'c2', 'text': 'Synthetic English claim two', 'label': 'unsupported',
         'source_refs': ['/clicks']},
    ]
    data['cases'].append(second)
    return data


def stratified_predictions():
    return {
        'corpus_id': 'synthetic-boundary', 'split': 'held_out', 'reviewer': 'independent',
        'predictions': [
            {'case_id': 'case', 'claim_id': 'c1', 'label': 'supported'},
            {'case_id': 'case', 'claim_id': 'c3', 'label': 'supported'},
            {'case_id': 'case', 'claim_id': 'c4', 'label': 'unresolved'},
            {'case_id': 'case', 'claim_id': 'c5', 'label': 'unsupported'},
            {'case_id': 'english', 'claim_id': 'c1', 'label': 'unsupported'},
        ],
    }


def test_stratified_metrics_count_missing_answers_and_false_supported(tmp_path):
    result, report = evaluate(tmp_path, stratified_corpus(), stratified_predictions())
    assert result.returncode == 0, result.stderr
    assert report['accuracy'] == pytest.approx(3 / 7)
    assert report['prediction_coverage'] == pytest.approx(5 / 7)
    fr = report['by_track_language']['report_fidelity']['fr']
    assert fr['total'] == 5 and fr['predicted'] == 4 and fr['correct'] == 3
    assert fr['missing_predictions'] == 1
    assert fr['unresolved_predictions'] == 1
    assert fr['prediction_coverage'] == 0.8
    assert fr['per_label']['supported']['precision'] == 0.5
    assert fr['per_label']['supported']['recall'] == 0.5
    assert fr['per_label']['unsupported']['recall'] == 0.5
    assert fr['unsupported_as_supported'] == 1
    assert fr['unsupported_as_supported_rate'] == 0.5
    assert fr['confusion']['unsupported']['supported'] == 1
    assert sum(sum(row.values()) for row in fr['confusion'].values()) == 4
    assert report['by_language']['en']['total'] == 2
    assert report['by_language']['fr'] == report['by_track']['report_fidelity']


def test_missing_prediction_is_not_an_unresolved_label(tmp_path):
    predicted = stratified_predictions()
    predicted['predictions'] = []
    result, report = evaluate(tmp_path, corpus(), predicted)
    assert result.returncode == 0, result.stderr
    stats = report['by_track']['report_fidelity']
    assert stats['missing_predictions'] == 2
    assert stats['unresolved_predictions'] == 0
    assert stats['prediction_coverage'] == 0
    assert stats['per_label']['supported']['precision'] is None
    assert stats['per_label']['supported']['recall'] == 0
    assert stats['per_label']['unresolved']['recall'] is None
    assert stats['per_label']['supported']['precision_unavailable_reason'] == 'no_predictions'
    assert stats['per_label']['unresolved']['recall_unavailable_reason'] == 'no_support'
    assert report['release_gate'] == 'unavailable'


def test_absent_unsupported_support_has_no_zero_false_positive_rate(tmp_path):
    data = corpus()
    data['cases'][0]['claims'] = [data['cases'][0]['claims'][1]]
    pred = stratified_predictions()
    pred['predictions'] = [{'case_id': 'case', 'claim_id': 'c2', 'label': 'supported'}]
    result, report = evaluate(tmp_path, data, pred)
    assert result.returncode == 0, result.stderr
    stats = report['by_track']['report_fidelity']
    assert stats['unsupported_as_supported_rate'] is None
    assert stats['per_label']['unresolved']['precision'] is None
    assert stats['per_label']['unresolved']['recall'] is None


@pytest.mark.parametrize('prepare', [True, False])
def test_normalized_self_review_is_rejected_even_without_predictions(tmp_path, prepare):
    data = corpus()
    if prepare:
        data['cases'][0]['annotation']['reviewer'] = ' ONE '
    pred = stratified_predictions()
    pred.update(reviewer=' ONE ', predictions=[])
    result, _ = evaluate(tmp_path, data, pred, prepare=prepare)
    assert result.returncode == 2, result.stderr


def report_targets():
    return {
        'schema_version': 1, 'corpus_id': 'synthetic-boundary',
        'dataset_sha256': 'AUTO', 'split': 'held_out',
        'annotation_provenance': 'synthetic',
        'review_reference': 'synthetic-fixture-only', 'frozen_before_tuning': True,
        'targets': [{
            'track': 'report_fidelity', 'language': 'fr', 'label': 'supported',
            'min_support': 1, 'min_precision': 1.0, 'min_recall': 1.0,
            'min_coverage': 1.0, 'max_unsupported_as_supported': 0,
        }],
    }


def manifest_evaluation(tmp_path, data=None, predictions=None, manifest=None):
    import hashlib
    data = corpus() if data is None else data
    if predictions is None:
        predictions = stratified_predictions()
        predictions['predictions'] = [
            {'case_id': 'case', 'claim_id': 'c1', 'label': 'unsupported'},
            {'case_id': 'case', 'claim_id': 'c2', 'label': 'supported'},
        ]
    manifest = report_targets() if manifest is None else manifest
    paths = {key: tmp_path / (key + '.json') for key in ('dataset', 'predictions', 'manifest')}
    paths['dataset'].write_text(json.dumps(data))
    paths['predictions'].write_text(json.dumps(predictions))
    manifest = json.loads(json.dumps(manifest))
    if manifest.get('dataset_sha256') == 'AUTO':
        manifest['dataset_sha256'] = hashlib.sha256(paths['dataset'].read_bytes()).hexdigest()
    paths['manifest'].write_text(json.dumps(manifest))
    result = subprocess.run(
        [sys.executable, '-I', str(SCRIPT), '--dataset', str(paths['dataset']),
         '--predictions', str(paths['predictions']), '--manifest', str(paths['manifest'])],
        capture_output=True, text=True)
    return result, json.loads(result.stdout) if result.returncode == 0 else None, paths


def test_frozen_report_targets_are_hash_bound_and_never_approve_release(tmp_path):
    import hashlib
    result, report, paths = manifest_evaluation(tmp_path)
    assert result.returncode == 0, result.stderr
    assert report['target_assessment'] == 'met'
    assert report['target_scope'] == 'listed_targets_only'
    assert report['manifest_sha256'] == hashlib.sha256(paths['manifest'].read_bytes()).hexdigest()
    assert report['target_checks'][0]['status'] == 'met'
    assert report['release_gate'] == 'unavailable'
    assert report['synthetic_release_eligible'] is False


def test_declared_human_data_and_met_targets_still_do_not_approve_release(tmp_path):
    data = corpus()
    data['provenance'] = 'human'
    manifest = report_targets()
    manifest['annotation_provenance'] = 'human'
    result, report, _ = manifest_evaluation(tmp_path, data=data, manifest=manifest)
    assert result.returncode == 0, result.stderr
    assert report['target_assessment'] == 'met'
    assert report['release_gate'] == 'unavailable'
    assert report['declarations_authenticated'] is False


def test_no_manifest_is_explicitly_unavailable(tmp_path):
    result, report = evaluate(tmp_path, corpus(), stratified_predictions() | {'predictions': []})
    assert result.returncode == 0, result.stderr
    assert report['target_assessment'] == 'unavailable'
    assert report['manifest_sha256'] is None
    assert report['target_checks'] == []


@pytest.mark.parametrize('failure', ['too_little_support', 'absent_language', 'absent_track',
                                     'false_supported', 'empty_predictions'])
def test_target_failure_and_insufficient_support_are_distinct(tmp_path, failure):
    targets = report_targets()
    pred = stratified_predictions()
    pred['predictions'] = [
        {'case_id': 'case', 'claim_id': 'c1', 'label': 'unsupported'},
        {'case_id': 'case', 'claim_id': 'c2', 'label': 'supported'},
    ]
    target = targets['targets'][0]
    if failure == 'too_little_support':
        target['min_support'] = 2
    elif failure == 'absent_language':
        target['language'] = 'en'
    elif failure == 'absent_track':
        target['track'] = 'traffic_diagnosis'
    elif failure == 'false_supported':
        pred['predictions'][0]['label'] = 'supported'
    else:
        pred['predictions'] = []
    result, report, _ = manifest_evaluation(tmp_path, predictions=pred, manifest=targets)
    assert result.returncode == 0, result.stderr
    expected = 'insufficient_support' if failure in {
        'too_little_support', 'absent_language', 'absent_track'} else 'failed'
    assert report['target_assessment'] == expected
    assert report['target_checks'][0]['status'] == expected
    assert report['release_gate'] == 'unavailable'


def test_targets_disclose_untargeted_strata(tmp_path):
    target = report_targets()
    target['targets'][0].update(min_precision=0.5, min_recall=0.5,
                               min_coverage=0.8, max_unsupported_as_supported=1)
    result, report, _ = manifest_evaluation(
        tmp_path, stratified_corpus(), stratified_predictions(), target)
    assert result.returncode == 0, result.stderr
    assert report['target_assessment'] == 'met'
    assert {'track': 'traffic_diagnosis', 'language': 'en', 'label': 'supported'} in report['untargeted_strata']
    assert {'track': 'report_fidelity', 'language': 'fr', 'label': 'unsupported'} in report['untargeted_strata']


@pytest.mark.parametrize('failure', [
    'wrong_hash', 'wrong_corpus', 'wrong_split', 'wrong_provenance', 'unfrozen',
    'missing_review', 'duplicate_target', 'empty_targets', 'unknown_label',
    'boolean_threshold', 'nonfinite_threshold', 'fractional_support', 'zero_support',
    'negative_false_supported', 'unknown_field', 'out_of_range',
])
def test_invalid_report_targets_fail_before_scoring(tmp_path, failure):
    manifest = report_targets()
    target = manifest['targets'][0]
    if failure == 'wrong_hash':
        manifest['dataset_sha256'] = '0' * 64
    elif failure == 'wrong_corpus':
        manifest['corpus_id'] = 'different'
    elif failure == 'wrong_split':
        manifest['split'] = 'tuning'
    elif failure == 'wrong_provenance':
        manifest['annotation_provenance'] = 'human'
    elif failure == 'unfrozen':
        manifest['frozen_before_tuning'] = False
    elif failure == 'missing_review':
        manifest['review_reference'] = ''
    elif failure == 'duplicate_target':
        manifest['targets'].append(dict(target))
    elif failure == 'empty_targets':
        manifest['targets'] = []
    elif failure == 'unknown_label':
        target['label'] = 'harmful'
    elif failure == 'boolean_threshold':
        target['min_precision'] = True
    elif failure == 'nonfinite_threshold':
        target['min_recall'] = float('nan')
    elif failure == 'fractional_support':
        target['min_support'] = 0.5
    elif failure == 'zero_support':
        target['min_support'] = 0
    elif failure == 'negative_false_supported':
        target['max_unsupported_as_supported'] = -1
    elif failure == 'unknown_field':
        target['approved'] = True
    else:
        target['min_coverage'] = 1.1
    result, _, _ = manifest_evaluation(tmp_path, manifest=manifest)
    assert result.returncode == 2
    assert not result.stdout
    assert 'Invalid evaluation input' in result.stderr


def test_non_object_prediction_json_is_rejected_without_a_traceback(tmp_path):
    result, _, _ = manifest_evaluation(tmp_path, predictions=[])
    assert result.returncode == 2
    assert not result.stdout
    assert 'Traceback' not in result.stderr


def test_huge_numeric_target_is_rejected_without_a_traceback(tmp_path):
    manifest = report_targets()
    manifest['targets'][0]['min_precision'] = 10 ** 500
    result, _, _ = manifest_evaluation(tmp_path, manifest=manifest)
    assert result.returncode == 2
    assert 'Traceback' not in result.stderr


def test_absent_manifest_lists_all_observed_strata_as_untargeted(tmp_path):
    pred = stratified_predictions() | {'predictions': []}
    result, report = evaluate(tmp_path, corpus(), pred)
    assert result.returncode == 0, result.stderr
    assert report['untargeted_strata'] == [
        {'track': 'report_fidelity', 'language': 'fr', 'label': 'supported'},
        {'track': 'report_fidelity', 'language': 'fr', 'label': 'unsupported'},
    ]

def test_tuning_cannot_use_held_out_release_targets(tmp_path):
    data = corpus()
    data['cases'][0]['split'] = 'tuning'
    pred = stratified_predictions()
    pred.update(split='tuning', predictions=[])
    result, _, _ = manifest_evaluation(tmp_path, data, pred)
    assert result.returncode == 2


def test_prepare_rejects_a_target_manifest_and_stays_label_free(tmp_path):
    result, _, paths = manifest_evaluation(tmp_path)
    assert result.returncode == 0, result.stderr
    result = subprocess.run(
        [sys.executable, str(SCRIPT), '--dataset', str(paths['dataset']),
         '--prepare', '--manifest', str(paths['manifest'])], capture_output=True, text=True)
    assert result.returncode == 2
    assert not result.stdout
