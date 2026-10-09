"""Evidence-first search pilot; identities and byte bounds are local contracts."""
from __future__ import annotations

import json
from collections import Counter
from copy import deepcopy
from hashlib import sha256

from gsc_mcp.meta import with_meta

_RULE_VERSION = 'search_change_breakdown.observed_segment.v2'
_SECTIONS = ('matched', 'baseline_only', 'comparison_only')


def _json(value: dict) -> str:
    return json.dumps(value, ensure_ascii=False, allow_nan=False)


def _identity(value: dict) -> str:
    canonical = json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(',', ':'))
    return sha256(canonical.encode('utf-8')).hexdigest()


def _pointer(value: str) -> str:
    return value.replace('~', '~0').replace('/', '~1')


def _references(row: dict, pointer: str) -> dict[str, list[str]]:
    references: dict[str, list[str]] = {'facts': [], 'calculations': [], 'unavailable': []}
    for period in ('baseline', 'comparison'):
        if row[period] is None:
            references['unavailable'].append(pointer + '/' + period)
            continue
        for metric in ('clicks', 'impressions', 'position', 'ctr'):
            kind = ('unavailable' if row[period][metric] is None else
                    'calculations' if metric == 'ctr' else 'facts')
            references[kind].append(f'{pointer}/{period}/{metric}')
    if row['delta'] is None:
        references['unavailable'].append(pointer + '/delta')
    else:
        for metric, value in row['delta'].items():
            kind = 'unavailable' if value is None else 'calculations'
            references[kind].append(f'{pointer}/delta/{metric}')
    return references


def search_report_contract(report: dict, observations: dict) -> dict:
    """Describe displayed findings; hash all retrieved sanitized observations."""
    findings = []
    source_identity = {key: report[key] for key in
                       ('engine', 'search_type', 'data_state', 'aggregation_type')}
    # The single filter group is AND; order does not change its semantic scope.
    source_identity['filters'] = sorted(report['filters'], key=lambda f: json.dumps(f, sort_keys=True))
    for dimension, breakdown in report['breakdowns'].items():
        for section in _SECTIONS:
            for index, row in enumerate(breakdown[section]):
                target = {'dimension': dimension, 'key': row['key']}
                identity = {'property': report['site'], 'target': target, 'rule_version': _RULE_VERSION,
                            'source': source_identity}
                pointer = f'/breakdowns/{_pointer(dimension)}/{section}/{index}'
                findings.append({'finding_id': 'finding:' + _identity(identity), 'target': target,
                                 **_references(row, pointer), 'hypotheses': [], 'kind': 'observation',
                                 'method_version': _RULE_VERSION, 'source_ref': '/report_contract/scope',
                                 'fix_candidates': [],
                                 'missing_criteria': ['cause_not_identified', 'business_context_not_reviewed'],
                                 'verification_step': 'Review referenced source values, coverage and intent before proposing any change.'})
    return {'version': 1, 'rule_version': _RULE_VERSION,
            'snapshot_id': 'snapshot:' + _identity({'report': report, 'observations': observations}),
            'scope': {'property': report['site'], 'periods': deepcopy(report['periods']),
                      'source': {key: deepcopy(report[key]) for key in
                                 ('engine', 'search_type', 'data_state', 'filters', 'aggregation_type')},
                      'finding_selection': 'displayed retrieved rows under the existing per-section limit'},
            'findings': findings,
            'verification': {'causal_effect': 'not_identified', 'complete_source_coverage': 'not_guaranteed',
                             'probabilistic_precision': 'unavailable'}}


class ResponseBudgetExceeded(ValueError):
    """Even the explicit omission envelope cannot fit; never return partial JSON."""

    def __init__(self, max_bytes: int, full_response_bytes: int, minimum_response: dict) -> None:
        self.max_bytes = max_bytes
        self.full_response_bytes = full_response_bytes
        self.minimum_response = deepcopy(minimum_response)
        self.minimum_response_bytes = len(_json(minimum_response).encode('utf-8'))
        errors = {'totals': {period: entry['fetch_error'] for period, entry in minimum_response['baseline_totals'].items()},
                  'periods': {period: entry['fetch_error'] for period, entry in minimum_response['periods'].items()},
                  'breakdowns': {dimension: {period: entry[period + '_coverage']['fetch_error']
                                           for period in ('baseline', 'comparison')}
                                 for dimension, entry in minimum_response['breakdowns'].items()}}
        super().__init__(f'RESPONSE_BUDGET_EXCEEDED: max_bytes={max_bytes}, full_response_bytes={full_response_bytes}, '
                         f'minimum_response_bytes={self.minimum_response_bytes}; '
                         f'no JSON envelope returned; source_errors={_json(errors)}')


def _accounted_envelope(report: dict, params: dict) -> tuple[dict, str]:
    envelope = with_meta(report, 'search_change_breakdown', params, sources={'google': {'site': report['site']}})
    # Only the decimal byte count changes; iterate until its own width is accounted for.
    while True:
        serialized = _json(envelope)
        byte_count = len(serialized.encode('utf-8'))
        if envelope['response_budget']['serialized_bytes'] == byte_count:
            return envelope, serialized
        envelope['response_budget']['serialized_bytes'] = byte_count


def _omit_rows(report: dict) -> dict:
    minimum = deepcopy(report)
    budget = minimum['response_budget']
    budget['status'] = 'exceeded'
    budget['omitted_rows'] = {}
    budget['omitted_unavailable_metrics'] = {}
    for dimension, breakdown in minimum['breakdowns'].items():
        budget['omitted_rows'][dimension] = {}
        reasons = Counter()
        for section in _SECTIONS:
            rows = breakdown[section]
            budget['omitted_rows'][dimension][section] = len(rows)
            for row in rows:
                for period in ('baseline', 'comparison'):
                    metrics = row[period]
                    if metrics is None:
                        reasons[f'{period}:unobserved_period'] += 1
                    else:
                        reasons.update(f'{period}:{metric}:{reason}' for metric, reason in metrics['unavailable_metrics'].items())
                if row['delta'] is None or any(value is None for value in row['delta'].values()):
                    reasons['delta:unavailable'] += 1
            breakdown[section] = []
            breakdown['displayed_counts'][section] = 0
        budget['omitted_unavailable_metrics'][dimension] = dict(sorted(reasons.items()))
        breakdown['display_truncated'] = breakdown['display_truncated'] or any(budget['omitted_rows'][dimension].values())
    budget['omitted_findings'] = len(minimum['report_contract']['findings'])
    minimum['report_contract']['findings'] = []
    minimum['error'] = {'code': 'RESPONSE_BUDGET_EXCEEDED',
                        'message': 'Complete report exceeds output_max_bytes; displayed rows and finding records omitted with counts. '
                                   'No detail retrieval or stored snapshot is available.'}
    return minimum


def serialize_search_report(report: dict, params: dict, observations: dict, max_bytes: int | None = None) -> str:
    """Return the full report or a counted omission envelope; never mutate inputs."""
    if max_bytes is not None and (type(max_bytes) is not int or max_bytes <= 0):
        raise ValueError('output_max_bytes must be a positive integer or None')
    result = deepcopy(report)
    result['report_contract'] = search_report_contract(report, observations)
    if max_bytes is None:
        return _json(with_meta(result, 'search_change_breakdown', params, sources={'google': {'site': report['site']}}))
    result['response_budget'] = {'max_bytes': max_bytes, 'serialized_bytes': 0, 'status': 'within_budget'}
    _, serialized = _accounted_envelope(result, params)
    full_bytes = len(serialized.encode('utf-8'))
    if full_bytes <= max_bytes:
        return serialized
    result['response_budget']['full_response_bytes'] = full_bytes
    minimum, serialized = _accounted_envelope(_omit_rows(result), params)
    if len(serialized.encode('utf-8')) > max_bytes:
        raise ResponseBudgetExceeded(max_bytes, full_bytes, minimum)
    return serialized
