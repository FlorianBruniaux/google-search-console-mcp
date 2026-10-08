"""Behavior checks use a request-body-driven fake Google transport."""
import json
from copy import deepcopy
from types import SimpleNamespace

import pytest


@pytest.fixture
def run(monkeypatch):
    from gsc_mcp.tools import search_breakdown

    def call(responder=None, **kwargs):
        calls = []

        def query(siteUrl, body):
            calls.append({'site': siteUrl, **deepcopy(body)})

            def execute():
                if responder:
                    return responder(body)
                if body.get('dimensions') == ['date']:
                    return response([row(body['startDate'], 1, 10), row(body['endDate'], 1, 10)])
                if not body.get('dimensions'):
                    return response([row(None, 100 if body['startDate'] == '2026-01-01' else 80, 1000)])
                baseline = body['startDate'] == '2026-01-01'
                return response([row('drop', 30 if baseline else 15, 100),
                                 row('gain', 5 if baseline else 10, 100),
                                 row('same', 2, 100), row('zero', 0, 0),
                                 row('seen-before' if baseline else 'seen-after', 10, 100)])

            return SimpleNamespace(execute=execute)

        monkeypatch.setattr(search_breakdown, 'get_searchconsole_service',
                            lambda: SimpleNamespace(searchanalytics=lambda: SimpleNamespace(query=query)))
        options = dict(site='sc-domain:Example.COM', baseline_start='2026-01-01',
                       baseline_end='2026-01-02', comparison_start='2026-02-01',
                       comparison_end='2026-02-02', dimensions=['query'])
        options.update(kwargs)
        return json.loads(search_breakdown.search_change_breakdown(**options)), calls

    return call


def row(key, clicks=1, impressions=10, **kwargs):
    return {'keys': [] if key is None else [key], 'clicks': clicks,
            'impressions': impressions, 'ctr': .99, 'position': 2.12345, **kwargs}


def response(rows, aggregation='byProperty', **kwargs):
    return {'rows': rows, 'responseAggregationType': aggregation, **kwargs}


def test_observed_changes_zeros_and_unseen_rows(run):
    out, calls = run(limit=1)
    report = out['breakdowns']['query']
    assert report['matched'][0]['key'] == 'drop'
    assert report['matched'][0]['delta']['clicks'] == -15
    assert report['matched_count'] == 4
    assert report['matched_delta']['clicks'] == -10
    assert report['baseline_only'][0]['comparison'] is None
    assert report['baseline_only'][0]['delta'] is None
    assert report['comparison_only'][0]['baseline'] is None
    assert report['display_truncated'] is True
    assert report['observed_sums']['baseline']['clicks'] == 47
    assert report['reconciliation']['baseline_residual']['clicks'] == 53
    assert report['reconciliation']['total_delta_minus_matched_delta']['clicks'] == -10
    assert out['baseline_delta']['clicks'] == -20
    assert out['baseline_totals']['baseline']['metrics']['ctr'] == .1
    assert out['baseline_totals']['baseline']['metrics']['position'] == 2.12345
    assert out['request_budget']['requests_made'] == len(calls) == 6
    full, _ = run()
    zero = next(r for r in full['breakdowns']['query']['matched'] if r['key'] == 'zero')
    assert zero['baseline']['clicks'] == 0
    assert zero['baseline']['ctr'] is None
    assert zero['baseline']['position'] is None
    assert full['_meta']['params']['baseline_start'] == '2026-01-01'


@pytest.mark.parametrize('options', [
    {'baseline_start': '20260101'}, {'baseline_start': '2026-02-30'},
    {'baseline_end': '2026-01-03'}, {'baseline_end': '2025-12-31'},
    {'comparison_start': '2026-01-02', 'comparison_end': '2026-01-03'},
    {'dimensions': []}, {'dimensions': ['query', 'query']}, {'dimensions': ['date']},
    {'search_type': 'discover'}, {'data_state': 'hourly_all'},
    {'aggregation_type': 'byProperty', 'dimensions': ['page']},
    {'aggregation_type': 'byPage', 'dimensions': ['page']},
    {'row_limit': True}, {'max_requests': 5}, {'limit': 0},
    {'filters': [{'dimension': 'query', 'operator': 'bad', 'expression': 'x'}]},
])
def test_invalid_inputs_before_credentials(monkeypatch, options):
    from gsc_mcp.tools import search_breakdown
    monkeypatch.setattr(search_breakdown, 'get_searchconsole_service',
                        lambda: pytest.fail('validation must precede credentials'))
    defaults = dict(site='site', baseline_start='2026-01-01', baseline_end='2026-01-02',
                    comparison_start='2026-02-01', comparison_end='2026-02-02', dimensions=['query'])
    defaults.update(options)
    with pytest.raises(ValueError):
        search_breakdown.search_change_breakdown(**defaults)


def test_identical_source_options_and_observed_date_coverage(run):
    filters = [{'dimension': 'country', 'operator': 'equals', 'expression': 'fra'}]
    out, calls = run(filters=filters, search_type='image', data_state='all', aggregation_type='byProperty')
    assert all(c['dimensionFilterGroups'] == [{'groupType': 'and', 'filters': filters}]
               and c['type'] == 'image' and c['dataState'] == 'all'
               and c['aggregationType'] == 'byProperty' for c in calls)
    assert out['periods']['baseline']['timezone'] == 'America/Los_Angeles'
    assert out['periods']['baseline']['observed_dates'] == ['2026-01-01', '2026-01-02']
    assert out['periods']['baseline']['missing_requested_dates'] == []
    assert out['site'] == 'sc-domain:Example.COM'


def test_unknown_metrics_and_empty_results_are_not_zeros(run):
    def answer(body):
        if body.get('dimensions') == ['date']:
            return response([])
        if not body.get('dimensions'):
            return response([])
        return response([{'keys': ['unknown'], 'clicks': True, 'impressions': '10', 'position': float('nan')}])
    out, _ = run(answer)
    assert out['baseline_totals']['baseline']['metrics']['clicks'] is None
    assert out['baseline_delta']['clicks'] is None
    assert out['breakdowns']['query']['observed_sums']['baseline']['clicks'] is None
    assert out['breakdowns']['query']['matched'][0]['baseline']['impressions'] is None
    assert out['breakdowns']['query']['matched'][0]['delta']['clicks'] is None
    assert out['periods']['baseline']['missing_requested_dates'] == ['2026-01-01', '2026-01-02']
    empty, _ = run(lambda b: response([]))
    assert empty['breakdowns']['query']['matched_delta']['clicks'] is None
    assert empty['breakdowns']['query']['observed_sums']['baseline']['clicks'] is None


@pytest.mark.parametrize('aggregation,reason', [('byPage', 'aggregation_mismatch'), (None, 'aggregation_unknown')])
def test_aggregation_gates_reconciliation(run, aggregation, reason):
    def answer(body):
        if body.get('dimensions') == ['page']:
            return response([row('exact/Case?x=1', 10)], aggregation)
        return response([row(None, 100)] if not body.get('dimensions') else [], 'byProperty')
    out, _ = run(answer, dimensions=['page'])
    report = out['breakdowns']['page']
    assert report['reconciliation']['comparable'] is False
    assert report['reconciliation']['reason'] == reason
    assert report['reconciliation']['baseline_residual']['clicks'] is None
    assert report['matched'][0]['delta']['clicks'] == (0 if aggregation else None)


def test_dimension_views_are_separate_and_first_pages_fair(run):
    def answer(body):
        if len(body.get('dimensions', [])) and body['dimensions'] != ['date']:
            return response([row('x', 100, 1000)])
        return response([row(None, 100, 1000)] if not body.get('dimensions') else [])
    out, calls = run(answer, dimensions=['country', 'device'], row_limit=1, max_requests=8)
    assert len(calls) == 8
    assert set(out['breakdowns']) == {'country', 'device'}
    assert out['request_budget']['requests_made'] == 8
    for report in out['breakdowns'].values():
        assert report['baseline_coverage']['row_limit_reached'] is True
        assert report['baseline_coverage']['api_pagination_exhausted'] is False
    assert 'combined_delta' not in out


def test_budget_caps_physical_requests_with_round_robin_pages(run):
    def answer(body):
        if body.get('dimensions') in [['query'], ['country']]:
            return response([row(str(i)) for i in range(body['startRow'], body['startRow'] + body['rowLimit'])])
        return response([])
    out, calls = run(answer, dimensions=['query', 'country'], row_limit=30000, max_requests=9)
    assert len(calls) == 9
    assert [(c['dimensions'][0], c['startRow']) for c in calls[4:8]] == [
        ('query', 0), ('query', 0), ('country', 0), ('country', 0)]
    assert calls[8]['startRow'] == 25000
    assert calls[8]['rowLimit'] == 5000
    assert out['breakdowns']['country']['baseline_coverage']['request_cap_reached'] is True
    assert out['breakdowns']['query']['baseline_coverage']['rows_returned'] == 30000


def test_provider_error_retains_other_observations(run):
    def answer(body):
        if not body.get('dimensions') and body['startDate'] == '2026-01-01':
            raise RuntimeError('provider failed')
        return response([row('present', 3)])
    out, calls = run(answer, max_requests=6)
    assert len(calls) == 6
    assert out['baseline_totals']['baseline']['availability'] == 'unavailable'
    assert out['breakdowns']['query']['matched'][0]['delta']['clicks'] == 0
    assert out['baseline_delta']['clicks'] is None


def test_duplicate_keys_suppress_reconciliation(run):
    def answer(body):
        if body.get('dimensions') == ['query']:
            return response([row('duplicate'), row('duplicate')], 'byProperty')
        return response([])
    out, _ = run(answer)
    report = out['breakdowns']['query']
    assert report['baseline_coverage']['anomalies'] == ['duplicate_key']
    assert report['reconciliation']['reason'] == 'source_anomaly'
    assert report['matched_count'] == 1


def test_recent_marker_preserved_without_filling_missing_days(run):
    def answer(body):
        if body.get('dimensions') == ['date']:
            return response([row(body['startDate'])], metadata={'first_incomplete_date': body['endDate']})
        return response([])
    out, _ = run(answer, data_state='all')
    assert out['periods']['comparison']['first_incomplete_date'] == '2026-02-02'
    assert out['periods']['comparison']['missing_requested_dates'] == ['2026-02-02']
    assert out['periods']['comparison']['incompleteness_status'] == 'incomplete'


def test_field_evidence_measured_derived_rule_and_unavailable(run):
    out, _ = run()
    fields = out['_meta']['evidence']['fields']
    assert fields['/baseline_totals/baseline/metrics/clicks']['basis'] == 'measured'
    assert fields['/baseline_totals/baseline/metrics/ctr']['basis'] == 'derived'
    assert fields['/breakdowns/query/matched/0/delta/clicks']['basis'] == 'derived'
    assert fields['/breakdowns/query/reconciliation/comparable']['basis'] == 'rule'
    assert fields['/breakdowns/query/baseline_only/0/comparison']['basis'] is None


def test_aggregation_changes_across_pages_block_comparison(run):
    def answer(body):
        if body.get('dimensions') == ['query']:
            if body['startRow']:
                return response([row('tail')], 'byPage')
            return response([row(str(i)) for i in range(25000)], 'byProperty')
        return response([row(None, 100)])
    out, calls = run(answer, row_limit=30000, max_requests=8, limit=1)
    assert len(calls) == 8
    coverage = out['breakdowns']['query']['baseline_coverage']
    assert coverage['response_aggregation_types'] == ['byProperty', 'byPage']
    assert coverage['anomalies'] == ['aggregation_changed']
    assert out['breakdowns']['query']['matched'][0]['delta']['clicks'] is None
    assert out['breakdowns']['query']['reconciliation']['reason'] == 'source_anomaly'


def test_missing_coverage_probe_remains_unknown(run):
    def answer(body):
        if body.get('dimensions') == ['date']:
            raise RuntimeError('failed date probe')
        return response([row(None, 100)] if not body.get('dimensions') else [row('x')])
    out, _ = run(answer, data_state='all')
    assert out['periods']['baseline']['observed_dates'] is None
    assert out['periods']['baseline']['missing_requested_dates'] is None
    assert out['periods']['baseline']['incompleteness_status'] == 'unknown'
    assert out['breakdowns']['query']['matched'][0]['delta']['clicks'] == 0


def test_extreme_finite_provider_counts_do_not_emit_nonfinite_json(run):
    def answer(body):
        if body.get('dimensions') == ['query']:
            return response([row('x', 1e308, 1e-308), row('y', 1e308, 1e-308)])
        return response([])
    out, _ = run(answer)
    assert out['breakdowns']['query']['matched'][0]['baseline']['ctr'] is None
    assert out['breakdowns']['query']['observed_sums']['baseline']['clicks'] is None


def test_invalid_aggregation_payload_retained_as_anomaly(run):
    out, _ = run(lambda b: response([row('x')], {'bad': 'value'}))
    assert out['breakdowns']['query']['comparison']['comparable'] is False
    assert out['breakdowns']['query']['baseline_coverage']['anomalies'] == ['invalid_aggregation']


def test_failed_page_is_an_attempt_not_a_fetched_page(run):
    def answer(body):
        if body.get('dimensions') == ['query']:
            raise RuntimeError('unavailable')
        return response([])
    out, _ = run(answer)
    assert out['request_budget']['requests_made'] == 6
    assert out['breakdowns']['query']['baseline_coverage']['pages_fetched'] == 0
    assert out['breakdowns']['query']['baseline_coverage']['fetch_error'] == 'RuntimeError'


def test_metric_unavailability_reasons_distinguish_absent_and_invalid(run):
    def answer(body):
        if body.get('dimensions') == ['query']:
            return response([{'keys': ['x'], 'clicks': True, 'impressions': 0}])
        return response([])
    out, _ = run(answer)
    reasons = out['breakdowns']['query']['matched'][0]['baseline']['unavailable_metrics']
    assert reasons == {'clicks': 'invalid_provider_value', 'ctr': 'missing_counts_or_nonpositive_impressions',
                       'position': 'missing_provider_value'}


def test_malformed_aggregate_is_anomaly_and_disables_total_comparison(run):
    def answer(body):
        if not body.get('dimensions'):
            return response([row(None), row(None)])
        return response([])
    out, _ = run(answer)
    assert out['baseline_totals']['baseline']['availability'] == 'unavailable'
    assert out['baseline_totals']['baseline']['anomalies'] == ['invalid_aggregate_rows']
    assert out['baseline_comparison']['comparable'] is False
    assert out['baseline_comparison']['reason'] == 'source_anomaly'
    assert out['_meta']['evidence']['fields']['/baseline_totals/baseline/availability']['basis'] is None


def test_fetch_counts_evidence_describes_calculation_not_heuristic(run):
    out, _ = run()
    fields = out['_meta']['evidence']['fields']
    assert fields['/breakdowns/query/baseline_coverage/rows_returned']['basis'] == 'derived'
    assert fields['/breakdowns/query/baseline_coverage/pages_fetched']['basis'] == 'derived'
    assert fields['/request_budget/exhausted']['basis'] == 'rule'
