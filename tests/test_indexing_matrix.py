"""A supplied observation matrix must never infer a current indexing boolean."""
import importlib
import json

import pytest

from tests.test_crawl_import import report, row
from tests.test_crawl_snapshots import call, store

SITE = 'sc-domain:example.com'
URL = 'https://example.com/A?b=2&a=1'


def source(tool, data, **params):
    return {'report': {**data, '_meta': {'tool': tool, 'params': params}}}


def matrix(reports=None, **kwargs):
    module = importlib.import_module('gsc_mcp.tools.indexing_matrix')
    return json.loads(module.indexing_evidence_matrix(SITE, [URL], json.dumps(reports or []), **kwargs))


def test_zero_and_absent_search_never_establish_indexing():
    r = source('get_search_analytics', {'site': SITE, 'date_range': {'start': '2026-01-01', 'end': '2026-01-28'},
        'rows': [{'page': URL, 'clicks': 0, 'impressions': 0}]}, site=SITE, dimensions=['page'])
    for response in [matrix([r]), matrix([])]:
        assert response['rows'][0]['current_indexing_status'] == 'unknown'
        assert response['rows'][0]['inspection'] == []
        assert response['sample_scope'] == 'Explicit selected URLs only; no whole-property extrapolation.'
    assert matrix([r])['rows'][0]['search'][0]['value']['clicks'] == 0


def test_unknown_inspection_category_is_not_used_as_provider_state():
    r = source('inspect_url', {'url': URL, 'verdict': 'UNKNOWN', 'category': 'not_indexed'}, site=SITE, url=URL)
    response = matrix([r])
    assert response['rows'][0]['inspection'][0]['availability'] == 'unavailable'
    assert 'category' not in response['rows'][0]['inspection'][0]['value']
    assert response['rows'][0]['current_indexing_status'] == 'unknown'


def test_contradictory_inspection_and_html_preserve_both_times():
    inspection = source('inspect_url', {'url': URL, 'verdict': 'PASS', 'google_canonical': URL, 'last_crawl': '2026-01-01T00:00:00Z'}, site=SITE, url=URL)
    inspection['collected_at'] = '2026-01-02T00:00:00Z'
    html = source('page_technical_audit', {'url': URL, 'findings': {'status_code': 200, 'meta_robots': 'noindex', 'canonical': 'https://example.com/B', 'robots_txt_blocks_googlebot': None}}, url=URL)
    html['collected_at'] = '2026-02-01T00:00:00Z'
    result = matrix([inspection, html])
    item = result['rows'][0]
    assert item['inspection'][0]['value']['verdict'] == 'PASS'
    assert item['html'][0]['value']['meta_robots'] == 'noindex'
    assert item['html'][0]['value']['robots_txt_blocks_googlebot'] is None
    kinds = {r['kind'] for r in item['contradictions']}
    assert {'reported_inspection_pass_vs_noindex', 'reported_google_vs_html_canonical'} <= kinds
    assert all(c['collection_order'] == 'caller_declared_unverified' for c in item['contradictions'])
    assert result['sources'][0]['collected_at'] == '2026-01-02T00:00:00Z'
    assert result['sources'][1]['collected_at'] == '2026-02-01T00:00:00Z'
    assert item['current_indexing_status'] == 'unknown'


def test_sitemap_declaration_and_canonical_difference_remain_conditional():
    inventory = source('caller_inventory', {'site': SITE, 'kind': 'sitemap', 'urls': [URL]}, site=SITE)
    html = source('page_technical_audit', {'url': URL, 'findings': {'status_code': 200, 'canonical': 'https://example.com/B'}}, url=URL)
    item = matrix([inventory, html])['rows'][0]
    assert item['sitemap'][0]['availability'] == 'caller_declared'
    assert item['contradictions'][0]['kind'] == 'declared_sitemap_vs_html_canonical'


def test_logs_are_path_candidates_not_bot_or_indexing_proof():
    logs = source('crawl_log_audit', {'site': SITE, 'status': 'partial', 'observed_window': {'start': '2026-01-01T00:00:00Z', 'end': '2026-01-02T00:00:00Z'},
        'paths': [{'path': '/A', 'origin': 'relative_to_declared_site', 'path_hash': 'sample', 'requests': 2, 'status_counts': {'200': 2}}]}, site=SITE)
    item = matrix([logs])['rows'][0]
    assert item['logs'][0]['relation'] == 'path_candidate_queries_stripped'
    assert item['rendering_status'] == 'unavailable'
    assert item['current_indexing_status'] == 'unknown'


def test_snapshot_import_only_observes_raw_status_not_current_indexing(store):
    sid = call('crawl_snapshot_import', report_json=report([row(url=URL)]), site=SITE, persist=True)['snapshot']['snapshot_id']
    response = matrix([], snapshot_id=sid)
    assert response['rows'][0]['crawl'][0]['value']['status'] == '200'
    assert response['rows'][0]['current_indexing_status'] == 'unknown'
    assert response['sources'][0]['scope']['selection'] == 'unknown'


def test_foreign_inspection_and_invalid_dimensions_fail_without_mixing():
    for r in [source('inspect_url', {'url': URL, 'verdict': 'PASS'}, site='sc-domain:outside.example', url=URL),
              source('get_search_analytics', {'site': SITE, 'rows': []}, site=SITE, dimensions=['query']),
              source('unknown_tool', {'url': URL}, url=URL)]:
        result = matrix([r])
        assert result['status'] == 'rejected' and 'rows' not in result


def test_redirect_soft404_and_fetch_error_do_not_overwrite_other_evidence():
    inspect = source('inspect_url', {'url': URL, 'verdict': 'FAIL', 'coverage_state': 'Soft 404', 'page_fetch_state': 'SOFT_404'}, site=SITE, url=URL)
    redirect = source('page_technical_audit', {'url': URL, 'findings': {'status_code': 301, 'redirect_target': '/B'}}, url=URL)
    failed = source('page_technical_audit', {'url': URL, 'error': 'timeout', 'verdict': 'fetch_error'}, url=URL)
    item = matrix([inspect, redirect, failed])['rows'][0]
    assert item['inspection'][0]['value']['page_fetch_state'] == 'SOFT_404'
    assert item['html'][0]['value']['status_code'] == 301
    assert item['html'][1]['availability'] == 'unavailable'
    assert item['current_indexing_status'] == 'unknown'


def test_url_report_and_input_caps_are_visible():
    module = importlib.import_module('gsc_mcp.tools.indexing_matrix')
    with pytest.raises(ValueError):
        module.indexing_evidence_matrix(SITE, [URL]*51)
    assert matrix([source('inspect_url', {'url': URL, 'verdict': 'PASS'}, site=SITE)]*21)['error'] == 'report_limit'
    assert matrix(reports=[] , max_reports=1)['coverage']['reports'] == 0
    result = json.loads(module.indexing_evidence_matrix(SITE, [URL], 'x' * 2097153))
    assert result['error'] == 'input_bytes_limit'


def test_noindex_spaces_and_cell_omissions_are_not_hidden():
    inspection = source('inspect_url', {'url': URL, 'verdict': 'PASS'}, site=SITE, url=URL)
    html = source('page_technical_audit', {'url': URL, 'findings': {'status_code': 200, 'meta_robots': 'index, noindex , follow'}}, url=URL)
    assert matrix([inspection, html])['rows'][0]['contradictions'][0]['kind'] == 'reported_inspection_pass_vs_noindex'
    item = matrix([inspection]*21, max_reports=30)['rows'][0]
    assert len(item['inspection']) == 20 and item['omitted_cells'] == 1


def test_wrong_timestamps_and_credential_urls_are_rejected():
    r = source('inspect_url', {'url': URL, 'verdict': 'PASS'}, site=SITE, url=URL)
    r['collected_at'] = '2026-01-01'
    assert matrix([r])['status'] == 'rejected'
    r.pop('collected_at')
    r['report']['google_canonical'] = 'https://user:secret@example.com/B'
    assert matrix([r])['status'] == 'rejected'


def test_literal_canonical_chain_is_bounded_to_selected_observations():
    module = importlib.import_module('gsc_mcp.tools.indexing_matrix')
    other = 'https://example.com/B'
    reports = [source('page_technical_audit', {'url': URL, 'findings': {'status_code': 200, 'canonical': other}}, url=URL),
               source('page_technical_audit', {'url': other, 'findings': {'status_code': 200, 'canonical': 'https://example.com/C'}}, url=other)]
    result = json.loads(module.indexing_evidence_matrix(SITE, [URL, other], json.dumps(reports)))
    chain = result['rows'][0]['canonical_chain']
    assert [hop['to'] for hop in chain['hops']] == [other, 'https://example.com/C']
    assert chain['status'] == 'out_of_selected_sample'
    assert chain['google_selection_status'] == 'unavailable'


@pytest.mark.parametrize('targets, expected', [(1, 'reported_cycle'), (6, 'hop_limit')])
def test_canonical_cycles_and_long_chains_do_not_fetch_or_claim_selection(targets, expected):
    module = importlib.import_module('gsc_mcp.tools.indexing_matrix')
    urls = [f'https://example.com/{i}' for i in range(targets + 1)]
    reports = [source('page_technical_audit', {'url': url, 'findings': {'status_code': 200,
                'canonical': urls[(i + 1) % len(urls)]}}, url=url) for i, url in enumerate(urls)]
    result = json.loads(module.indexing_evidence_matrix(SITE, urls, json.dumps(reports)))
    assert result['rows'][0]['canonical_chain']['status'] == expected
    assert len(result['rows'][0]['canonical_chain']['hops']) <= 5
    assert result['coverage']['provider_requests'] == 0
    assert result['rows'][0]['rendering_status'] == 'unavailable'
