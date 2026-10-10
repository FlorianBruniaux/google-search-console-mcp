"""One bounded weekly reference using existing descriptive Google observations."""
from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from gsc_mcp.auth import get_searchconsole_service
from gsc_mcp.audit_runtime import execute_google
from gsc_mcp.meta import with_meta
from gsc_mcp.traffic_context import annual_window, context_preflight, robust_reference
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
    reference_strategy: str = 'weekday',
    history_days: int = 56,
    min_support: int = 6,
    context_json: str | None = None,
) -> str:
    """Describe eligible traffic against weekday, annual or robust daily references.

    End defaults to the current Pacific date minus three reporting-lag days.
    Explicit ends must respect that bound. Equal windows are shifted by the
    smallest multiple of seven that prevents overlap. Final data is requested;
    a reporting lag does not guarantee complete finalized observations.
    Missing date coverage or aggregate counts make the reference unavailable.
    The child report remains intact and has one bounded execution, with no
    retries. The default retains the previous weekday contract. Optional annual
    alignment discloses leap-day clamping and weekday mismatch. Rolling history
    uses one extra bounded date query and same-weekday daily medians; absent days
    are not zero-filled. 'all' shares max_requests across three reports and returns
    mixed/undetermined signs explicitly. context_json is a bounded version=1
    caller-declared ledger, never an independently verified incident registry.
    Signed count deltas are descriptive; cause and collection health stay unknown.
    """
    params = dict(site=site, days=days, end_date=end_date, dimensions=deepcopy(dimensions),
                  filters=deepcopy(filters), search_type=search_type,
                  aggregation_type=aggregation_type, row_limit=row_limit,
                  max_requests=max_requests, limit=limit, reference_strategy=reference_strategy,
                  history_days=history_days, min_support=min_support,
                  context_json='provided' if context_json is not None else None)
    _integer(days, 'days', 1, 366)
    if reference_strategy not in ('weekday', 'year_on_year', 'rolling_daily', 'all'):
        raise ValueError('Unsupported reference_strategy')
    _integer(history_days, 'history_days', 42, 364)
    _integer(min_support, 'min_support', 2, 52)
    timezone = 'America/Los_Angeles'
    eligible_end = datetime.now(ZoneInfo(timezone)).date() - timedelta(days=3)
    end = eligible_end if end_date is None else _date(end_date)
    if end > eligible_end:
        raise ValueError('end_date must respect the three-day Pacific reporting lag')
    shift_days = ((days + 6) // 7) * 7
    alignment = {'weekday_aligned': True, 'leap_day_clamped': False}
    try:
        start = end - timedelta(days=days - 1)
        baseline_end = end - timedelta(days=shift_days)
        baseline_start = start - timedelta(days=shift_days)
        if reference_strategy in ('rolling_daily', 'all'):
            history_end = start - timedelta(days=1)
            history_start = history_end - timedelta(days=history_days-1)
        if reference_strategy in ('year_on_year', 'all'):
            baseline_start, baseline_end, alignment = annual_window(end, days)
            shift_days = (end - baseline_end).days
    except OverflowError as exc:
        raise ValueError('Reference window exceeds supported date bounds') from exc
    windows = {'baseline': {'start': baseline_start.isoformat(), 'end': baseline_end.isoformat()},
               'comparison': {'start': start.isoformat(), 'end': end.isoformat()}}
    context_windows = deepcopy(windows)
    if reference_strategy in ('rolling_daily', 'all'):
        context_windows['rolling_history'] = {'start': history_start.isoformat(), 'end': history_end.isoformat()}
    if reference_strategy == 'all':
        weekday_shift = ((days + 6) // 7) * 7
        context_windows['weekday_baseline'] = {'start': (start-timedelta(days=weekday_shift)).isoformat(),
                                               'end': (end-timedelta(days=weekday_shift)).isoformat()}
    preflight = context_preflight(context_json, site, datetime.now(ZoneInfo(timezone)), context_windows)
    dimension_count = len(dimensions) if isinstance(dimensions, list) else 4
    minimum_requests = 4 + 2 * dimension_count
    _integer(max_requests, 'max_requests', minimum_requests, 100)
    if reference_strategy == 'all':
        caps = [max_requests // 3, max_requests // 3, max_requests - 2*(max_requests // 3)]
        if caps[0] < minimum_requests or caps[2] < minimum_requests + 1:
            raise ValueError('max_requests must fund each reference and the rolling history query')
        references = {}
        for strategy, cap in zip(('weekday', 'year_on_year', 'rolling_daily'), caps):
            references[strategy] = json.loads(search_weekday_reference(
                site=site, days=days, end_date=end.isoformat(), dimensions=dimensions, filters=filters,
                search_type=search_type, aggregation_type=aggregation_type, row_limit=row_limit,
                max_requests=cap, limit=limit, reference_strategy=strategy,
                history_days=history_days, min_support=min_support))
        usable = []
        for strategy, report in references.items():
            reference = report['robust_reference'] if strategy == 'rolling_daily' else report['weekday_reference']
            if reference['status'] == 'observed' and reference['delta'] is not None:
                usable.append(reference['delta']['clicks'])
        signs = {1 if value > 0 else -1 if value < 0 else 0 for value in usable}
        assessment = ('undetermined' if len(usable) != 3 else 'mixed' if len(signs) > 1 else
                      'consistent_decline' if signs == {-1} else 'consistent_increase' if signs == {1} else 'unchanged')
        return json.dumps(with_meta({'site': site, 'engine': 'google', 'reference_strategy': 'all',
            'references': references, 'assessment': assessment, 'causal_interpretation': False,
            'context_preflight': preflight, 'request_budget': {'max_requests': max_requests,
                'requests_made': sum(r['request_budget']['requests_made'] for r in references.values()),
                'hidden_retries': False}}, 'search_weekday_reference', params,
            sources={'google': {'site': site}}), allow_nan=False)
    child_budget = max_requests - (1 if reference_strategy == 'rolling_daily' else 0)
    if child_budget < minimum_requests:
        raise ValueError('max_requests must also fund the rolling history query')
    result = json.loads(search_change_breakdown(
        site=site, baseline_start=windows['baseline']['start'], baseline_end=windows['baseline']['end'],
        comparison_start=windows['comparison']['start'], comparison_end=windows['comparison']['end'],
        dimensions=dimensions, filters=filters, search_type=search_type, data_state='final',
        aggregation_type=aggregation_type, row_limit=row_limit, max_requests=child_budget, limit=limit))
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
        'method': ('prior_year_calendar_end_equal_length' if reference_strategy == 'year_on_year'
                   else 'prior_disjoint_same_weekdays'), 'alignment': alignment, 'status': 'unavailable' if reasons else 'observed',
        'reasons': reasons, 'shift_days': shift_days, 'effective_windows': windows,
        'eligible_end': eligible_end.isoformat(), 'report_lag_days': 3, 'timezone': timezone,
        'delta': None if reasons else {metric: result['baseline_delta'][metric]
                                      for metric in ('clicks', 'impressions')},
        'causal_interpretation': False, 'upstream_meta': upstream_meta,
    }
    result['reference_strategy'] = reference_strategy
    result['context_preflight'] = preflight
    if reference_strategy == 'rolling_daily':
        body = {'startDate': history_start.isoformat(), 'endDate': history_end.isoformat(),
                'dimensions': ['date'], 'rowLimit': history_days, 'type': search_type,
                'dataState': 'final', 'aggregationType': aggregation_type}
        if filters:
            body['dimensionFilterGroups'] = [{'groupType': 'and', 'filters': deepcopy(filters)}]
        answer, error = None, None
        try:
            answer = execute_google(get_searchconsole_service().searchanalytics().query(siteUrl=site, body=body))
            if not isinstance(answer, dict) or not isinstance(answer.get('rows', []), list) or len(answer.get('rows', [])) > history_days:
                raise ValueError('Malformed rolling history response')
        except Exception as exc:
            answer, error = None, type(exc).__name__
        result['request_budget']['requests_made'] += 1
        result['request_budget']['max_requests'] = max_requests
        robust = robust_reference(answer, error, history_start, history_end, start, end,
                                  result['baseline_totals']['comparison'], min_support)
        comparison_reasons = [reason for reason in reasons if not reason.startswith('baseline_')
                              and reason != 'aggregate_comparison_unavailable']
        if comparison_reasons:
            robust['status'], robust['delta'], robust['expected_counts'] = 'unavailable', None, None
            robust['reasons'] = sorted(set(robust['reasons'] + comparison_reasons))
        result['robust_reference'] = robust
    return json.dumps(with_meta(result, 'search_weekday_reference', params,
                                sources=upstream_meta.get('sources')), allow_nan=False)
