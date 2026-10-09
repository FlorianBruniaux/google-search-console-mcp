"""Inventory absence and measured-field comparison are distinct contracts."""
import json

import pytest

from tests.test_crawl_import import report, row
from tests.test_crawl_snapshots import call, module, store


def save(raw):
    return call('crawl_snapshot_import', report_json=raw, site='sc-domain:example.com', persist=True)['snapshot']['snapshot_id']


def diff(a, b, **kwargs):
    return call('crawl_diff', site='sc-domain:example.com', baseline_id=a, comparison_id=b, **kwargs)


def test_partial_inventory_absence_never_means_deleted_or_unindexed(store):
    a = save(report([row(url='https://example.com/A'), row(url='https://example.com/B')]))
    b = save(report([row(url='https://example.com/A')], error=['fetch failed for B']))
    result = diff(a, b)
    assert result['counts']['absent_from_comparison_inventory'] == 1
    assert result['changes'][0]['kind'] == 'absent_from_comparison_inventory'
    assert result['changes'][0]['raw_url'] == 'https://example.com/B'
    assert result['site_deletion_status'] == 'unavailable'
    assert result['indexing_status'] == 'unavailable'
    assert result['coverage']['comparison']['source_errors'] == 1


def test_same_method_field_changes_preserve_both_sources(store):
    a = save(report([row(status='200', size=30)]))
    b = save(report([row(status='404', size=0)]))
    result = diff(a, b)
    changed = {item['field']: item for item in result['changes']}
    assert changed['status']['before'] == '200' and changed['status']['after'] == '404'
    assert changed['size']['before'] == 30 and changed['size']['after'] == 0
    assert changed['status']['baseline_snapshot_id'] == a
    assert changed['status']['comparison_snapshot_id'] == b
    assert changed['status']['kind'] == 'observed_field_difference'
    assert result['comparability']['collection_order'] == 'unverified'


@pytest.mark.parametrize('change', [
    {'options': {'url': 'https://example.com/', 'maxDepth': 3}},
    {'crawler': {'name': 'SiteOne', 'version': '2.0', 'executedAt': '2026-01-01'}},
])
def test_changed_config_or_version_cannot_confirm_field_change(store, change):
    a = save(report([row(status='200')]))
    b = save(report([row(status='404')], **change))
    result = diff(a, b)
    assert result['comparability']['field_comparison'] == 'unavailable'
    assert result['counts']['observed_field_differences'] == 0
    assert result['changes'] == []
    assert result['comparability']['reasons']


def test_exact_url_keys_duplicates_and_null_fields_stay_distinct(store):
    u = 'https://example.com/é?b=2&a=1#Keep'
    a = save(report([row(url=u), row(url=u), row(url='https://example.com/null', cacheLifetime=None)]))
    b = save(report([row(url='https://example.com/é?a=1&b=2#Keep'), row(url='https://example.com/null', cacheLifetime=0)]))
    result = diff(a, b)
    assert result['counts']['ambiguous_raw_urls'] == 1
    assert result['counts']['only_in_comparison_inventory'] == 1
    assert not any(c.get('field') == 'cacheLifetime' for c in result['changes'])
    assert result['counts']['unavailable_matched_field_pairs'] >= 1


def test_bounded_large_diff_has_visible_omissions_and_deterministic_order(store):
    a = save(report([row(url=f'https://example.com/{n}') for n in range(200)]))
    b = save(report([]))
    result = diff(a, b, limit=3)
    assert len(result['changes']) == 3
    assert result['counts']['omitted_changes'] == 197
    assert result['changes'] == diff(a, b, limit=3)['changes']
    assert [c['raw_url'] for c in result['changes']] == ['https://example.com/0', 'https://example.com/1', 'https://example.com/10']


def test_missing_snapshot_is_unavailable_not_empty_diff(store):
    a = save(report())
    assert diff(a, 'a'*64)['status'] == 'unavailable'


@pytest.mark.parametrize('limit', [0, 101, True])
def test_invalid_diff_limit_is_rejected_before_storage(store, limit):
    with pytest.raises(ValueError):
        diff('a'*64, 'b'*64, limit=limit)
    assert not store.exists()


def test_named_ci_policy_never_passes_unknown_or_incompatible_fields(store):
    a = save(report([row(status='200', cacheLifetime=None)]))
    b = save(report([row(status='404', cacheLifetime=0)]))
    changed = diff(a, b, policy_fields=['status'])
    assert changed['policy']['status'] == 'field_change_detected'
    assert changed['policy']['scope'] == 'Matched retained unique raw URLs only.'
    assert diff(a, b, policy_fields=['cacheLifetime'])['policy']['status'] == 'undetermined'
    assert diff(a, a, policy_fields=['status'])['policy']['status'] == 'no_field_change_detected'
    wrong = save(report([row(status='200')], options={'url': 'https://example.com/', 'maxDepth': 3}))
    assert diff(a, wrong, policy_fields=['status'])['policy']['status'] == 'undetermined'


def test_unknown_policy_field_refused_before_storage(store):
    with pytest.raises(ValueError):
        diff('a'*64, 'b'*64, policy_fields=['indexed'])
    assert not store.exists()


def test_failed_fetch_placeholders_cannot_become_page_field_changes(store):
    a = save(report([row(status='fetch_error', size=0, elapsedTime=0)]))
    b = save(report([row(status='200', size=30, elapsedTime=0.005)]))
    result = diff(a, b, policy_fields=['size'])
    assert result['changes'] == []
    assert result['policy']['status'] == 'undetermined'
