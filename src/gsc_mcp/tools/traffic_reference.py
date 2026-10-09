"""One bounded weekly reference using existing descriptive Google observations."""
from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from gsc_mcp.meta import with_meta
from gsc_mcp.tools.search_breakdown import _date, _integer, search_change_breakdown


def search_weekday_reference(
    site: str,
    days: int = 28,
    end_date: str | None = None,
    dimensions: list[str] | None = None,
    filters: list[dict] | None = None,
    search_type: str = 'web',
    aggregation_type: str = 'auto',
    row_limit: int = 1000,
    max_requests: int = 20,
    limit: int = 50,
) -> str:
    """Describe the newest eligible window against a prior same-weekday window.

    End defaults to the current Pacific date minus three reporting-lag days.
    Explicit ends must respect that bound. Equal windows are shifted by the
    smallest multiple of seven that prevents overlap. Final data is requested;
    a reporting lag does not guarantee complete finalized observations.
    Missing date coverage or aggregate counts make the reference unavailable.
    The child report remains intact and has one bounded execution, with no
    retries or additional historical probes. Signed count deltas are descriptive.
    """
    params = dict(site=site, days=days, end_date=end_date, dimensions=deepcopy(dimensions),
                  filters=deepcopy(filters), search_type=search_type,
                  aggregation_type=aggregation_type, row_limit=row_limit,
                  max_requests=max_requests, limit=limit)
    _integer(days, 'days', 1, 366)
    timezone = 'America/Los_Angeles'
    eligible_end = datetime.now(ZoneInfo(timezone)).date() - timedelta(days=3)
    end = eligible_end if end_date is None else _date(end_date)
    if end > eligible_end:
        raise ValueError('end_date must respect the three-day Pacific reporting lag')
    shift_days = ((days + 6) // 7) * 7
    try:
        start = end - timedelta(days=days - 1)
        baseline_end = end - timedelta(days=shift_days)
        baseline_start = start - timedelta(days=shift_days)
    except OverflowError as exc:
        raise ValueError('Reference window exceeds supported date bounds') from exc
    windows = {'baseline': {'start': baseline_start.isoformat(), 'end': baseline_end.isoformat()},
               'comparison': {'start': start.isoformat(), 'end': end.isoformat()}}
    result = json.loads(search_change_breakdown(
        site=site, baseline_start=windows['baseline']['start'], baseline_end=windows['baseline']['end'],
        comparison_start=windows['comparison']['start'], comparison_end=windows['comparison']['end'],
        dimensions=dimensions, filters=filters, search_type=search_type, data_state='final',
        aggregation_type=aggregation_type, row_limit=row_limit, max_requests=max_requests, limit=limit))
    reasons = []
    if (result['site'] != site or result['engine'] != 'google' or result['search_type'] != search_type
            or result['data_state'] != 'final' or result['aggregation_type'] != aggregation_type
            or result['filters'] != ([] if filters is None else filters)):
        reasons.append('source_options_mismatch')
    for name, window in windows.items():
        period = result['periods'][name]
        if (period['requested_start'] != window['start'] or period['requested_end'] != window['end']
                or period['requested_days'] != days):
            reasons.append(f'{name}_window_mismatch')
        if period['timezone'] != timezone:
            reasons.append(f'{name}_timezone_mismatch')
        if period['coverage_probe_status'] != 'observed':
            reasons.append(f'{name}_date_probe_unavailable')
        if period['observed_day_count'] != days or period['missing_requested_dates'] != []:
            reasons.append(f'{name}_date_coverage_incomplete')
        if period['anomalies']:
            reasons.append(f'{name}_date_probe_anomaly')
        if period['incompleteness_status'] != 'final_requested':
            reasons.append(f'{name}_finality_unconfirmed')
        aggregate = result['baseline_totals'][name]
        if aggregate['availability'] != 'observed':
            reasons.append(f'{name}_aggregate_unavailable')
        if any(aggregate['metrics'][metric] is None for metric in ('clicks', 'impressions')):
            reasons.append(f'{name}_counts_unavailable')
    if not result['baseline_comparison']['comparable']:
        reasons.append('aggregate_comparison_unavailable')
    upstream_meta = result.pop('_meta')
    result['weekday_reference'] = {
        'method': 'prior_disjoint_same_weekdays', 'status': 'unavailable' if reasons else 'observed',
        'reasons': reasons, 'shift_days': shift_days, 'effective_windows': windows,
        'eligible_end': eligible_end.isoformat(), 'report_lag_days': 3, 'timezone': timezone,
        'delta': None if reasons else {metric: result['baseline_delta'][metric]
                                      for metric in ('clicks', 'impressions')},
        'causal_interpretation': False, 'upstream_meta': upstream_meta,
    }
    return json.dumps(with_meta(result, 'search_weekday_reference', params,
                                sources=upstream_meta.get('sources')), allow_nan=False)
