#!/usr/bin/env python3
"""Offline claim evaluation, separate from query intent and extraction quality.

Annotation provenance is caller-declared, not authenticated. Synthetic success
cannot approve release; human targets and quality decisions remain independent.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

LABELS = {'supported', 'unsupported', 'unresolved'}
TRACKS = {'traffic_diagnosis', 'harmful_competition', 'report_fidelity'}


def require(value, message):
    if not value: raise ValueError(message)


def text(value):
    require(isinstance(value, str) and bool(value.strip()), 'Expected nonempty string')


def identity(value):
    text(value)
    return ' '.join(value.casefold().split())


def shape(value, fields):
    require(isinstance(value, dict) and set(value) == set(fields), 'Invalid object fields')


def unique_keys(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'Duplicate JSON key')
        result[key] = value
    return result


def load(path):
    with open(path, 'rb') as handle: raw = handle.read(2_000_001)
    require(len(raw) <= 2_000_000, 'Input byte budget exceeded')
    result = json.loads(raw, object_pairs_hook=unique_keys,
                        parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Nonfinite JSON value')))
    return result, hashlib.sha256(raw).hexdigest()


def pointer(value, ref):
    text(ref)
    require(ref.startswith('/'), 'Expected JSON pointer')
    for raw in ref[1:].split('/'):
        import re
        require(not re.search(r'~(?![01])', raw), 'Invalid JSON pointer escape')
        key = raw.replace('~1', '/').replace('~0', '~')
        if isinstance(value, list):
            require(key.isdecimal() and int(key) < len(value), 'Missing source reference')
            value = value[int(key)]
        else:
            require(isinstance(value, dict) and key in value, 'Missing source reference')
            value = value[key]
    return value


def validate(data):
    shape(data, {'schema_version', 'corpus_id', 'provenance', 'cases'})
    require(type(data['schema_version']) is int and data['schema_version'] == 1, 'Unsupported schema')
    text(data['corpus_id'])
    require(data['provenance'] in {'human', 'synthetic'}, 'Unknown provenance')
    require(isinstance(data['cases'], list) and 0 < len(data['cases']) <= 500, 'Invalid case count')
    identities, families = set(), {}
    for case in data['cases']:
        shape(case, {'id', 'family_id', 'split', 'track', 'language', 'annotation', 'observations', 'claims'})
        for key in ('id', 'family_id'): text(case[key])
        require(case['id'] not in identities, 'Duplicate case identity'); identities.add(case['id'])
        require(case['split'] in {'train', 'tuning', 'held_out'}, 'Unknown split')
        require(families.setdefault(case['family_id'], case['split']) == case['split'], 'Family crosses splits')
        require(case['track'] in TRACKS and case['language'] in {'fr', 'en'}, 'Unknown task/language')
        shape(case['annotation'], {'annotator', 'reviewer', 'source_authorization', 'disagreement_resolution'})
        for item in case['annotation'].values(): text(item)
        require(identity(case['annotation']['annotator']) != identity(case['annotation']['reviewer']),
                'Independent human review required')
        require(isinstance(case['observations'], dict), 'Expected source observation object')
        require(isinstance(case['claims'], list) and 0 < len(case['claims']) <= 100, 'Invalid claim count')
        claim_ids = set()
        for claim in case['claims']:
            shape(claim, {'id', 'text', 'label', 'source_refs'})
            text(claim['id']); text(claim['text'])
            require(claim['id'] not in claim_ids, 'Duplicate claim identity'); claim_ids.add(claim['id'])
            require(claim['label'] in LABELS, 'Unknown claim label')
            require(isinstance(claim['source_refs'], list) and bool(claim['source_refs']), 'Required source references')
            for ref in claim['source_refs']: pointer(case['observations'], ref)


def author_packet(data, split):
    selected = [case for case in data['cases'] if case['split'] == split]
    require(bool(selected), 'Empty selected split')
    return {'corpus_id': data['corpus_id'], 'provenance': data['provenance'],
            'cases': [{key: case[key] for key in ('id', 'track', 'language', 'observations')} for case in selected]}


def metrics_for(rows):
    """Claim-weighted metrics; missing predictions never enter the confusion matrix."""
    labels = sorted(LABELS)
    confusion = {actual: {predicted: 0 for predicted in labels} for actual in labels}
    for actual, predicted in rows:
        if predicted is not None:
            confusion[actual][predicted] += 1
    per_label = {}
    for label in labels:
        support = sum(actual == label for actual, _ in rows)
        predicted_count = sum(predicted == label for _, predicted in rows)
        true_positive = confusion[label][label]
        per_label[label] = {
            'support': support, 'predicted_count': predicted_count,
            'true_positive_count': true_positive,
            'precision': true_positive / predicted_count if predicted_count else None,
            'recall': true_positive / support if support else None,
            'precision_unavailable_reason': None if predicted_count else 'no_predictions',
            'recall_unavailable_reason': None if support else 'no_support',
        }
    total = len(rows)
    predicted = sum(value is not None for _, value in rows)
    correct = sum(actual == value for actual, value in rows)
    false_supported = confusion['unsupported']['supported']
    unsupported_support = per_label['unsupported']['support']
    return {
        'total': total, 'predicted': predicted, 'correct': correct,
        'accuracy': correct / total if total else None,
        'prediction_coverage': predicted / total if total else None,
        'missing_predictions': total - predicted,
        'unresolved_predictions': sum(value == 'unresolved' for _, value in rows),
        'unsupported_as_supported': false_supported,
        'unsupported_as_supported_rate': (
            false_supported / unsupported_support if unsupported_support else None),
        'per_label': per_label, 'confusion': confusion,
    }


def evaluate(data, predictions, digest):
    shape(predictions, {'corpus_id', 'split', 'reviewer', 'predictions'})
    require(predictions['corpus_id'] == data['corpus_id'], 'Corpus mismatch')
    require(predictions['split'] in {'train', 'tuning', 'held_out'}, 'Unknown prediction split')
    text(predictions['reviewer'])
    selected = {case['id']: case for case in data['cases'] if case['split'] == predictions['split']}
    require(bool(selected), 'Empty selected split')
    for case in selected.values():
        require(identity(predictions['reviewer']) not in {
            identity(case['annotation']['annotator']), identity(case['annotation']['reviewer'])},
            'Evaluator identity must differ from label authors')
    require(isinstance(predictions['predictions'], list) and len(predictions['predictions']) <= 50000, 'Invalid predictions')
    predicted = {}
    for row in predictions['predictions']:
        shape(row, {'case_id', 'claim_id', 'label'})
        key = (row['case_id'], row['claim_id'])
        require(key not in predicted and row['label'] in LABELS, 'Invalid/duplicate prediction')
        require(row['case_id'] in selected, 'Prediction outside selected split')
        case = selected[row['case_id']]
        require(any(c['id'] == row['claim_id'] for c in case['claims']), 'Unknown claim')
        predicted[key] = row['label']
    tracks, languages, strata, all_rows = {}, {}, {}, []
    for case in selected.values():
        track_rows = tracks.setdefault(case['track'], [])
        language_rows = languages.setdefault(case['language'], [])
        stratum_rows = strata.setdefault(case['track'], {}).setdefault(case['language'], [])
        for claim in case['claims']:
            label = predicted.get((case['id'], claim['id']))
            row = (claim['label'], label)
            for group in (track_rows, language_rows, stratum_rows, all_rows):
                group.append(row)
    return {'corpus_id': data['corpus_id'], 'dataset_sha256': digest,
            'annotation_provenance': data['provenance'], 'split': predictions['split'],
            **metrics_for(all_rows),
            'by_track': {key: metrics_for(rows) for key, rows in sorted(tracks.items())},
            'by_language': {key: metrics_for(rows) for key, rows in sorted(languages.items())},
            'by_track_language': {
                track: {language: metrics_for(rows) for language, rows in sorted(groups.items())}
                for track, groups in sorted(strata.items())},
            'release_gate': 'unavailable',
            'limitations': 'Declared annotations are not authenticated. No approved pre-tuning target or human release decision is supplied by this evaluator.'}


def validate_target_manifest(manifest, dataset_sha, corpus_id, provenance, split):
    shape(manifest, {'schema_version', 'corpus_id', 'dataset_sha256', 'split',
                     'annotation_provenance', 'review_reference', 'frozen_before_tuning', 'targets'})
    require(type(manifest['schema_version']) is int and manifest['schema_version'] == 1,
            'Unsupported target manifest schema')
    require(manifest['corpus_id'] == corpus_id, 'Target corpus mismatch')
    require(manifest['dataset_sha256'] == dataset_sha, 'Frozen dataset hash mismatch')
    require(manifest['annotation_provenance'] == provenance, 'Target provenance mismatch')
    require(manifest['split'] == split == 'held_out', 'Targets require the held_out split')
    require(manifest['frozen_before_tuning'] is True, 'Pre-tuning freeze declaration required')
    text(manifest['review_reference'])
    require(isinstance(manifest['targets'], list) and 0 < len(manifest['targets']) <= 18,
            'Expected 1 to 18 stratum targets')
    identities = set()
    for target in manifest['targets']:
        shape(target, {'track', 'language', 'label', 'min_support', 'min_precision',
                       'min_recall', 'min_coverage', 'max_unsupported_as_supported'})
        require(target['track'] in TRACKS and target['language'] in {'fr', 'en'}
                and target['label'] in LABELS, 'Unknown target stratum')
        key = (target['track'], target['language'], target['label'])
        require(key not in identities, 'Duplicate target stratum')
        identities.add(key)
        require(type(target['min_support']) is int and 1 <= target['min_support'] <= 50000,
                'Support target must be a positive bounded integer')
        require(type(target['max_unsupported_as_supported']) is int
                and 0 <= target['max_unsupported_as_supported'] <= 50000,
                'False-supported ceiling must be a bounded nonnegative integer')
        for field in ('min_precision', 'min_recall', 'min_coverage'):
            value = target[field]
            require(type(value) in (int, float) and 0 <= value <= 1 and math.isfinite(value),
                    'Expected a finite target between zero and one')


def observed_strata(report):
    return [
        {'track': track, 'language': language, 'label': label}
        for track, languages in report['by_track_language'].items()
        for language, stats in languages.items()
        for label, counts in stats['per_label'].items() if counts['support']
    ]


def assess_report_targets(report, manifest):
    targeted = set()
    results = []
    for target in manifest['targets']:
        key = (target['track'], target['language'], target['label'])
        targeted.add(key)
        stats = report['by_track_language'].get(key[0], {}).get(key[1], metrics_for([]))
        label = stats['per_label'][key[2]]
        observed = {
            'support': label['support'], 'precision': label['precision'],
            'recall': label['recall'], 'coverage': stats['prediction_coverage'],
            'unsupported_as_supported': stats['unsupported_as_supported'],
        }
        checks = {'min_support': observed['support'] >= target['min_support'],
                  'max_unsupported_as_supported': observed['unsupported_as_supported']
                  <= target['max_unsupported_as_supported']}
        for field in ('precision', 'recall', 'coverage'):
            checks['min_' + field] = (observed[field] is not None
                                      and observed[field] >= target['min_' + field])
        status = ('insufficient_support' if not checks['min_support'] else
                  'met' if all(checks.values()) else 'failed')
        results.append({'track': key[0], 'language': key[1], 'label': key[2],
                        'status': status, 'observed': observed, 'targets': target,
                        'checks': checks})
    statuses = {item['status'] for item in results}
    status = ('insufficient_support' if 'insufficient_support' in statuses else
              'failed' if 'failed' in statuses else 'met')
    untargeted = [row for row in observed_strata(report)
                  if (row['track'], row['language'], row['label']) not in targeted]
    return {'target_assessment': status, 'target_checks': results,
            'target_scope': 'listed_targets_only', 'untargeted_strata': untargeted}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset', required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--prepare', action='store_true')
    mode.add_argument('--predictions')
    parser.add_argument('--split', choices=['train', 'tuning', 'held_out'], default='held_out')
    parser.add_argument('--manifest', help='Frozen held-out report targets; unavailable without human review')
    args = parser.parse_args()
    try:
        data, digest = load(args.dataset); validate(data)
        if args.prepare:
            require(args.manifest is None, '--manifest requires --predictions')
            result = author_packet(data, args.split)
        else:
            predictions, prediction_digest = load(args.predictions)
            shape(predictions, {'corpus_id', 'split', 'reviewer', 'predictions'})
            manifest, manifest_digest = load(args.manifest) if args.manifest is not None else (None, None)
            if args.manifest is not None:
                validate_target_manifest(manifest, digest, data['corpus_id'],
                                         data['provenance'], predictions.get('split'))
            result = evaluate(data, predictions, digest)
            result.update(predictions_sha256=prediction_digest, manifest_sha256=manifest_digest,
                          declarations_authenticated=False, synthetic_release_eligible=False,
                          target_assessment='unavailable', target_checks=[],
                          target_scope='listed_targets_only',
                          untargeted_strata=observed_strata(result))
            if args.manifest is not None:
                result.update(assess_report_targets(result, manifest))
            result['limitations'] = (
                'Identity, authorization and pre-tuning freeze are declarations, not authenticated. '
                'Numerical target results cover listed strata only, not release approval. '
                'Claim metrics do not assess missing prose claims or establish causal truth.')
        print(json.dumps(result, ensure_ascii=False, allow_nan=False))
    except (ValueError, TypeError, KeyError, OSError, RecursionError) as error:
        parser.exit(2, f'Invalid evaluation input: {error}\n')


if __name__ == '__main__': main()
