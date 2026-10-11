"""Identity and missing-data qualification, not a live supplier comparison."""
import copy

import pytest

from tests.test_serpapi_provider import provider, report, request


@pytest.mark.parametrize('field,value', [('q', 'different'), ('gl', 'us'), ('hl', 'en'),
                                        ('device', 'mobile'), ('engine', 'bing'),
                                        ('google_domain', 'google.fr')])
def test_other_context_never_becomes_equivalent_google_observation(field, value):
    raw = report()
    raw['search_parameters'][field] = value
    result = provider().normalize_response(raw, request(), received_at='2026-10-11T13:01:00Z')
    assert result['status'] == 'mismatch'
    assert field in result['context_mismatches']
    assert result['effective'][field] == value


@pytest.mark.parametrize('missing', ['gl', 'hl', 'device', 'q', 'engine', 'google_domain'])
def test_missing_context_is_unavailable_not_requested_default(missing):
    raw = report()
    del raw['search_parameters'][missing]
    result = provider().normalize_response(raw, request(), received_at='2026-10-11T13:01:00Z')
    assert result['status'] == 'partial' and missing in result['missing_context']
    assert missing not in result['effective']


def test_organic_absence_is_not_zero_and_unknown_features_survive():
    raw = report()
    del raw['organic_results']
    before = copy.deepcopy(raw)
    result = provider().normalize_response(raw, request(), received_at='2026-10-11T13:01:00Z')
    assert result['status'] == 'partial' and result['organic_results'] is None
    assert result['raw']['unknown_feature'] == before['unknown_feature']
    assert raw == before


def test_location_requested_and_used_are_kept_separate():
    p = provider()
    req = p.SearchRequest('café + guide %2B', location='Paris, France')
    raw = report()
    raw['search_parameters'].update(location_requested='Paris, France', location_used='Paris,Ile-de-France,France')
    result = p.normalize_response(raw, req, received_at='2026-10-11T13:01:00Z')
    assert result['status'] == 'success'
    assert result['effective']['location_used'] == 'Paris,Ile-de-France,France'
    assert result['requested']['location'] == 'Paris, France'


def test_no_cache_flag_never_claims_provider_cache_hit():
    p = provider()
    result = p.normalize_response(report(), p.SearchRequest('café + guide %2B', fresh=True),
                                  received_at='2026-10-11T13:01:00Z')
    assert result['provider_cache'] == 'bypass_requested'
    assert result['provider_created_at'] == '2026-10-11 13:00:00 UTC'


@pytest.mark.parametrize('metadata', [
    {'id': ['not-an-id'], 'created_at': '2026-10-11 13:00:00 UTC'},
    {'id': 'synthetic', 'created_at': {'date': 'unknown'}},
    {'id': 'synthetic', 'created_at': 'not-a-date'},
])
def test_invalid_metadata_is_not_a_dated_complete_observation(metadata):
    raw = report(search_metadata={'status': 'Success', **metadata})
    result = provider().normalize_response(raw, request(), received_at='2026-10-11T13:01:00Z')
    assert result['status'] == 'partial'
    assert result['search_id'] is None or result['provider_created_at'] is None
    assert result['raw']['search_metadata'] == raw['search_metadata']
