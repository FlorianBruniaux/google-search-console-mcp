"""Weekly reference checks exercise the real breakdown with a fake Google transport."""
import json
from copy import deepcopy
from datetime import date, datetime, timedelta
from types import SimpleNamespace

import pytest


@pytest.fixture
def run(monkeypatch):
    from gsc_mcp.tools import search_breakdown

    def call(responder=None, **kwargs):
        from gsc_mcp.tools import traffic_reference

        class FixedDateTime(datetime):
            @classmethod
            def now(cls, tz=None):
                return cls(2026, 10, 9, 12, tzinfo=tz)

        monkeypatch.setattr(traffic_reference, 'datetime', FixedDateTime)
        calls = []

        def query(siteUrl, body):
            calls.append({'site': siteUrl, **deepcopy(body)})

            def execute():
                if responder:
                    return responder(body)
                comparison = body['endDate'] == kwargs.get('end_date', '2026-01-31')
                if body.get('dimensions') == ['date']:
                    start, end = date.fromisoformat(body['startDate']), date.fromisoformat(body['endDate'])
                    return response([row((start + timedelta(days=i)).isoformat())
                                     for i in range((end - start).days + 1)])
                if not body.get('dimensions'):
                    return response([row(None, 80 if comparison else 100, 800 if comparison else 1000)])
                return response([row('segment', 9999, 99999)])

            return SimpleNamespace(execute=execute)

        monkeypatch.setattr(search_breakdown, 'get_searchconsole_service',
                            lambda: SimpleNamespace(searchanalytics=lambda: SimpleNamespace(query=query)))
        monkeypatch.setattr(traffic_reference, 'get_searchconsole_service',
                            lambda: SimpleNamespace(searchanalytics=lambda: SimpleNamespace(query=query)), raising=False)
        options = dict(site='sc-domain:Example.COM', days=28, end_date='2026-01-31', dimensions=['query'])
        options.update(kwargs)
        return json.loads(traffic_reference.search_weekday_reference(**options)), calls

    return call


def row(key, clicks=1, impressions=10):
    return {'keys': [] if key is None else [key], 'clicks': clicks, 'impressions': impressions,
            'ctr': .1, 'position': 2}


def response(rows):
    return {'rows': rows, 'responseAggregationType': 'byProperty'}


@pytest.mark.parametrize(('days', 'before_start', 'before_end', 'after_start', 'shift'), [
    (28, '2025-12-07', '2026-01-03', '2026-01-04', 28),
    (10, '2026-01-08', '2026-01-17', '2026-01-22', 14),
    (7, '2026-01-18', '2026-01-24', '2026-01-25', 7),
    (1, '2026-01-24', '2026-01-24', '2026-01-31', 7),
])
def test_equal_disjoint_weekday_windows_and_descriptive_aggregate_delta(run, days, before_start,
                                                                      before_end, after_start, shift):
    # A fixed seven-day shift would overlap longer windows; summing segments would inflate deltas.
    out, calls = run(days=days)
    before, after = out['periods']['baseline'], out['periods']['comparison']
    assert (before['requested_start'], before['requested_end']) == (before_start, before_end)
    assert (after['requested_start'], after['requested_end']) == (after_start, '2026-01-31')
    assert before['requested_days'] == after['requested_days'] == days
    reference = out['weekday_reference']
    assert reference['shift_days'] == shift
    assert reference['status'] == 'observed'
    assert reference['delta'] == {'clicks': -20, 'impressions': -200}
    assert reference['causal_interpretation'] is False
    assert len(calls) == out['request_budget']['requests_made'] == 6


def test_newest_eligible_window_uses_pacific_reporting_lag(run):
    out, calls = run(end_date=None, days=7)
    assert out['periods']['comparison']['requested_start'] == '2026-09-30'
    assert out['periods']['comparison']['requested_end'] == '2026-10-06'
    assert out['weekday_reference']['eligible_end'] == '2026-10-06'
    assert out['weekday_reference']['report_lag_days'] == 3
    assert out['weekday_reference']['timezone'] == 'America/Los_Angeles'
    assert {c['endDate'] for c in calls} == {'2026-09-29', '2026-10-06'}


@pytest.mark.parametrize('options', [
    {'days': 0}, {'days': -1}, {'days': 367}, {'days': True}, {'days': 2.5},
    {'end_date': '20261006'}, {'end_date': '2026-02-30'}, {'end_date': '2026-10-07'},
    {'end_date': '2027-01-01'}, {'end_date': '0001-01-01'},
])
def test_invalid_date_bounds_and_durations_fail_before_provider(run, options):
    # Removing validation must expose either a provider call or an invalid window.
    with pytest.raises(ValueError):
        run(lambda body: pytest.fail('invalid bounds must not reach Google'), **options)


def test_filters_source_and_child_provenance_survive_the_wrapper(run):
    filters = [{'dimension': 'country', 'operator': 'equals', 'expression': 'fra'}]
    out, calls = run(filters=filters, search_type='image', aggregation_type='byProperty')
    assert all(c['site'] == 'sc-domain:Example.COM' and c['type'] == 'image'
               and c['dataState'] == 'final' and c['aggregationType'] == 'byProperty'
               and c['dimensionFilterGroups'] == [{'groupType': 'and', 'filters': filters}]
               for c in calls)
    assert out['filters'] == filters
    assert out['engine'] == 'google'
    assert out['_meta']['tool'] == 'search_weekday_reference'
    assert out['_meta']['params']['end_date'] == '2026-01-31'
    assert out['_meta']['sources']['google']['site'] == 'sc-domain:Example.COM'
    assert out['weekday_reference']['upstream_meta']['tool'] == 'search_change_breakdown'
    assert out['weekday_reference']['upstream_meta']['params']['data_state'] == 'final'


@pytest.mark.parametrize('missing', ['all_dates', 'one_date', 'aggregate'])
def test_missing_historical_observations_are_unavailable_not_zero(run, missing):
    def answer(body):
        baseline = body['startDate'] == '2025-12-07'
        if body.get('dimensions') == ['date']:
            start = date.fromisoformat(body['startDate'])
            dates = [row((start + timedelta(days=i)).isoformat()) for i in range(28)]
            return response(([] if missing == 'all_dates' else dates[1:])
                            if baseline and missing != 'aggregate' else dates)
        if not body.get('dimensions'):
            return response([] if baseline and missing == 'aggregate' else [row(None, 100, 1000)])
        return response([])

    out, _ = run(answer)
    assert out['weekday_reference']['status'] == 'unavailable'
    assert out['weekday_reference']['delta'] is None
    assert out['weekday_reference']['reasons']
    if missing == 'aggregate':
        assert out['baseline_totals']['baseline']['metrics']['clicks'] is None
        assert out['baseline_delta']['clicks'] is None
    else:
        assert out['periods']['baseline']['observed_day_count'] < 28


def test_upstream_failure_retained_without_retry_or_extra_probe(run):
    def answer(body):
        raise TimeoutError('private provider detail')

    out, calls = run(answer)
    assert len(calls) == out['request_budget']['requests_made'] == 6
    assert out['baseline_totals']['baseline']['fetch_error'] == 'TimeoutError'
    assert out['periods']['baseline']['fetch_error'] == 'TimeoutError'
    assert out['breakdowns']['query']['baseline_coverage']['fetch_error'] == 'TimeoutError'
    assert out['weekday_reference']['status'] == 'unavailable'
    assert out['weekday_reference']['delta'] is None
    assert 'private provider detail' not in json.dumps(out)


def test_incomplete_final_data_marker_is_not_treated_as_a_finalized_reference(run):
    def answer(body):
        if body.get('dimensions') == ['date']:
            start = date.fromisoformat(body['startDate'])
            return {**response([row((start + timedelta(days=i)).isoformat()) for i in range(28)]),
                    'metadata': {'first_incomplete_date': body['endDate']}}
        return response([row(None if not body.get('dimensions') else 'segment', 100, 1000)])

    out, _ = run(answer)
    assert out['data_state'] == 'final'
    assert out['weekday_reference']['status'] == 'unavailable'
    assert out['weekday_reference']['delta'] is None
    assert out['periods']['baseline']['first_incomplete_date'] == '2026-01-03'


@pytest.mark.parametrize('end,days,baseline_end', [('2024-02-29', 7, '2023-02-28'), ('2025-03-09', 7, '2024-03-09')])
def test_annual_reference_discloses_calendar_and_weekday_alignment(run, end, days, baseline_end):
    out, calls = run(reference_strategy='year_on_year', days=days, end_date=end)
    reference = out['weekday_reference']
    assert reference['method'] == 'prior_year_calendar_end_equal_length'
    assert out['periods']['baseline']['requested_end'] == baseline_end
    assert reference['alignment']['weekday_aligned'] is False
    assert reference['alignment']['leap_day_clamped'] is (end == '2024-02-29')
    assert len(calls) == 6


def test_rolling_reference_uses_observed_daily_medians_and_preserves_zeros(run):
    def answer(body):
        if body.get('dimensions') == ['date']:
            start, end = date.fromisoformat(body['startDate']), date.fromisoformat(body['endDate'])
            return response([row((start+timedelta(days=i)).isoformat(), 0, 10) for i in range((end-start).days+1)])
        return response([row(None if not body.get('dimensions') else 'segment', 80, 800)])
    out, calls = run(answer, reference_strategy='rolling_daily')
    robust = out['robust_reference']
    assert robust['status'] == 'observed'
    assert robust['expected_counts']['clicks'] == 0
    assert robust['delta']['clicks'] == 80
    assert robust['support_by_weekday']['0']['clicks']['days'] == 8
    assert len(calls) == out['request_budget']['requests_made'] == 7


def test_missing_rolling_history_is_not_zero_filled(run):
    def answer(body):
        if body.get('dimensions') == ['date']:
            return response([])
        return response([row(None if not body.get('dimensions') else 'segment', 80, 800)])
    out, _ = run(answer, reference_strategy='rolling_daily')
    assert out['robust_reference']['status'] == 'unavailable'
    assert out['robust_reference']['delta'] is None
    assert out['robust_reference']['omitted_days'] == 56


def test_all_references_share_one_total_request_cap_and_conflicting_signs_are_mixed(run):
    out, calls = run(reference_strategy='all', max_requests=20)
    assert len(calls) <= 20
    assert out['request_budget']['requests_made'] == len(calls)
    assert out['assessment'] == 'mixed'
    assert out['causal_interpretation'] is False
    assert set(out['references']) == {'weekday', 'year_on_year', 'rolling_daily'}


@pytest.mark.parametrize('options', [
    {'reference_strategy':'unknown'}, {'reference_strategy':'all', 'max_requests':10},
    {'reference_strategy':'year_on_year', 'days':366, 'end_date':'2026-01-31'},
    {'reference_strategy':'rolling_daily', 'history_days':6},
    {'reference_strategy':'rolling_daily', 'min_support':True},
    {'context_json':json.dumps({'version':1,'site':'sc-domain:other.test'})},
])
def test_new_preflight_validation_precedes_provider_calls(run, options):
    with pytest.raises(ValueError):
        run(lambda body: pytest.fail('invalid preflight reached Google'), **options)


def test_context_staleness_and_timing_never_confirm_collection_health_or_cause(run):
    context = {'version':1, 'site':'sc-domain:Example.COM', 'retrieved_at':'2026-09-01T00:00:00Z',
               'collection_incidents':[{'id':'incident', 'provider':'google', 'report_type':'search_analytics',
                   'start':'2026-01-01', 'end':'2026-01-31', 'source_url':'https://status.search.google.com/',
                   'uncertainty':'scope_unverified'}], 'business_events':[]}
    out, _ = run(context_json=json.dumps(context))
    preflight = out['context_preflight']
    assert preflight['collection_registry_status'] == 'stale_caller_declared'
    assert preflight['collection_health'] == 'unknown'
    assert preflight['records'][0]['date_overlap'] is True
    assert preflight['records'][0]['causal_interpretation'] is False


def test_absent_incident_registry_is_unknown_not_all_clear(run):
    out, _ = run()
    assert out['context_preflight']['collection_registry_status'] == 'unavailable'
    assert out['context_preflight']['collection_health'] == 'unknown'


def test_weekday_default_does_not_require_an_unused_history_window(run):
    out, _ = run(days=1, end_date='0001-01-10')
    assert out['periods']['baseline']['requested_end'] == '0001-01-03'


def test_one_historical_spike_does_not_move_the_daily_median(run):
    def answer(body):
        if body.get('dimensions') == ['date']:
            start, end = date.fromisoformat(body['startDate']), date.fromisoformat(body['endDate'])
            return response([row((start+timedelta(days=i)).isoformat(), 9999 if i == 0 else 1, 10)
                             for i in range((end-start).days+1)])
        return response([row(None if not body.get('dimensions') else 'segment', 80, 800)])
    out, _ = run(answer, reference_strategy='rolling_daily')
    assert out['robust_reference']['expected_counts']['clicks'] == 28
    fields = out['_meta']['evidence']['fields']
    assert fields['/robust_reference/expected_counts/clicks']['basis'] == 'derived'


def test_history_failure_uses_one_attempt_and_keeps_error_reason(run):
    def answer(body):
        if body['startDate'] == '2025-11-09':
            raise TimeoutError('private provider message')
        if body.get('dimensions') == ['date']:
            start = date.fromisoformat(body['startDate'])
            return response([row((start+timedelta(days=i)).isoformat()) for i in range(28)])
        return response([row(None if not body.get('dimensions') else 'segment', 80, 800)])
    out, calls = run(answer, reference_strategy='rolling_daily')
    assert len(calls) == 7
    assert out['robust_reference']['fetch_error'] == 'TimeoutError'
    assert out['robust_reference']['delta'] is None
    assert 'private provider message' not in json.dumps(out)


def test_absent_annual_dates_leave_multireference_assessment_undetermined(run):
    def answer(body):
        if body.get('dimensions') == ['date']:
            start, end = date.fromisoformat(body['startDate']), date.fromisoformat(body['endDate'])
            return response([] if body['endDate'] == '2025-01-31' else
                            [row((start+timedelta(days=i)).isoformat()) for i in range((end-start).days+1)])
        return response([row(None if not body.get('dimensions') else 'segment', 80, 800)])
    out, _ = run(answer, reference_strategy='all', max_requests=20)
    assert out['assessment'] == 'undetermined'
    assert out['references']['year_on_year']['weekday_reference']['delta'] is None
