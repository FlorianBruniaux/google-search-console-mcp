"""Bounded, descriptive Google period comparisons. Contributions are not causes."""
from __future__ import annotations

import json
import math
import re
from copy import deepcopy
from datetime import date, timedelta
from typing import Optional

from gsc_mcp.auth import get_searchconsole_service
from gsc_mcp.meta import with_meta

_DIMENSIONS = ('page', 'query', 'country', 'device')
_METRICS = ('clicks', 'impressions', 'ctr', 'position')
_COUNTS = ('clicks', 'impressions')


def _date(value: str) -> date:
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        raise ValueError('Dates must use YYYY-MM-DD')
    return date.fromisoformat(value)


def _integer(value: int, name: str, low: int, high: int) -> None:
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f'{name} must be an integer in {low}..{high}')


def _finite(value):
    if type(value) not in (int, float):
        return None
    try:
        return value if math.isfinite(value) else None
    except OverflowError:
        return None


def _number(value):
    value = _finite(value)
    return value if value is not None and value >= 0 else None


def _metrics(row: dict | None) -> dict:
    row = row or {}
    clicks, impressions = (_number(row.get(k)) for k in _COUNTS)
    position = _number(row.get('position')) if impressions is not None and impressions > 0 else None
    metrics = {'clicks': clicks, 'impressions': impressions,
            'ctr': _finite(clicks / impressions) if clicks is not None and impressions is not None and impressions > 0 else None,
            'position': position}
    reasons = {}
    for key in _METRICS:
        if metrics[key] is not None:
            continue
        if key == 'ctr':
            reasons[key] = 'missing_counts_or_nonpositive_impressions' if clicks is None or impressions is None or impressions <= 0 else 'nonfinite_calculation'
        elif key not in row:
            reasons[key] = 'missing_provider_value'
        elif _number(row[key]) is None:
            reasons[key] = 'invalid_provider_value'
        else:
            reasons[key] = 'nonpositive_or_missing_impressions'
    return {**metrics, 'unavailable_metrics': reasons}


def _difference(before: dict, after: dict, comparable: bool, keys=_METRICS) -> dict:
    return {('ctr_percentage_points' if k == 'ctr' else k):
            (_finite((after[k] - before[k]) * (100 if k == 'ctr' else 1))
             if comparable and before.get(k) is not None and after.get(k) is not None else None)
            for k in keys}


def _sum(rows: list[dict], keys=_COUNTS) -> dict:
    # Empty source sets remain unknown; no zero filling of censored observations.
    return {k: _finite(sum(r[k] for r in rows)) if rows and all(r.get(k) is not None for r in rows) else None
            for k in keys}


def _aggregation_reason(*values) -> str | None:
    if any(v not in ('byProperty', 'byPage') for v in values):
        return 'aggregation_unknown'
    if len(set(values)) != 1:
        return 'aggregation_mismatch'
    return None


def _coverage() -> dict:
    return {'rows_returned': 0, 'pages_fetched': 0, 'response_aggregation_type': None,
            'response_aggregation_types': [], 'api_pagination_exhausted': False,
            'row_limit_reached': False, 'request_cap_reached': False, 'fetch_error': None,
            'anomalies': [], 'all_source_rows_guaranteed': False}


def search_change_breakdown(
    site: str,
    baseline_start: str,
    baseline_end: str,
    comparison_start: str,
    comparison_end: str,
    dimensions: list[str] | None = None,
    filters: Optional[list[dict]] = None,
    search_type: str = 'web',
    data_state: str = 'final',
    aggregation_type: str = 'auto',
    row_limit: int = 1000,
    max_requests: int = 20,
    limit: int = 50,
) -> str:
    """Compare equal explicit Google windows using independent bounded segment views.

    Missing rows/metrics remain unknown. CTR uses counts; position is the provider
    row average, never averaged across segments. Deltas describe observations, not
    causality. All calls use identical filters/source options. Requests have one
    attempt each, with no whole-report retries or hidden pagination probes.
    """
    params = dict(site=site, baseline_start=baseline_start, baseline_end=baseline_end,
                  comparison_start=comparison_start, comparison_end=comparison_end,
                  dimensions=deepcopy(dimensions), filters=deepcopy(filters), search_type=search_type,
                  data_state=data_state, aggregation_type=aggregation_type, row_limit=row_limit,
                  max_requests=max_requests, limit=limit)
    starts = [_date(baseline_start), _date(comparison_start)]
    ends = [_date(baseline_end), _date(comparison_end)]
    days = [(end - start).days + 1 for start, end in zip(starts, ends)]
    if days[0] <= 0 or days[0] != days[1] or ends[0] >= starts[1] or days[0] > 25000:
        raise ValueError('Windows must be ordered, disjoint, equal length, and 1..25000 days')
    dims = list(_DIMENSIONS) if dimensions is None else dimensions
    if (not isinstance(dims, list) or not dims or any(not isinstance(d, str) or d not in _DIMENSIONS for d in dims)
            or len(dims) != len(set(dims))):
        raise ValueError('dimensions must be unique page/query/country/device values')
    if search_type not in ('web', 'image', 'video', 'news'):
        raise ValueError('Unsupported search_type')
    if data_state not in ('final', 'all') or aggregation_type not in ('auto', 'byProperty', 'byPage'):
        raise ValueError('Unsupported data_state or aggregation_type')
    actual_filters = [] if filters is None else deepcopy(filters)
    if not isinstance(actual_filters, list):
        raise ValueError('filters must be a list')
    for f in actual_filters:
        if (not isinstance(f, dict) or set(f) != {'dimension', 'operator', 'expression'}
                or f['dimension'] not in (*_DIMENSIONS, 'searchAppearance')
                or f['operator'] not in ('equals', 'notEquals', 'contains', 'notContains', 'includingRegex', 'excludingRegex')
                or not isinstance(f['expression'], str)):
            raise ValueError('Invalid dimension/operator/expression filter')
    if aggregation_type != 'auto' and ('page' in dims or any(f['dimension'] == 'page' for f in actual_filters)):
        raise ValueError('Page grouping/filtering requires auto aggregation')
    _integer(row_limit, 'row_limit', 1, 100000)
    _integer(limit, 'limit', 1, 1000)
    _integer(max_requests, 'max_requests', 4 + 2 * len(dims), 100)
    service = get_searchconsole_service()
    requests_made = 0
    common = {'type': search_type, 'dataState': data_state, 'aggregationType': aggregation_type}
    if actual_filters:
        common['dimensionFilterGroups'] = [{'groupType': 'and', 'filters': actual_filters}]
    names = ('baseline', 'comparison')
    windows = {name: {'startDate': start.isoformat(), 'endDate': end.isoformat()}
               for name, start, end in zip(names, starts, ends)}

    def fetch(name, grouping, row_count, offset=0):
        nonlocal requests_made
        body = {**deepcopy(common), **windows[name], 'rowLimit': row_count, 'startRow': offset}
        if grouping:
            body['dimensions'] = [grouping]
        requests_made += 1
        try:
            response = service.searchanalytics().query(siteUrl=site, body=body).execute()
            if not isinstance(response, dict) or not isinstance(response.get('rows', []), list):
                raise ValueError('Malformed provider response')
            return response, None
        except Exception as exc:
            # Expose type only: provider messages may contain credentials/URLs.
            return None, type(exc).__name__

    totals, periods = {}, {}
    for name in names:
        answer, error = fetch(name, None, 1)
        rows = (answer or {}).get('rows', [])
        valid = len(rows) == 1 and isinstance(rows[0], dict)
        totals[name] = {'metrics': _metrics(rows[0] if valid else None),
                        'availability': 'unavailable' if error or (rows and not valid) else ('observed' if valid else 'empty'),
                        'anomalies': ['invalid_aggregate_rows'] if rows and not valid else [],
                        'response_aggregation_type': (answer or {}).get('responseAggregationType'),
                        'fetch_error': error}
    for name, start, end in zip(names, starts, ends):
        answer, error = fetch(name, 'date', days[0])
        dates = set()
        anomalies = []
        for r in (answer or {}).get('rows', []):
            key = r.get('keys') if isinstance(r, dict) else None
            if not isinstance(key, list) or len(key) != 1:
                anomalies.append('invalid_date_key')
                continue
            try:
                observed = _date(key[0])
            except (ValueError, TypeError):
                anomalies.append('invalid_date_key')
                continue
            if not start <= observed <= end:
                anomalies.append('date_outside_window')
            elif key[0] in dates:
                anomalies.append('duplicate_date')
            else:
                dates.add(key[0])
        dates = sorted(dates)
        metadata = (answer or {}).get('metadata', {})
        marker = metadata.get('first_incomplete_date') if isinstance(metadata, dict) else None
        if marker is not None:
            try:
                _date(marker)
            except (ValueError, TypeError):
                marker = None
                anomalies.append('invalid_incomplete_date')
        date_set = set(dates)
        requested = [(start + timedelta(days=i)).isoformat() for i in range(days[0])]
        periods[name] = {'requested_start': start.isoformat(), 'requested_end': end.isoformat(),
                         'requested_days': days[0], 'timezone': 'America/Los_Angeles',
                         'observed_dates': dates if not error else None,
                         'observed_start': dates[0] if dates else None,
                         'observed_end': dates[-1] if dates else None,
                         'observed_day_count': len(dates) if not error else None,
                         'missing_requested_dates': [d for d in requested if d not in date_set] if not error else None,
                         'first_incomplete_date': marker,
                         'incompleteness_status': ('unknown' if error or anomalies else
                                                   'incomplete' if marker else
                                                   'final_requested' if data_state == 'final' else 'no_marker_returned'),
                         'coverage_probe_status': 'unavailable' if error else 'observed',
                         'response_aggregation_type': (answer or {}).get('responseAggregationType'),
                         'fetch_error': error, 'anomalies': sorted(set(anomalies)),
                         'all_source_rows_guaranteed': False}

    streams = {(dim, name): {'rows': {}, 'coverage': _coverage(), 'active': True}
               for dim in dims for name in names}
    # First round funds every independent view before any pagination consumes the remainder.
    while any(s['active'] for s in streams.values()) and requests_made < max_requests:
        for (dim, name), stream in streams.items():
            if not stream['active'] or requests_made >= max_requests:
                continue
            coverage = stream['coverage']
            allowance = min(25000, row_limit - coverage['rows_returned'])
            answer, error = fetch(name, dim, allowance, coverage['rows_returned'])
            if error:
                coverage['fetch_error'] = error
                stream['active'] = False
                continue
            coverage['pages_fetched'] += 1
            agg = answer.get('responseAggregationType')
            coverage['response_aggregation_types'].append(agg)
            coverage['response_aggregation_type'] = agg
            if agg is not None and agg not in ('byProperty', 'byPage', 'auto'):
                coverage['anomalies'].append('invalid_aggregation')
            if any(value != coverage['response_aggregation_types'][0] for value in coverage['response_aggregation_types']):
                coverage['anomalies'].append('aggregation_changed')
            page = answer.get('rows', [])
            if len(page) > allowance:
                coverage['anomalies'].append('provider_row_limit_exceeded')
            coverage['rows_returned'] += len(page)
            for r in page[:allowance]:
                keys = r.get('keys') if isinstance(r, dict) else None
                if not isinstance(keys, list) or len(keys) != 1 or not isinstance(keys[0], str):
                    coverage['anomalies'].append('invalid_row_key')
                elif keys[0] in stream['rows']:
                    coverage['anomalies'].append('duplicate_key')
                else:
                    stream['rows'][keys[0]] = _metrics(r)
            coverage['api_pagination_exhausted'] = len(page) < allowance
            coverage['row_limit_reached'] = coverage['rows_returned'] >= row_limit
            stream['active'] = not (coverage['api_pagination_exhausted'] or coverage['row_limit_reached'] or coverage['anomalies'])
    for stream in streams.values():
        coverage = stream['coverage']
        coverage['request_cap_reached'] = stream['active'] and requests_made >= max_requests
        coverage['anomalies'] = sorted(set(coverage['anomalies']))

    total_reason = _aggregation_reason(*(totals[n]['response_aggregation_type'] for n in names))
    if any(totals[n]['anomalies'] for n in names):
        total_reason = 'source_anomaly'
    if any(totals[n]['fetch_error'] for n in names):
        total_reason = 'fetch_error'
    baseline_delta = _difference(totals['baseline']['metrics'], totals['comparison']['metrics'], total_reason is None)
    breakdowns = {}
    for dim in dims:
        before, after = (streams[dim, n]['rows'] for n in names)
        coverage = {n: streams[dim, n]['coverage'] for n in names}
        pair_reason = _aggregation_reason(*(coverage[n]['response_aggregation_type'] for n in names))
        if any(coverage[n]['anomalies'] for n in names):
            pair_reason = 'source_anomaly'
        matched = [{'key': key, 'baseline': before[key], 'comparison': after[key],
                    'delta': _difference(before[key], after[key], pair_reason is None)}
                   for key in before.keys() & after.keys()]
        matched.sort(key=lambda r: (r['delta']['clicks'] is None,
                                   -abs(r['delta']['clicks']) if r['delta']['clicks'] is not None else 0, r['key']))
        baseline_only = [{'key': key, 'baseline': before[key], 'comparison': None, 'delta': None}
                         for key in sorted(before.keys() - after.keys())]
        comparison_only = [{'key': key, 'baseline': None, 'comparison': after[key], 'delta': None}
                           for key in sorted(after.keys() - before.keys())]
        observed_sums = {n: _sum(list(streams[dim, n]['rows'].values())) for n in names}
        matched_delta = _sum([r['delta'] for r in matched])
        reason = pair_reason or total_reason or _aggregation_reason(
            *(coverage[n]['response_aggregation_type'] for n in names),
            *(totals[n]['response_aggregation_type'] for n in names))
        if any(coverage[n]['fetch_error'] for n in names):
            reason = 'fetch_error'
        reconciliation = {'comparable': reason is None, 'reason': reason,
                          'scope': 'retrieved rows only; residuals are descriptive, not causes'}
        for n in names:
            reconciliation[f'{n}_residual'] = _difference(observed_sums[n], totals[n]['metrics'], reason is None, _COUNTS)
        reconciliation['total_delta_minus_matched_delta'] = _difference(matched_delta, baseline_delta, reason is None, _COUNTS)
        reconciliation['overcoverage'] = any(v is not None and v < 0 for n in names
                                              for v in reconciliation[f'{n}_residual'].values())
        sections = {'matched': matched, 'baseline_only': baseline_only, 'comparison_only': comparison_only}
        breakdowns[dim] = {**{section: rows[:limit] for section, rows in sections.items()},
                           **{f'{section}_count': len(rows) for section, rows in sections.items()},
                           'displayed_counts': {section: min(limit, len(rows)) for section, rows in sections.items()},
                           'display_truncated': any(len(rows) > limit for rows in sections.values()),
                           'baseline_coverage': coverage['baseline'], 'comparison_coverage': coverage['comparison'],
                           'observed_sums': observed_sums, 'matched_delta': matched_delta,
                           'comparison': {'comparable': pair_reason is None, 'reason': pair_reason,
                                          'scope': 'observed matched rows; equal requested windows do not prove complete equal coverage'},
                           'reconciliation': reconciliation}
    result = {'site': site, 'engine': 'google', 'search_type': search_type, 'data_state': data_state,
              'filters': actual_filters, 'aggregation_type': aggregation_type, 'periods': periods,
              'baseline_totals': totals, 'baseline_delta': baseline_delta,
              'baseline_comparison': {'comparable': total_reason is None, 'reason': total_reason,
                                      'scope': 'reported aggregates; observed date coverage may differ'},
              'breakdowns': breakdowns,
              'position_method': 'provider_row_average; no averaging across rows',
              'request_budget': {'max_requests': max_requests, 'requests_made': requests_made,
                                 'exhausted': requests_made >= max_requests},
              'limitations': ['Google returns top rows, not guaranteed complete source data.',
                              'Absent rows and omitted dates are unknown, not observed zero.',
                              'Separate dimension reports describe the same traffic and cannot be added together.',
                              'Observed contributors and residuals do not establish causes.',
                              'Finalized records were requested, not complete coverage, when data_state=final.',
                              'Values requested with data_state=all can change as unfinished data is finalized.']}
    return json.dumps(with_meta(result, 'search_change_breakdown', params,
                                sources={'google': {'site': site}}), allow_nan=False)
