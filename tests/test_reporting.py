"""The pilot must preserve its inputs, exact source identity and byte accounting."""
import copy
import json

import pytest

from gsc_mcp.reporting import ResponseBudgetExceeded, serialize_search_report


@pytest.fixture
def inputs():
    metrics = {'clicks': None, 'impressions': 0, 'ctr': None, 'position': None,
               'unavailable_metrics': {'clicks': 'missing_provider_value', 'ctr': 'missing_counts_or_nonpositive_impressions',
                                       'position': 'missing_provider_value'}}
    report = {'site': 'https://Example.COM/exact/Case/', 'engine': 'google', 'search_type': 'web', 'data_state': 'final',
              'filters': [], 'aggregation_type': 'auto', 'periods': {'baseline': {'fetch_error': 'RuntimeError'}},
              'baseline_totals': {'baseline': {'fetch_error': 'RuntimeError', 'availability': 'unavailable'}},
              'breakdowns': {'query': {'matched': [{'key': 'été' + '界' * 1000, 'baseline': metrics, 'comparison': metrics,
                                                  'delta': {'clicks': None, 'impressions': 0}}],
                                        'baseline_only': [], 'comparison_only': [], 'displayed_counts': {'matched': 1},
                                        'display_truncated': False, 'baseline_coverage': {'fetch_error': 'RuntimeError'},
                                        'comparison_coverage': {'fetch_error': None}}}}
    return report, {'site': report['site'], 'filters': []}, {'query': {'baseline': {'exact-key': metrics}}}


def test_serializing_success_and_budget_errors_never_mutates_report_params_or_observations(inputs):
    original = copy.deepcopy(inputs)
    full = json.loads(serialize_search_report(*inputs))
    assert {key: value for key, value in full.items() if key not in ('report_contract', '_meta')} == original[0]
    assert 'response_budget' not in full
    assert inputs == original
    capped = json.loads(serialize_search_report(*inputs, max_bytes=12000))
    assert capped['error']['code'] == 'RESPONSE_BUDGET_EXCEEDED'
    assert inputs == original
    assert capped['response_budget']['omitted_unavailable_metrics']['query']['baseline:clicks:missing_provider_value'] == 1
    assert capped['response_budget']['omitted_unavailable_metrics']['query']['delta:unavailable'] == 1
    with pytest.raises(ResponseBudgetExceeded):
        serialize_search_report(*inputs, max_bytes=1)
    assert inputs == original


def test_budget_boundary_includes_own_accounting_and_metadata(inputs):
    payload = serialize_search_report(*inputs, max_bytes=99999)
    size = len(payload.encode('utf-8'))
    assert 10000 <= size < 99999  # Same digit width avoids changing the cap's own serialized width.
    exact = serialize_search_report(*inputs, max_bytes=size)
    assert len(exact.encode('utf-8')) == size
    assert json.loads(exact)['response_budget']['status'] == 'within_budget'
    under = json.loads(serialize_search_report(*inputs, max_bytes=size - 1))
    assert under['error']['code'] == 'RESPONSE_BUDGET_EXCEEDED'
    assert under['response_budget']['serialized_bytes'] <= size - 1
    assert under['_meta']['sources']['google']['site'] == 'https://Example.COM/exact/Case/'


def test_nonfinite_observation_cannot_create_a_snapshot(inputs):
    inputs[2]['nonfinite'] = float('inf')
    with pytest.raises(ValueError):
        serialize_search_report(*inputs)


def test_property_case_and_url_prefix_are_part_of_semantic_finding_identity(inputs):
    first = json.loads(serialize_search_report(*inputs))['report_contract']
    changed = copy.deepcopy(inputs)
    changed[0]['site'] = 'https://example.com/exact/case/'
    second = json.loads(serialize_search_report(*changed))['report_contract']
    assert first['findings'][0]['finding_id'] != second['findings'][0]['finding_id']


@pytest.mark.parametrize('key,value', [('engine', 'bing'), ('search_type', 'image'),
                                      ('aggregation_type', 'byPage'), ('data_state', 'all'),
                                      ('filters', [{'dimension': 'country', 'operator': 'equals', 'expression': 'fra'}])])
def test_finding_identity_keeps_distinct_source_scopes_separate(inputs, key, value):
    first = json.loads(serialize_search_report(*inputs))['report_contract']
    changed = copy.deepcopy(inputs)
    changed[0][key] = value
    second = json.loads(serialize_search_report(*changed))['report_contract']
    assert first['findings'][0]['finding_id'] != second['findings'][0]['finding_id']


def test_repeated_findings_keep_identity_and_source_references(inputs):
    first = json.loads(serialize_search_report(*inputs))['report_contract']
    second = json.loads(serialize_search_report(*copy.deepcopy(inputs)))['report_contract']
    assert first == second
    finding = first['findings'][0]
    assert finding['kind'] == 'observation' and finding['fix_candidates'] == []
    assert finding['missing_criteria'] and finding['verification_step']
    assert finding['source_ref'] == '/report_contract/scope'


def test_and_filter_order_does_not_change_finding_identity_but_raw_scope_is_kept(inputs):
    inputs[0]['filters'] = [{'dimension': 'country', 'operator': 'equals', 'expression': 'fra'},
                            {'dimension': 'device', 'operator': 'equals', 'expression': 'mobile'}]
    first = json.loads(serialize_search_report(*inputs))['report_contract']
    inputs[0]['filters'].reverse()
    second = json.loads(serialize_search_report(*inputs))['report_contract']
    assert first['findings'][0]['finding_id'] == second['findings'][0]['finding_id']
    assert second['scope']['source']['filters'] == inputs[0]['filters']
