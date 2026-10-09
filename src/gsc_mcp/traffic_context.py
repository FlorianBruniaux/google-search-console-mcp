"""Calendar, robust descriptive arithmetic and caller-declared context. No I/O."""
from __future__ import annotations

from datetime import date, datetime, timedelta
import json
import math
from statistics import median
from urllib.parse import urlsplit

from gsc_mcp.tools.search_breakdown import _date, _metrics


def annual_window(end: date, days: int) -> tuple[date, date, dict]:
    clamped = end.month == 2 and end.day == 29
    prior_end = end.replace(year=end.year - 1, day=28 if clamped else end.day)
    prior_start = prior_end - timedelta(days=days - 1)
    start = end - timedelta(days=days - 1)
    if prior_end >= start:
        raise ValueError('Annual reference must remain disjoint from comparison')
    return prior_start, prior_end, {'calendar_anchor': 'prior_year_end',
        'leap_day_clamped': clamped, 'weekday_aligned': prior_end.weekday() == end.weekday()}


def context_preflight(raw: str | None, site: str, now: datetime,
                      windows: dict) -> dict:
    result = {'version': 1, 'collection_registry_status': 'unavailable',
              'collection_health': 'unknown', 'authority_verification': 'not_performed',
              'records': [], 'causal_interpretation': False}
    if raw is None:
        return result
    if not isinstance(raw, str) or len(raw.encode('utf-8')) > 32768:
        raise ValueError('context_json must be a JSON string within 32768 bytes')
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('Duplicate context key')
            result[key] = value
        return result

    def invalid_constant(value):
        raise ValueError('Nonfinite context value')

    try:
        document = json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid_constant)
    except (ValueError, TypeError) as exc:
        raise ValueError('Invalid context JSON') from exc
    if (not isinstance(document, dict) or type(document.get('version')) is not int or document.get('version') != 1
            or document.get('site') != site
            or set(document) - {'version', 'site', 'retrieved_at', 'collection_incidents', 'business_events'}):
        raise ValueError('Context needs version=1 and the exact source property')
    retrieved = document.get('retrieved_at')
    try:
        stamp = datetime.fromisoformat(retrieved.replace('Z', '+00:00'))
        if stamp.utcoffset() is None or stamp > now:
            raise ValueError()
    except (AttributeError, TypeError, ValueError) as exc:
        raise ValueError('Context retrieval time must be a past timezone-aware ISO timestamp') from exc
    result['retrieved_at'] = retrieved
    result['collection_registry_status'] = ('stale_caller_declared'
        if now - stamp > timedelta(days=7) else 'caller_declared_unverified')
    result['stale_after_days'] = 7
    for family in ('collection_incidents', 'business_events'):
        records = document.get(family, [])
        if not isinstance(records, list) or len(records) > 50:
            raise ValueError('Context record family must contain at most 50 records')
        for record in records:
            required = {'id', 'start', 'end', 'uncertainty'} | (
                {'provider', 'report_type', 'source_url'} if family == 'collection_incidents' else {'kind'})
            if (not isinstance(record, dict) or set(record) != required
                    or any(not isinstance(value, str) or not value or len(value) > 512 for value in record.values())):
                raise ValueError('Context record fields do not match the versioned schema')
            start, end = _date(record['start']), _date(record['end'])
            if end < start:
                raise ValueError('Context dates must be ordered')
            if family == 'collection_incidents':
                try:
                    parsed = urlsplit(record['source_url'])
                    if (parsed.scheme not in ('http', 'https') or not parsed.hostname
                            or parsed.username or parsed.password or parsed.query or parsed.fragment):
                        raise ValueError()
                    parsed.port
                except ValueError as exc:
                    raise ValueError('Context source must be an HTTP URL without credentials or query') from exc
            overlap = any(start <= _date(window['end']) and end >= _date(window['start'])
                          for window in windows.values())
            result['records'].append({**record, 'family': family, 'origin': 'caller_declared',
                'date_overlap': overlap, 'relevance': 'unverified', 'causal_interpretation': False})
    return result


def robust_reference(answer: dict | None, error: str | None, start: date, end: date,
                     comparison_start: date, comparison_end: date,
                     comparison_totals: dict, min_support: int) -> dict:
    reasons = []
    valid = {}
    if error:
        reasons.append('history_fetch_error')
    answer = answer or {}
    for row in answer.get('rows', []):
        try:
            keys = row['keys']
            if not isinstance(keys, list) or len(keys) != 1:
                raise ValueError()
            day = _date(keys[0])
            if not start <= day <= end or keys[0] in valid:
                raise ValueError()
            valid[keys[0]] = _metrics(row)
        except (KeyError, TypeError, ValueError):
            reasons.append('invalid_or_duplicate_history_date')
    metadata = answer.get('metadata', {})
    if not isinstance(metadata, dict) or metadata.get('first_incomplete_date'):
        reasons.append('history_finality_unconfirmed')
    if (answer.get('responseAggregationType') not in ('byProperty', 'byPage')
            or answer.get('responseAggregationType') != comparison_totals['response_aggregation_type']):
        reasons.append('history_aggregation_mismatch')
    support, expected = {}, {'clicks': 0, 'impressions': 0}
    for weekday in range(7):
        support[str(weekday)] = {}
        occurrences = sum((comparison_start + timedelta(days=i)).weekday() == weekday
                          for i in range((comparison_end - comparison_start).days + 1))
        for metric in expected:
            values = [metrics[metric] for day, metrics in valid.items()
                      if _date(day).weekday() == weekday and metrics[metric] is not None]
            center = median(values) if values else None
            support[str(weekday)][metric] = {'days': len(values), 'median': center,
                'median_absolute_deviation': median(abs(value-center) for value in values) if values else None}
            if occurrences and len(values) < min_support:
                reasons.append('insufficient_weekday_history')
            if occurrences and center is not None:
                expected[metric] += center * occurrences
    if any(comparison_totals['metrics'][metric] is None for metric in expected):
        reasons.append('comparison_counts_unavailable')
    if any(not math.isfinite(value) for value in expected.values()):
        reasons.append('nonfinite_reference_calculation')
    delta = None if reasons else {metric: comparison_totals['metrics'][metric] - value
                                  for metric, value in expected.items()}
    requested = [(start + timedelta(days=i)).isoformat() for i in range((end-start).days+1)]
    return {'method': 'sum_of_prior_same_weekday_daily_medians.v1',
            'status': 'unavailable' if reasons else 'observed', 'reasons': sorted(set(reasons)),
            'requested_window': {'start': start.isoformat(), 'end': end.isoformat()},
            'observed_dates': sorted(valid), 'omitted_dates': [day for day in requested if day not in valid],
            'omitted_days': len(requested) - len(valid), 'minimum_support_per_weekday': min_support,
            'support_by_weekday': support, 'expected_counts': None if reasons else expected,
            'delta': delta, 'timezone': 'America/Los_Angeles', 'data_state': 'final',
            'fetch_error': error, 'causal_interpretation': False,
            'formula': 'For each comparison weekday, multiply its occurrences by the median of observed prior counts; sum weekdays. No zero-filled missing days.'}
