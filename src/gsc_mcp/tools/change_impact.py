"""Caller-declared page changes with descriptive, coverage-aware GSC follow-up."""
from __future__ import annotations

import json
import re
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from gsc_mcp.meta import with_meta
from gsc_mcp.tools.analytics import _ANALYTICS_LAG_DAYS
from gsc_mcp.tools.search_breakdown import _date, _integer, search_change_breakdown
from gsc_mcp.url_safety import normalize_hostname, normalize_observation_url

_GOOGLE_TIMEZONE = 'America/Los_Angeles'
_METRICS = ('clicks', 'impressions', 'ctr')


def _text(value, name: str, maximum: int) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError(f'{name} must be a nonempty string of at most {maximum} characters')
    return value


def _page(site: str, url: str) -> str:
    _text(url, 'url', 2048)
    if '#' in url:
        raise ValueError('Page URLs must not contain fragments')
    normalized = normalize_observation_url(url)
    if site.startswith('sc-domain:'):
        domain = site.removeprefix('sc-domain:')
        if any(c in domain for c in '/?#:@'):
            raise ValueError('Invalid domain property')
        host = normalize_hostname(domain).encode('idna').decode('ascii')
        page_host = urlsplit(normalized).hostname
        belongs = page_host == host or page_host.endswith('.' + host)
    else:
        if '?' in site or '#' in site:
            raise ValueError('URL-prefix properties must not contain query or fragment')
        prefix = normalize_observation_url(site)
        belongs = normalized.startswith(prefix)
    if not belongs:
        raise ValueError('Page URL is outside the declared property')
    return normalized


def _event(event: dict) -> dict:
    required = {'site', 'url', 'changed_at', 'timezone', 'description'}
    if not isinstance(event, dict) or not required <= set(event) or set(event) - required - {'revision', 'baseline_id'}:
        raise ValueError('event requires site/url/changed_at/timezone/description; optional revision/baseline_id')
    _text(event['site'], 'event.site', 2048)
    url = _page(event['site'], event['url'])
    _text(event['description'], 'event.description', 4000)
    _text(event['timezone'], 'event.timezone', 128)
    stamp = _text(event['changed_at'], 'event.changed_at', 64)
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})', stamp):
        raise ValueError('changed_at must be an ISO timestamp with seconds and explicit UTC offset')
    try:
        moment = datetime.fromisoformat(stamp)
        zone = ZoneInfo(event['timezone'])
        if moment.utcoffset() != moment.astimezone(zone).utcoffset():
            raise ValueError('changed_at offset does not match the declared timezone')
        google_day = moment.astimezone(ZoneInfo(_GOOGLE_TIMEZONE)).date().isoformat()
    except (ValueError, OverflowError, ZoneInfoNotFoundError) as exc:
        raise ValueError('Invalid event timestamp/timezone or offset mismatch') from exc
    for field in ('revision', 'baseline_id'):
        if field in event:
            _text(event[field], f'event.{field}', 256)
    return {**deepcopy(event), 'provenance': 'caller_declared', 'effective_url': url,
            'google_event_date': google_day}


def seo_change_impact(
    event: dict,
    baseline_start: str,
    baseline_end: str,
    comparison_start: str,
    comparison_end: str,
    filters: list[dict] | None = None,
    search_type: str = 'web',
    align_weekdays: bool = False,
    page_mapping: dict | None = None,
    concurrent_changes: list[str] | None = None,
    row_limit: int = 1000,
    max_requests: int = 20,
    limit: int = 50,
) -> str:
    """Associate a caller event with equal explicit GSC before/after windows.

    event requires site/url/changed_at/timezone/description, optionally revision
    and baseline_id. changed_at includes seconds and an offset matching its IANA
    timezone. Exclude the entire event day in America/Los_Angeles. Optional
    page_mapping requires baseline_url/comparison_url and selects both URLs in
    both periods; it declares identity, without discovering redirects/canonicals.
    No event persistence, page editing or provider notification occurs. The
    caller retains the returned record. Observed changes do not identify causes.
    """
    record = _event(event)
    site = record['site']
    start_a, end_a, start_b, end_b = map(_date, (baseline_start, baseline_end, comparison_start, comparison_end))
    days = (end_a - start_a).days + 1
    event_day = _date(record['google_event_date'])
    if not 1 <= days <= 25000 or (end_b - start_b).days + 1 != days or not end_a < event_day < start_b:
        raise ValueError('Equal ordered windows of 1..25000 days must exclude the whole Google event date')
    if type(align_weekdays) is not bool or (align_weekdays and start_a.weekday() != start_b.weekday()):
        raise ValueError('align_weekdays must be boolean; aligned windows start on the same weekday')
    if search_type not in ('web', 'image', 'video', 'news'):
        raise ValueError('Unsupported search_type')
    _integer(row_limit, 'row_limit', 1, 100000)
    _integer(max_requests, 'max_requests', 12, 100)
    _integer(limit, 'limit', 1, 1000)
    if concurrent_changes is not None and (not isinstance(concurrent_changes, list) or len(concurrent_changes) > 20):
        raise ValueError('concurrent_changes must be a list of at most 20 descriptions')
    changes = [] if concurrent_changes is None else deepcopy(concurrent_changes)
    for change in changes:
        _text(change, 'concurrent change', 2000)
    actual_filters = [] if filters is None else deepcopy(filters)
    if not isinstance(actual_filters, list) or len(actual_filters) > 20:
        raise ValueError('filters must be a list of at most 20 non-page filters')
    for item in actual_filters:
        if (not isinstance(item, dict) or set(item) != {'dimension', 'operator', 'expression'}
                or item['dimension'] not in ('query', 'country', 'device', 'searchAppearance')
                or item['operator'] not in ('equals', 'notEquals', 'contains', 'notContains', 'includingRegex', 'excludingRegex')):
            raise ValueError('Invalid non-page dimension/operator/expression filter')
        _text(item['expression'], 'filter expression', 2048)
    mapping = None
    urls = [record['effective_url']]
    if page_mapping is not None:
        if not isinstance(page_mapping, dict) or set(page_mapping) != {'baseline_url', 'comparison_url'}:
            raise ValueError('page_mapping requires exactly baseline_url/comparison_url')
        urls = [_page(site, page_mapping[k]) for k in ('baseline_url', 'comparison_url')]
        if record['effective_url'] not in urls:
            raise ValueError('page_mapping must include the declared event URL')
        mapping = {**deepcopy(page_mapping), 'provenance': 'caller_declared',
                   'effective_baseline_url': urls[0], 'effective_comparison_url': urls[1]}
    unique_urls = list(dict.fromkeys(urls))
    actual_filters.append({'dimension': 'page', 'operator': 'equals' if len(unique_urls) == 1 else 'includingRegex',
                           'expression': unique_urls[0] if len(unique_urls) == 1 else
                           '^(' + '|'.join(re.escape(url) for url in unique_urls) + ')$'})
    params = dict(event=deepcopy(event), baseline_start=baseline_start, baseline_end=baseline_end,
                  comparison_start=comparison_start, comparison_end=comparison_end,
                  filters=deepcopy(filters), search_type=search_type, align_weekdays=align_weekdays,
                  page_mapping=deepcopy(page_mapping), concurrent_changes=deepcopy(concurrent_changes),
                  row_limit=row_limit, max_requests=max_requests, limit=limit)
    started = datetime.now(timezone.utc)
    cutoff = started.astimezone(ZoneInfo(_GOOGLE_TIMEZONE)).date() - timedelta(days=_ANALYTICS_LAG_DAYS)
    reasons = []
    evidence = None
    fetch_error = None
    before = after = None
    delta = {'clicks': None, 'impressions': None, 'ctr_percentage_points': None}
    if end_b > cutoff:
        reasons.append('insufficient_post_change_data')
    else:
        try:
            evidence = json.loads(search_change_breakdown(
                site=site, baseline_start=baseline_start, baseline_end=baseline_end,
                comparison_start=comparison_start, comparison_end=comparison_end,
                filters=actual_filters, search_type=search_type, data_state='final',
                aggregation_type='auto', row_limit=row_limit, max_requests=max_requests, limit=limit))
        except Exception as exc:
            # Authentication/service initialization can fail before #21 fetch handling.
            # Keep only the type, since exception text may contain credentials.
            fetch_error = type(exc).__name__
            reasons.append('provider_unavailable')
        if evidence is not None:
            for name, reason in (('baseline', 'insufficient_baseline_data'),
                                ('comparison', 'insufficient_post_change_data')):
                total = evidence['baseline_totals'][name]
                period = evidence['periods'][name]
                marker = period['first_incomplete_date']
                if (total['availability'] != 'observed' or
                        any(total['metrics'][k] is None for k in ('clicks', 'impressions')) or
                        period['coverage_probe_status'] != 'observed' or period['anomalies'] or
                        period['missing_requested_dates'] or
                        (marker is not None and _date(marker) <= _date(period['requested_end']))):
                    reasons.append(reason)
            if not evidence['baseline_comparison']['comparable']:
                reasons.append('incompatible_aggregation')
            # A page-filtered report must resolve to byPage, including date probes.
            if any(evidence['periods'][n]['response_aggregation_type'] != 'byPage' or
                   evidence['baseline_totals'][n]['response_aggregation_type'] != 'byPage'
                   for n in ('baseline', 'comparison')):
                if 'incompatible_aggregation' not in reasons:
                    reasons.append('incompatible_aggregation')
            before, after = ({k: deepcopy(evidence['baseline_totals'][n]['metrics'][k])
                             for k in (*_METRICS, 'unavailable_metrics')}
                            for n in ('baseline', 'comparison'))
            if not reasons:
                delta = {k: evidence['baseline_delta'][k] for k in delta}
    result = {
        'event': record, 'site': site, 'engine': 'google', 'page_mapping': mapping,
        'concurrent_changes': changes,
        'windows': {'baseline': {'start': baseline_start, 'end': baseline_end},
                    'comparison': {'start': comparison_start, 'end': comparison_end},
                    'days': days, 'timezone': _GOOGLE_TIMEZONE,
                    'weekday_alignment_requested': align_weekdays,
                    'weekday_aligned': start_a.weekday() == start_b.weekday()},
        'source_options': {'search_type': search_type, 'data_state': 'final',
                           'aggregation_type': 'auto', 'filters': actual_filters},
        'maturity_policy': {'lag_days': _ANALYTICS_LAG_DAYS, 'latest_eligible_date': cutoff.isoformat(),
                            'basis': 'conservative_reporting_lag_policy', 'provider_finalization_verified': False},
        'comparison': {'status': 'unavailable' if reasons else 'observed', 'reasons': reasons,
                       'before': before, 'after': after, 'descriptive_delta': delta,
                       'scope': 'combined_mapped_urls_in_both_windows' if len(unique_urls) > 1 else 'declared_page',
                       'fetch_error': fetch_error},
        'search_evidence': evidence,
        'collection': {'started_at': started.isoformat(), 'completed_at': datetime.now(timezone.utc).isoformat()},
        'persistence': {'status': 'not_persisted', 'retention': 'caller retains the returned event and report'},
        'attribution': {'causal_effect': None, 'status': 'not_identified',
                        'reason': 'Temporal succession and observed differences do not identify the event effect.'},
        'limitations': ['Seasonality, search-system changes and other edits may affect the observations.',
                        'Caller-declared events and URL mappings do not prove deployment or canonical identity.',
                        'Missing or censored rows and dates remain unknown, not observed zero.',
                        'Final records are requested; the lag policy does not prove provider finalization.',
                        'Mapped URL totals describe both URLs in both windows, including any overlap.',
                        'No causal lift, ROI, significance or ranking guarantee is estimated.'],
    }
    return json.dumps(with_meta(result, 'seo_change_impact', params,
                                sources={'google': {'site': site}}), allow_nan=False)
