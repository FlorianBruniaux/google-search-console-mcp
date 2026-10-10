#!/usr/bin/env python3
"""Produce offline intent predictions for the existing evaluation harness."""
import argparse
import json

from eval_classifier import load_json, validate_dataset
from gsc_mcp.query_rules import classify


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset', required=True)
    parser.add_argument('--split', choices=['train', 'tuning', 'held_out'], default='held_out')
    parser.add_argument('--brand-terms', default='[]', help='Explicit JSON string array, never inferred from labels')
    args = parser.parse_args()
    try:
        data, _ = load_json(args.dataset); validate_dataset(data)
        brands = json.loads(args.brand_terms)
        rows = [row for row in data['queries'] if row['split'] == args.split]
        if not rows: raise ValueError('Selected query split is empty')
        print(json.dumps({'schema_version': 1, 'corpus_id': data['corpus_id'], 'run_id': 'experimental-fr-en-v1',
            'run_kind': 'rules', 'task': 'intent', 'split': args.split,
            'predictions': [{'id': row['id'], 'predicted_label': classify(row['query'], row['language'], brands)['label']} for row in rows]}, ensure_ascii=False))
    except (ValueError, TypeError, KeyError, OSError) as error: parser.exit(2, f'Invalid baseline input: {error}\n')


if __name__ == '__main__': main()
