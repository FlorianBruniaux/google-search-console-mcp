#!/usr/bin/env python3
"""Offline claim evaluation, separate from query intent and extraction quality.

Annotation provenance is caller-declared, not authenticated. Synthetic success
cannot approve release; human targets and quality decisions remain independent.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

LABELS = {'supported', 'unsupported', 'unresolved'}
TRACKS = {'traffic_diagnosis', 'harmful_competition', 'report_fidelity'}


def require(value, message):
    if not value: raise ValueError(message)


def text(value):
    require(isinstance(value, str) and bool(value.strip()), 'Expected nonempty string')


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
        require(case['annotation']['annotator'] != case['annotation']['reviewer'], 'Independent human review required')
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


def evaluate(data, predictions, digest):
    shape(predictions, {'corpus_id', 'split', 'reviewer', 'predictions'})
    require(predictions['corpus_id'] == data['corpus_id'], 'Corpus mismatch')
    require(predictions['split'] in {'train', 'tuning', 'held_out'}, 'Unknown prediction split')
    text(predictions['reviewer'])
    selected = {case['id']: case for case in data['cases'] if case['split'] == predictions['split']}
    require(bool(selected), 'Empty selected split')
    require(isinstance(predictions['predictions'], list) and len(predictions['predictions']) <= 50000, 'Invalid predictions')
    predicted = {}
    for row in predictions['predictions']:
        shape(row, {'case_id', 'claim_id', 'label'})
        key = (row['case_id'], row['claim_id'])
        require(key not in predicted and row['label'] in LABELS, 'Invalid/duplicate prediction')
        require(row['case_id'] in selected, 'Prediction outside selected split')
        case = selected[row['case_id']]
        require(predictions['reviewer'] not in case['annotation'].values(), 'Evaluator identity must differ from label authors')
        require(any(c['id'] == row['claim_id'] for c in case['claims']), 'Unknown claim')
        predicted[key] = row['label']
    tracks = {}
    for case in selected.values():
        stats = tracks.setdefault(case['track'], {'total': 0, 'correct': 0, 'predicted': 0, 'unsupported_as_supported': 0})
        for claim in case['claims']:
            label = predicted.get((case['id'], claim['id']))
            stats['total'] += 1
            stats['predicted'] += label is not None
            stats['correct'] += label == claim['label']
            stats['unsupported_as_supported'] += claim['label'] == 'unsupported' and label == 'supported'
    total = sum(s['total'] for s in tracks.values())
    correct = sum(s['correct'] for s in tracks.values())
    return {'corpus_id': data['corpus_id'], 'dataset_sha256': digest,
            'annotation_provenance': data['provenance'], 'total': total, 'correct': correct,
            'accuracy': correct / total, 'prediction_coverage': len(predicted) / total,
            'by_track': tracks, 'release_gate': 'unavailable',
            'limitations': 'Declared annotations are not authenticated. No approved pre-tuning target or human release decision is supplied by this evaluator.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset', required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--prepare', action='store_true')
    mode.add_argument('--predictions')
    parser.add_argument('--split', choices=['train', 'tuning', 'held_out'], default='held_out')
    args = parser.parse_args()
    try:
        data, digest = load(args.dataset); validate(data)
        result = author_packet(data, args.split) if args.prepare else evaluate(data, load(args.predictions)[0], digest)
        print(json.dumps(result, ensure_ascii=False, allow_nan=False))
    except (ValueError, TypeError, KeyError, OSError, RecursionError) as error:
        parser.exit(2, f'Invalid evaluation input: {error}\n')


if __name__ == '__main__': main()
