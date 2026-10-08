"""Issue 23 boundaries exercise the real breakdown against a fake Google transport."""
import json
import os
import subprocess
import sys
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest


EVENT = {
    'site': 'sc-domain:example.com', 'url': 'https://example.com/article',
    'changed_at': '2026-01-08T12:00:00-08:00', 'timezone': 'America/Los_Angeles',
    'description': 'Caller reports a heading update.', 'revision': 'caller-revision',
}


@pytest.fixture
def run(monkeypatch):
    def call(responder=None, after_clicks=15, **options):
        from gsc_mcp.tools import change_impact, search_breakdown

        class Clock(datetime):
            @classmethod
            def now(cls, tz=None):
                return datetime(2026, 3, 1, 12, tzinfo=timezone.utc).astimezone(tz)

        monkeypatch.setattr(change_impact, 'datetime', Clock)
        calls = []

        def query(siteUrl, body):
            calls.append({'site': siteUrl, **deepcopy(body)})

            def execute():
                if responder:
                    response = responder(body)
                    if response is not None:
                        return response
                baseline = body['startDate'] == '2026-01-01'
                if body.get('dimensions') == ['date']:
                    start, end = date.fromisoformat(body['startDate']), date.fromisoformat(body['endDate'])
                    rows = [metric_row((start + timedelta(days=i)).isoformat())
                            for i in range((end - start).days + 1)]
                else:
                    key = body.get('dimensions', [None])[0]
                    rows = [metric_row('https://example.com/article' if key == 'page' else key,
                                       10 if baseline else after_clicks)]
                return {'rows': rows, 'responseAggregationType': 'byPage'}

            return SimpleNamespace(execute=execute)

        monkeypatch.setattr(search_breakdown, 'get_searchconsole_service',
                            lambda: SimpleNamespace(searchanalytics=lambda: SimpleNamespace(query=query)))
        params = dict(event=deepcopy(EVENT), baseline_start='2026-01-01', baseline_end='2026-01-07',
                      comparison_start='2026-01-09', comparison_end='2026-01-15')
        params.update(options)
        return json.loads(change_impact.seo_change_impact(**params)), calls

    return call


def metric_row(key, clicks=10, impressions=100):
    return {'keys': [] if key is None else [key], 'clicks': clicks,
            'impressions': impressions, 'ctr': .99, 'position': 2}


@pytest.mark.parametrize(('after_clicks', 'delta'), [(15, 5), (4, -6), (10, 0)])
def test_descriptive_change_preserves_event_and_coverage(run, after_clicks, delta):
    out, calls = run(after_clicks=after_clicks, concurrent_changes=['Seasonal campaign'])
    assert out['comparison']['status'] == 'observed'
    assert out['comparison']['descriptive_delta']['clicks'] == delta
    assert out['comparison']['before']['ctr'] == .1
    assert out['comparison']['after']['ctr'] == after_clicks / 100
    assert out['event']['changed_at'] == EVENT['changed_at']
    assert out['event']['provenance'] == 'caller_declared'
    assert out['event']['google_event_date'] == '2026-01-08'
    assert out['event']['revision'] == 'caller-revision'
    assert out['concurrent_changes'] == ['Seasonal campaign']
    assert out['persistence']['status'] == 'not_persisted'
    assert out['attribution']['causal_effect'] is None
    assert out['search_evidence']['periods']['baseline']['observed_day_count'] == 7
    assert out['search_evidence']['breakdowns']['page']['baseline_coverage']['all_source_rows_guaranteed'] is False
    assert out['collection']['completed_at']
    assert out['_meta']['tool'] == 'seo_change_impact'
    assert out['_meta']['sources']['google']['site'] == EVENT['site']
    assert len(calls) <= 20
    assert all(c['dataState'] == 'final' for c in calls)
    assert all(c['dimensionFilterGroups'][0]['filters'][-1] ==
               {'dimension': 'page', 'operator': 'equals', 'expression': EVENT['url']} for c in calls)


@pytest.mark.parametrize(('section', 'reason'), [('baseline', 'insufficient_baseline_data'),
                                               ('comparison', 'insufficient_post_change_data')])
def test_missing_aggregate_is_unavailable_not_zero(run, section, reason):
    def responder(body):
        if not body.get('dimensions') and (body['startDate'] == '2026-01-01') == (section == 'baseline'):
            return {'rows': [], 'responseAggregationType': 'byPage'}
    out, _ = run(responder=responder)
    assert out['comparison']['status'] == 'unavailable'
    assert reason in out['comparison']['reasons']
    assert out['comparison']['descriptive_delta']['clicks'] is None
    assert out['comparison']['before' if section == 'baseline' else 'after']['clicks'] is None


def test_missing_date_and_incomplete_provider_marker_suppress_delta(run):
    def responder(body):
        if body.get('dimensions') == ['date'] and body['startDate'] == '2026-01-09':
            return {'rows': [metric_row('2026-01-09')], 'responseAggregationType': 'byPage',
                    'metadata': {'first_incomplete_date': '2026-01-10'}}
    out, _ = run(responder=responder)
    assert out['comparison']['status'] == 'unavailable'
    assert 'insufficient_post_change_data' in out['comparison']['reasons']
    assert out['comparison']['descriptive_delta']['clicks'] is None
    assert out['search_evidence']['periods']['comparison']['first_incomplete_date'] == '2026-01-10'
    assert '2026-01-15' in out['search_evidence']['periods']['comparison']['missing_requested_dates']


def test_too_recent_window_returns_policy_and_does_not_query(run):
    event = {**EVENT, 'changed_at': '2026-02-25T12:00:00-08:00'}
    out, calls = run(event=event, baseline_start='2026-02-18', baseline_end='2026-02-24',
                     comparison_start='2026-02-26', comparison_end='2026-03-04')
    assert out['comparison']['reasons'] == ['insufficient_post_change_data']
    assert out['search_evidence'] is None
    assert out['maturity_policy']['latest_eligible_date'] == '2026-02-26'
    assert out['maturity_policy']['provider_finalization_verified'] is False
    assert out['comparison']['before'] is None
    assert out['comparison']['descriptive_delta']['clicks'] is None
    assert calls == []


def test_event_day_uses_google_timezone_not_caller_day(run):
    event = {**EVENT, 'changed_at': '2026-01-09T01:00:00+01:00', 'timezone': 'Europe/Paris'}
    out, _ = run(event=event)
    assert out['event']['google_event_date'] == '2026-01-08'
    assert out['event']['timezone'] == 'Europe/Paris'


@pytest.mark.parametrize('options', [
    {'baseline_end': '2026-01-08', 'baseline_start': '2026-01-02'},
    {'comparison_start': '2026-01-08', 'comparison_end': '2026-01-14'},
    {'comparison_end': '2026-01-16'}, {'align_weekdays': True},
    {'event': {**EVENT, 'changed_at': '2026-01-08T12:00:00'}},
    {'event': {**EVENT, 'timezone': 'Europe/Paris'}},
    {'event': {**EVENT, 'provenance': 'observed_deployment'}},
    {'event': {**EVENT, 'url': 'https://example.com.evil.test/article'}},
    {'event': {**EVENT, 'site': 'https://example.com/docs/'}},
    {'event': {**EVENT, 'url': 'https://user:secret@example.com/article'}},
    {'event': {**EVENT, 'url': 'https://example.com/article#part'}},
    {'filters': [{'dimension': 'page', 'operator': 'equals', 'expression': 'https://example.com/other'}]},
    {'filters': [{'dimension': 'country', 'operator': 'bogus', 'expression': 'fra'}]},
    {'concurrent_changes': 'not a list'}, {'row_limit': True}, {'max_requests': 5},
    {'page_mapping': {'baseline_url': EVENT['url'], 'comparison_url': 'https://evil.test/new'}},
])
def test_invalid_or_incompatible_inputs_fail_before_provider(run, options):
    with pytest.raises(ValueError):
        run(**options)


def test_weekday_alignment_and_copied_filters(run):
    filters = [{'dimension': 'country', 'operator': 'equals', 'expression': 'fra'}]
    out, calls = run(comparison_start='2026-01-15', comparison_end='2026-01-21',
                     align_weekdays=True, filters=filters)
    assert out['windows']['weekday_aligned'] is True
    assert out['search_evidence']['filters'][0] == filters[0]
    assert filters == [{'dimension': 'country', 'operator': 'equals', 'expression': 'fra'}]
    assert all(c['dimensionFilterGroups'][0]['filters'] == out['search_evidence']['filters'] for c in calls)


def test_explicit_changed_url_mapping_retains_combined_scope_and_unmatched_rows(run):
    mapping = {'baseline_url': EVENT['url'], 'comparison_url': 'https://example.com/new'}
    def responder(body):
        if body.get('dimensions') == ['page']:
            key = mapping['baseline_url'] if body['startDate'] == '2026-01-01' else mapping['comparison_url']
            return {'rows': [metric_row(key)], 'responseAggregationType': 'byPage'}
    out, calls = run(responder=responder, page_mapping=mapping)
    assert out['page_mapping']['provenance'] == 'caller_declared'
    assert out['page_mapping']['comparison_url'] == mapping['comparison_url']
    assert out['comparison']['scope'] == 'combined_mapped_urls_in_both_windows'
    pages = out['search_evidence']['breakdowns']['page']
    assert pages['matched'] == []
    assert pages['baseline_only'][0]['delta'] is None
    assert pages['comparison_only'][0]['delta'] is None
    assert all(c['dimensionFilterGroups'][0]['filters'][-1]['operator'] == 'includingRegex' for c in calls)


def test_aggregation_mismatch_is_unavailable(run):
    def responder(body):
        if not body.get('dimensions') and body['startDate'] == '2026-01-09':
            return {'rows': [metric_row(None, 15)], 'responseAggregationType': 'byProperty'}
    out, _ = run(responder=responder)
    assert 'incompatible_aggregation' in out['comparison']['reasons']
    assert out['comparison']['descriptive_delta']['clicks'] is None


def test_zero_observed_counts_keep_undefined_ctr_unavailable(run):
    def responder(body):
        if not body.get('dimensions'):
            return {'rows': [metric_row(None, 0, 0)], 'responseAggregationType': 'byPage'}
    out, _ = run(responder=responder)
    assert out['comparison']['status'] == 'observed'
    assert out['comparison']['descriptive_delta']['clicks'] == 0
    assert out['comparison']['before']['ctr'] is None
    assert out['comparison']['descriptive_delta']['ctr_percentage_points'] is None
    assert out['comparison']['before']['unavailable_metrics']['ctr']


def test_missing_provider_metric_keeps_it_unknown(run):
    def responder(body):
        if not body.get('dimensions') and body['startDate'] == '2026-01-09':
            return {'rows': [{'impressions': 100}], 'responseAggregationType': 'byPage'}
    out, _ = run(responder=responder)
    assert out['comparison']['status'] == 'unavailable'
    assert out['comparison']['after']['clicks'] is None
    assert out['comparison']['descriptive_delta']['clicks'] is None


def test_provider_errors_are_retained_without_sensitive_exception_text(run):
    def responder(body):
        raise RuntimeError('private credential SECRET')
    out, _ = run(responder=responder)
    assert out['comparison']['status'] == 'unavailable'
    assert out['search_evidence']['baseline_totals']['baseline']['fetch_error'] == 'RuntimeError'
    assert 'SECRET' not in json.dumps(out)


def test_valid_iana_event_works_without_system_timezone_database():
    # A fresh process excludes both the system TZPATH and any cached ZoneInfo.
    # A future window exercises timezone parsing without requesting Google data.
    script = '''
import json
import zoneinfo
from datetime import datetime, timezone
from gsc_mcp.tools.change_impact import seo_change_impact

assert zoneinfo.TZPATH == ()
year = datetime.now(timezone.utc).year + 2
event = {
    'site': 'sc-domain:example.com', 'url': 'https://example.com/article',
    'changed_at': f'{year}-01-08T12:00:00+01:00', 'timezone': 'Europe/Paris',
    'description': 'Caller reports a heading update.',
}
print(seo_change_impact(event, f'{year}-01-01', f'{year}-01-07',
                        f'{year}-01-09', f'{year}-01-15'))
'''
    environment = {**os.environ, 'PYTHONTZPATH': '',
                   'PYTHONPATH': str(Path(__file__).resolve().parents[1] / 'src')}
    process = subprocess.run([sys.executable, '-c', script], env=environment,
                             capture_output=True, text=True, timeout=30)
    assert process.returncode == 0, process.stderr
    out = json.loads(process.stdout)
    assert out['event']['timezone'] == 'Europe/Paris'
    assert out['event']['google_event_date'].endswith('-01-08')
    assert out['comparison']['reasons'] == ['insufficient_post_change_data']
    assert out['search_evidence'] is None
