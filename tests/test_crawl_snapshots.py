"""Real local SQLite behavior and exact imported identities; no crawler runtime."""
import importlib
import json
import os
from pathlib import Path

import pytest

from tests.test_crawl_import import report, row


def module():
    return importlib.import_module('gsc_mcp.tools.crawl_snapshots')


def call(name, **kwargs):
    return json.loads(getattr(module(), name)(**kwargs))


@pytest.fixture
def store(tmp_path, monkeypatch):
    monkeypatch.setattr(module(), '_STORE_DIR', tmp_path / 'snapshots')
    return tmp_path / 'snapshots'


def test_default_preview_never_creates_storage(tmp_path, monkeypatch):
    monkeypatch.setattr(module(), '_STORE_DIR', tmp_path / 'never')
    result = call('crawl_snapshot_import', report_json=report(), site='sc-domain:example.com')
    assert result['status'] == 'preview'
    assert not (tmp_path / 'never').exists()
    assert result['snapshot']['rows_retained'] == 1
    assert result['snapshot']['indexing_status'] == 'unavailable'
    assert result['snapshot']['owner']['association'] == 'caller_declared'


def test_idempotent_storage_retains_full_inventory_and_exact_urls(store):
    urls = [f'https://example.com/é/{n}?b=2&a=1#Keep' for n in range(73)]
    raw = report([row(url=url) for url in urls])
    first = call('crawl_snapshot_import', report_json=raw, site='sc-domain:example.com', persist=True)
    again = call('crawl_snapshot_import', report_json=raw, site='sc-domain:example.com', persist=True)
    assert first['status'] == 'stored' and again['status'] == 'already_stored'
    sid = first['snapshot']['snapshot_id']
    assert again['snapshot']['snapshot_id'] == sid
    read = call('crawl_snapshot_read', site='sc-domain:example.com', snapshot_id=sid, offset=50, limit=100)
    assert [r['raw_url'] for r in read['rows']] == urls[50:]
    assert read['pagination'] == {'offset': 50, 'limit': 100, 'total': 73, 'returned': 23, 'remaining': 0}
    assert read['snapshot']['coverage']['accepted_rows'] == 73
    assert os.stat(store).st_mode & 0o777 == 0o700
    assert os.stat(store / 'inventory.sqlite3').st_mode & 0o777 == 0o600


def test_sites_and_source_options_have_separate_identity(store):
    first = call('crawl_snapshot_import', report_json=report(), site='sc-domain:example.com', persist=True)
    second = call('crawl_snapshot_import', report_json=report(), site='https://example.com/', persist=True)
    third = call('crawl_snapshot_import', report_json=report(options={'url': 'https://example.com/', 'maxDepth': 3}), site='sc-domain:example.com', persist=True)
    assert len({x['snapshot']['snapshot_id'] for x in (first, second, third)}) == 3
    foreign = call('crawl_snapshot_read', site='https://example.com/', snapshot_id=first['snapshot']['snapshot_id'])
    assert foreign['status'] == 'unavailable' and foreign['error'] == 'snapshot_not_found'


def test_scope_exclusions_and_duplicate_urls_survive_summary(store):
    raw = report([row(), row(), row(url='https://outside.example/secret')])
    saved = call('crawl_snapshot_import', report_json=raw, site='sc-domain:example.com', persist=True)
    assert saved['snapshot']['scope_excluded_rows'] == 1
    assert saved['snapshot']['duplicate_url_rows'] == 1
    sid = saved['snapshot']['snapshot_id']
    assert len(call('crawl_snapshot_read', site='sc-domain:example.com', snapshot_id=sid)['rows']) == 2


def test_quota_rejects_new_snapshot_but_not_idempotent_retry(store, monkeypatch):
    monkeypatch.setattr(module(), '_MAX_SNAPSHOTS', 1)
    first = call('crawl_snapshot_import', report_json=report(), site='sc-domain:example.com', persist=True)
    other = call('crawl_snapshot_import', report_json=report([row(status='404')]), site='sc-domain:example.com', persist=True)
    assert other['status'] == 'unavailable' and other['error'] == 'snapshot_quota'
    assert call('crawl_snapshot_import', report_json=report(), site='sc-domain:example.com', persist=True)['status'] == 'already_stored'
    assert call('crawl_snapshot_read', site='sc-domain:example.com', snapshot_id=first['snapshot']['snapshot_id'])['rows'][0]['status'] == '200'


def test_explicit_cleanup_is_site_owned_and_requires_confirmation(store):
    saved = call('crawl_snapshot_import', report_json=report(), site='sc-domain:example.com', persist=True)
    args = {'site': 'sc-domain:example.com', 'snapshot_id': saved['snapshot']['snapshot_id']}
    assert call('crawl_snapshot_delete', **args)['status'] == 'confirmation_required'
    assert call('crawl_snapshot_read', **args)['status'] == 'observed'
    assert call('crawl_snapshot_delete', **args, confirm=True)['status'] == 'deleted'
    assert call('crawl_snapshot_read', **args)['status'] == 'unavailable'


def test_malformed_and_unsupported_inputs_cannot_create_storage(store):
    for raw, producer in [('{"results":[', 'siteone'), (report(), 'unknown')]:
        result = call('crawl_snapshot_import', report_json=raw, site='sc-domain:example.com', persist=True, producer=producer)
        assert result['status'] == 'rejected'
        assert not store.exists()


def test_storage_byte_quota_does_not_partially_write(store, monkeypatch):
    monkeypatch.setattr(module(), '_MAX_STORED_BYTES', 1)
    result = call('crawl_snapshot_import', report_json=report(), site='sc-domain:example.com', persist=True)
    assert result['error'] == 'snapshot_byte_quota'
    import sqlite3
    with sqlite3.connect(store / 'inventory.sqlite3') as db:
        assert db.execute('SELECT count(*) FROM snapshots').fetchone()[0] == 0


@pytest.mark.parametrize('snapshot_id', ['../escape', 'a'*65, 'Z'*64])
def test_invalid_handles_never_create_storage(tmp_path, monkeypatch, snapshot_id):
    monkeypatch.setattr(module(), '_STORE_DIR', tmp_path / 'never')
    with pytest.raises(ValueError):
        call('crawl_snapshot_read', site='sc-domain:example.com', snapshot_id=snapshot_id)
    assert not (tmp_path / 'never').exists()


def search(rows, site='sc-domain:example.com', dimensions=None):
    return json.dumps({'site': site, 'date_range': {'start': '2026-01-01', 'end': '2026-01-28'},
        'rows': rows, '_meta': {'tool': 'get_search_analytics',
        'params': {'site': site, 'dimensions': ['page'] if dimensions is None else dimensions}}})


def test_join_preserves_explicit_zero_null_and_absent_search_row(store):
    raw = report([row(url='https://example.com/zero'), row(url='https://example.com/missing')])
    saved = call('crawl_snapshot_import', report_json=raw, site='sc-domain:example.com', persist=True)
    result = call('crawl_snapshot_join', site='sc-domain:example.com', snapshot_id=saved['snapshot']['snapshot_id'],
        search_report_json=search([{'page': 'https://example.com/zero', 'clicks': 0, 'impressions': 0, 'position': None}]))
    assert result['rows'][0]['search']['metrics']['clicks'] == 0
    assert result['rows'][0]['search']['metrics']['position'] is None
    assert result['rows'][1]['search']['status'] == 'not_in_returned_rows'
    assert result['rows'][1]['search']['metrics'] is None
    assert all(r['indexing_status'] == 'unavailable' for r in result['rows'])
    assert result['search_source']['requested_window'] == {'start': '2026-01-01', 'end': '2026-01-28'}
    assert result['search_source']['authenticated_origin'] == 'unverified'


def test_join_duplicate_and_parameter_keys_do_not_collapse(store):
    raw = report([row(url='https://example.com/A?b=2&a=1#Keep')])
    saved = call('crawl_snapshot_import', report_json=raw, site='sc-domain:example.com', persist=True)
    args = {'site': 'sc-domain:example.com', 'snapshot_id': saved['snapshot']['snapshot_id']}
    response = search([{'page': 'https://example.com/A?a=1&b=2#Keep', 'clicks': 5}])
    assert call('crawl_snapshot_join', **args, search_report_json=response)['rows'][0]['search']['status'] == 'not_in_returned_rows'
    response = search([{'page': 'https://example.com/A?b=2&a=1#Keep', 'clicks': 5}]*2)
    joined = call('crawl_snapshot_join', **args, search_report_json=response)['rows'][0]['search']
    assert joined['status'] == 'ambiguous_duplicate_key' and joined['metrics'] is None


def test_join_refuses_wrong_site_or_non_page_dimensions(store):
    saved = call('crawl_snapshot_import', report_json=report(), site='sc-domain:example.com', persist=True)
    args = {'site': 'sc-domain:example.com', 'snapshot_id': saved['snapshot']['snapshot_id']}
    for response in [search([], site='sc-domain:outside.example'), search([], dimensions=['page', 'query']),
                     '{"rows":[],"rows":[]}']:
        joined = call('crawl_snapshot_join', **args, search_report_json=response)
        assert joined['status'] == 'rejected' and 'rows' not in joined


def test_link_join_discloses_existing_path_aggregation_and_sample(store):
    url = 'https://example.com/A?b=2&a=1#keep'
    saved = call('crawl_snapshot_import', report_json=report([row(url=url)]), site='sc-domain:example.com', persist=True)
    link = json.dumps({'site': 'sc-domain:example.com', 'pages_crawled': 2, 'pages_failed': 1,
        'orphan_candidates': [{'url': url, 'path': '/A', 'body_inbound': 0, 'demoted_inbound': 1}],
        '_meta': {'tool': 'link_equity_map', 'params': {'site': 'sc-domain:example.com', 'days': 90}}})
    joined = call('crawl_snapshot_join', site='sc-domain:example.com', snapshot_id=saved['snapshot']['snapshot_id'], link_report_json=link)
    assert joined['link_source']['normalization'] == 'Path only; query/fragment discarded and trailing slash stripped by producer.'
    assert joined['link_source']['collected_at'] is None
    assert joined['rows'][0]['links']['records'][0]['category'] == 'orphan_candidates'
    assert joined['rows'][0]['links']['site_wide_orphan_status'] == 'unavailable'
    assert joined['rows'][0]['search']['status'] == 'unavailable'


def test_symlink_store_refuses_writing_other_directory(store, tmp_path):
    target = tmp_path / 'outside'
    target.mkdir()
    store.symlink_to(target, target_is_directory=True)
    result = call('crawl_snapshot_import', report_json=report(), site='sc-domain:example.com', persist=True)
    assert result['status'] == 'unavailable'
    assert list(target.iterdir()) == []


def test_corrupted_snapshot_payload_is_unavailable_instead_of_trusted_empty(store):
    import sqlite3
    saved = call('crawl_snapshot_import', report_json=report(), site='sc-domain:example.com', persist=True)
    sid = saved['snapshot']['snapshot_id']
    with sqlite3.connect(store / 'inventory.sqlite3') as db:
        db.execute('UPDATE snapshots SET payload=? WHERE id=?', ('{}', sid))
    assert call('crawl_snapshot_read', site='sc-domain:example.com', snapshot_id=sid)['status'] == 'unavailable'


@pytest.mark.parametrize('metric', [-1, True, 'missing', float('inf')])
def test_invalid_join_metric_is_not_coerced_to_zero(store, metric):
    saved = call('crawl_snapshot_import', report_json=report(), site='sc-domain:example.com', persist=True)
    result = call('crawl_snapshot_join', site='sc-domain:example.com', snapshot_id=saved['snapshot']['snapshot_id'],
        search_report_json=search([{'page': 'https://example.com/', 'clicks': metric}]))
    assert result['status'] == 'rejected'


def test_actual_public_fixture_retains_all_rows_and_no_command_or_certificate(store):
    raw = (Path(__file__).parent / 'fixtures/siteone/public-export-subset.json').read_text()
    saved = call('crawl_snapshot_import', report_json=raw, site='sc-domain:crawler.siteone.io', persist=True)
    assert saved['snapshot']['rows_retained'] == 73
    result = call('crawl_snapshot_read', site='sc-domain:crawler.siteone.io', snapshot_id=saved['snapshot']['snapshot_id'], limit=100)
    assert len(result['rows']) == 73
    assert 'certificate' not in json.dumps(result).lower() and 'command' not in result['snapshot']['source']


def test_snapshot_failure_status_has_unavailable_evidence(store):
    result = call('crawl_snapshot_read', site='sc-domain:example.com', snapshot_id='a'*64)
    assert result['_meta']['evidence']['fields']['/status']['basis'] is None
    assert not store.exists()
