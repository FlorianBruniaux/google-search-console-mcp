#!/usr/bin/env python3
"""Compare existing extraction profiles on a bounded, annotated local corpus.

No fetch, model invocation, threshold selection or default adoption. Provenance,
authorization, independent annotation and pre-tuning freeze are declarations.
"""
from collections import Counter
import argparse
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import platform
import re
import sys
import time
import tracemalloc
from urllib.parse import urlsplit

MAX_HTML_BYTES = 2_097_152
MAX_CORPUS_BYTES = 16_777_216
SPLITS = ('train', 'tuning', 'held_out')
PAGE_TYPES = ('article', 'product', 'local_service', 'forum', 'js_shell')


def require(value, message):
    if not value:
        raise ValueError(message)


def shape(value, keys):
    require(isinstance(value, dict) and set(value) == set(keys), 'Invalid object fields')


def nonempty(value):
    require(isinstance(value, str) and bool(value.strip()) and len(value) <= 10_000,
            'Expected nonempty string within 10000 characters')


def normalize(value):
    return ' '.join(value.casefold().split())


def unique_keys(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'Duplicate JSON key')
        result[key] = value
    return result


def read_bounded(path, limit):
    require(path.is_file(), 'Expected regular local file')
    with path.open('rb') as handle:
        raw = handle.read(limit + 1)
    require(len(raw) <= limit, 'Input byte budget exceeded')
    return raw


class SourceText(HTMLParser):
    """Text occurrence check, including script/style data, never a quality label."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []

    def handle_data(self, value):
        self.parts.append(value)


def load_dataset(path):
    raw = read_bounded(path, MAX_HTML_BYTES)
    data = json.loads(raw, object_pairs_hook=unique_keys,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Nonfinite JSON value')))
    shape(data, {'schema_version', 'corpus_id', 'provenance', 'protocol', 'cases'})
    require(type(data['schema_version']) is int and data['schema_version'] == 1, 'Unsupported schema')
    nonempty(data['corpus_id'])
    require(data['provenance'] in ('human', 'synthetic'), 'Unknown provenance')
    shape(data['protocol'], {'frozen_before_tuning', 'inclusion_criteria', 'omission_criteria', 'resource_criteria'})
    require(data['protocol']['frozen_before_tuning'] is True, 'Pre-tuning freeze declaration required')
    for key in ('inclusion_criteria', 'omission_criteria', 'resource_criteria'):
        nonempty(data['protocol'][key])
    require(isinstance(data['cases'], list) and 0 < len(data['cases']) <= 100, 'Expected 1 to 100 cases')
    identities, hashes, families, total_bytes, loaded = set(), set(), {}, 0, []
    for case in data['cases']:
        shape(case, {'id', 'split', 'task_family', 'site_family', 'page_family', 'language',
                     'page_type', 'source_url', 'html_path', 'html_sha256', 'annotation', 'include', 'omit'})
        for key in ('id', 'task_family', 'site_family', 'page_family', 'source_url', 'html_path'):
            nonempty(case[key])
        require(case['id'] not in identities, 'Duplicate case identity'); identities.add(case['id'])
        require(case['split'] in SPLITS, 'Unknown split')
        for key in ('task_family', 'site_family', 'page_family'):
            identity = (key, case[key])
            require(families.setdefault(identity, case['split']) == case['split'], 'Family crosses splits')
        require(case['language'] in ('fr', 'en') and case['page_type'] in PAGE_TYPES, 'Unknown language/page type')
        url = urlsplit(case['source_url'])
        require(url.scheme in ('http', 'https') and url.hostname and not url.username and not url.password,
                'Expected source HTTP(S) URL without credentials')
        shape(case['annotation'], {'annotator', 'reviewer', 'source_authorization', 'independent_of_extractors'})
        for key in ('annotator', 'reviewer', 'source_authorization'):
            nonempty(case['annotation'][key])
        require(normalize(case['annotation']['annotator']) != normalize(case['annotation']['reviewer']),
                'Independent annotation reviewer required')
        require(case['annotation']['independent_of_extractors'] is True, 'Independent annotation declaration required')
        relative = Path(case['html_path'])
        require(not relative.is_absolute() and '..' not in relative.parts, 'HTML path must remain inside corpus directory')
        source = (path.parent / relative).resolve()
        require(source.is_relative_to(path.parent), 'HTML path escapes corpus directory')
        html_bytes = read_bounded(source, MAX_HTML_BYTES)
        total_bytes += len(html_bytes)
        require(total_bytes <= MAX_CORPUS_BYTES, 'Corpus byte budget exceeded')
        digest = hashlib.sha256(html_bytes).hexdigest()
        require(isinstance(case['html_sha256'], str) and re.fullmatch('[0-9a-f]{64}', case['html_sha256'])
                and case['html_sha256'] == digest, 'HTML SHA256 mismatch')
        require(digest not in hashes, 'Duplicate HTML source'); hashes.add(digest)
        html = html_bytes.decode('utf-8', errors='strict')
        require(isinstance(case['include'], list) and isinstance(case['omit'], list)
                and len(case['include']) + len(case['omit']) <= 100, 'Expected at most 100 snippet labels')
        snippets = list(case['include'])
        for item in case['omit']:
            shape(item, {'text', 'kind'})
            require(item['kind'] in ('template', 'comment', 'other'), 'Unknown omission kind')
            snippets.append(item['text'])
        for snippet in snippets:
            nonempty(snippet)
        normalized = [normalize(s) for s in snippets]
        require(len(set(normalized)) == len(normalized), 'Duplicate/conflicting snippet annotation')
        require(not any(a in b or b in a for i, a in enumerate(normalized) for b in normalized[i + 1:]),
                'Overlapping snippet annotations')
        parser = SourceText(); parser.feed(html); parser.close()
        source_text = normalize(' '.join(parser.parts))
        require(all(s in source_text for s in normalized), 'Snippet absent from supplied source text')
        loaded.append((case, html, str(source), len(html_bytes)))
    return data, loaded, hashlib.sha256(raw).hexdigest()


def measure(html, url, profile, include, omit):
    from gsc_mcp.content_extraction import extract_html
    # One in-process observation: imports/cache/order affect cost; no RSS claim.
    tracemalloc.start()
    start = time.perf_counter()
    try:
        try:
            extraction = extract_html(html, url, profile)
        except Exception as error:
            extraction = {'status': 'extraction_failed', 'text': None, 'error_type': type(error).__name__}
        elapsed = time.perf_counter() - start
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    text = extraction.pop('text', None)
    result = {'extraction': extraction, 'wall_seconds': elapsed, 'python_allocation_peak_bytes': peak,
              'metrics': None, 'annotation_coverage': 'unavailable'}
    if extraction['status'] != 'extracted' or not isinstance(text, str) or not text.strip():
        return result
    text = normalize(text)
    included = [normalize(s) in text for s in include]
    omitted = [normalize(s['text']) in text for s in omit]
    kinds = {}
    for snippet, hit in zip(omit, omitted):
        count = kinds.setdefault(snippet['kind'], {'hits': 0, 'total': 0})
        count['hits'] += int(hit); count['total'] += 1
    result['metrics'] = {'included_hits': included, 'omitted_hits': omitted,
                         'inclusion_recall': sum(included) / len(included) if included else None,
                         'omission_leakage': sum(omitted) / len(omitted) if omitted else None,
                         'omission_by_kind': kinds}
    result['annotation_coverage'] = ('no_inclusion_labels' if not included else
                                     'complete_labeled_snippets' if all(included) else 'partial')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset', required=True, help='Manifest; relative HTML paths stay beneath its directory')
    parser.add_argument('--split', choices=SPLITS, default='held_out')
    args = parser.parse_args()
    try:
        path = Path(args.dataset).resolve()
        data, loaded, digest = load_dataset(path)
        selected = [row for row in loaded if row[0]['split'] == args.split]
        require(bool(selected), 'Empty selected split')
        from gsc_mcp.content_extraction import PROFILES
        rows = []
        for case, html, resolved, byte_count in selected:
            rows.append({'id': case['id'], 'source_url': case['source_url'], 'html_path': case['html_path'],
                         'resolved_html_path': resolved, 'html_sha256': case['html_sha256'], 'html_bytes': byte_count,
                         'profiles': {p: measure(html, case['source_url'], p, case['include'], case['omit']) for p in PROFILES}})
        report = {'schema_version': 1, 'corpus_id': data['corpus_id'], 'manifest_path': str(path),
                  'dataset_sha256': digest, 'annotation_provenance': data['provenance'],
                  'declarations_authenticated': False, 'declared_protocol': data['protocol'], 'split': args.split,
                  'coverage': {key: dict(Counter(row[0][key] for row in selected)) for key in ('language', 'page_type')},
                  'environment': {'python': platform.python_version(), 'platform': platform.platform()},
                  'cases': rows, 'release_quality': 'UNKNOWN', 'synthetic_release_eligible': False,
                  'downstream_warnings': 'not_measured',
                  'limitations': ['Snippet presence measures labeled coverage only, not whole-content recall or precision.',
                                  'One observation per profile in fixed order; imports and caches affect wall time.',
                                  'tracemalloc peak bytes covers traced Python allocations during extraction, not RSS or native allocations.',
                                  'No approved numeric thresholds or adoption decision is implemented.']}
        output = json.dumps(report, ensure_ascii=False, allow_nan=False)
        require(len(output.encode('utf-8')) <= MAX_HTML_BYTES, 'Report byte budget exceeded')
        print(output)
    except (ValueError, TypeError, KeyError, OSError, RecursionError) as error:
        parser.exit(2, f'Invalid evaluation input: {type(error).__name__}: {error}\n')


if __name__ == '__main__':
    main()
