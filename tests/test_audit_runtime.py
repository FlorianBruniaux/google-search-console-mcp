"""Behavioral contracts for an opt-in, shared read-only audit run."""
import importlib
import json
from concurrent.futures import ThreadPoolExecutor

import pytest


def runtime():
    assert importlib.util.find_spec('gsc_mcp.audit_runtime'), 'audit runtime is not implemented'
    return importlib.import_module('gsc_mcp.audit_runtime')


def config(tmp_path, **changes):
    return dict(run_id='case', site='sc-domain:example.com', bing_site='https://example.com/',
                ledger_path=str(tmp_path / 'run.sqlite'), max_provider_attempts=3,
                max_tool_calls=10, allowed_tools=['get_search_analytics'], **changes)


def test_failed_attempts_and_reopened_sessions_share_one_budget(tmp_path):
    api = runtime()
    one, two = api.AuditSession(config(tmp_path)), api.AuditSession(config(tmp_path))
    for session in (one, two, one):
        with session.activate():
            api.provider_attempt('google')
    with two.activate(), pytest.raises(api.AuditBudgetExceeded):
        api.provider_attempt('bing')
    assert two.status()['provider_attempts'] == 3


def test_concurrent_attempts_cannot_exceed_reservation_limit(tmp_path):
    api = runtime()
    session = api.AuditSession(config(tmp_path))
    def attempt(_):
        try:
            with session.activate(): api.provider_attempt('google')
            return True
        except api.AuditBudgetExceeded: return False
    with ThreadPoolExecutor(max_workers=8) as executor:
        assert sum(executor.map(attempt, range(20))) == 3
    assert session.status()['provider_attempts'] == 3


def test_shared_observation_is_cached_without_mutation_or_reacquisition(tmp_path):
    api = runtime()
    from gsc_mcp.registry import TOOLS
    session = api.AuditSession(config(tmp_path))
    calls = []
    def source(site, days=28, dimensions=None, row_limit=1000):
        calls.append(site)
        api.provider_attempt('google')
        return json.dumps({'site': site, 'clicks': None, '_meta': {'sources': {'site': site}}})
    with pytest.MonkeyPatch.context() as patch:
        patch.setitem(TOOLS, 'get_search_analytics', source)
        first = json.loads(session.call('get_search_analytics', {'site': 'sc-domain:example.com'}))
        first['clicks'] = 99
        second = json.loads(session.call('get_search_analytics', {'site': 'sc-domain:example.com'}))
    assert second['clicks'] is None
    assert calls == ['sc-domain:example.com']
    assert session.status()['provider_attempts'] == 1


def test_scope_write_and_changed_run_configuration_are_rejected_before_calls(tmp_path):
    api = runtime()
    session = api.AuditSession(config(tmp_path))
    with pytest.raises(ValueError, match='scope'):
        session.call('get_search_analytics', {'site': 'sc-domain:other.test'})
    with pytest.raises(ValueError, match='allowed'):
        session.call('submit_url', {'url': 'https://example.com/'})
    changed = config(tmp_path); changed['max_provider_attempts'] = 9
    with pytest.raises(ValueError, match='configuration'):
        api.AuditSession(changed)
    assert session.status()['provider_attempts'] == 0


def test_physical_google_and_ga4_boundaries_stop_before_transport(tmp_path):
    api = runtime()
    session = api.AuditSession(config(tmp_path))
    class Request:
        def execute(self): return {'rows': []}
    class Client:
        def report(self, request, *, retry):
            assert retry is None
            return {'count': 0}
    with session.activate():
        assert api.execute_google(Request()) == {'rows': []}
        assert api.call_ga4(Client().report, {}) == {'count': 0}
        api.provider_attempt('bing')
        with pytest.raises(api.AuditBudgetExceeded):
            api.execute_google(Request())
    assert session.status()['provider_attempts'] == 3


def test_google_retry_is_counted_at_each_execute(tmp_path, mock_gsc_service, monkeypatch):
    from googleapiclient.errors import HttpError
    import httplib2
    from gsc_mcp.tools.analytics import get_search_analytics
    api = runtime()
    settings = config(tmp_path); settings['max_provider_attempts'] = 1
    session = api.AuditSession(settings)
    request = mock_gsc_service.searchanalytics.return_value.query.return_value
    request.execute.side_effect = HttpError(httplib2.Response({'status': '500'}), b'{}')
    monkeypatch.setattr('gsc_mcp.tools.analytics.get_searchconsole_service', lambda: mock_gsc_service)
    monkeypatch.setattr('gsc_mcp.retry.time.sleep', lambda _: None)
    with session.activate(), pytest.raises(api.AuditBudgetExceeded):
        get_search_analytics('sc-domain:example.com')
    assert request.execute.call_count == 1
    assert session.status()['provider_attempts'] == 1


def test_bing_retry_stops_before_second_http_attempt(tmp_path, monkeypatch):
    import httpx
    from gsc_mcp.providers.bing import BingWebmasterClient
    api = runtime()
    settings = config(tmp_path); settings['max_provider_attempts'] = 1
    session = api.AuditSession(settings)
    attempts = []
    def response(request):
        attempts.append(request.url.path)
        return httpx.Response(429, json={'d': None})
    original = httpx.Client
    monkeypatch.setattr('gsc_mcp.providers.bing.httpx.Client', lambda **kwargs: original(transport=httpx.MockTransport(response), **kwargs))
    monkeypatch.setattr('gsc_mcp.providers.bing.time.sleep', lambda _: None)
    with session.activate(), pytest.raises(api.AuditBudgetExceeded):
        BingWebmasterClient('secret').read('GetQueryStats', {'siteUrl': 'https://example.com/'})
    assert len(attempts) == 1


def test_actual_ga4_tool_disables_hidden_sdk_retries(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from gsc_mcp.tools.ga4 import ga4_realtime
    api = runtime()
    session = api.AuditSession(config(tmp_path))
    calls = []
    class Client:
        def run_realtime_report(self, request, *, retry='SDK default'):
            calls.append(retry)
            return SimpleNamespace(rows=[])
    monkeypatch.setattr('gsc_mcp.tools.ga4.get_ga4_service', lambda: Client())
    with session.activate():
        result = json.loads(ga4_realtime(property_id='123'))
    assert result['count'] == 0
    assert calls == [None]
    assert session.status()['provider_attempts'] == 1


def test_ga4_scope_cannot_fall_back_to_another_property(tmp_path, monkeypatch):
    api = runtime()
    from gsc_mcp.registry import TOOLS
    settings = config(tmp_path)
    settings['allowed_tools'] = ['ga4_realtime']
    settings['ga4_property'] = '123'
    session = api.AuditSession(settings)
    def source(property_id=None, hostname=None):
        assert property_id == '123'
        return json.dumps({'property': property_id})
    monkeypatch.setitem(TOOLS, 'ga4_realtime', source)
    assert json.loads(session.call('ga4_realtime', {}))['property'] == '123'
    with pytest.raises(ValueError, match='scope'):
        session.call('ga4_realtime', {'property_id': '456'})


def test_server_audit_surface_is_read_only_and_counts_observations(tmp_path):
    import os
    import subprocess
    import sys
    settings = config(tmp_path)
    settings['allowed_tools'] = ['get_capabilities', 'indexing_evidence_matrix']
    path = tmp_path / 'config.json'
    path.write_text(json.dumps(settings))
    code = """
import json
from gsc_mcp.server import MCP_TOOLS, AUDIT_SESSION
assert set(MCP_TOOLS) == {'get_capabilities', 'indexing_evidence_matrix'}
assert AUDIT_SESSION is not None
print(json.dumps(AUDIT_SESSION.status()))
"""
    child = subprocess.run([sys.executable, '-c', code], env={**os.environ, 'GSC_MCP_AUDIT_CONFIG': str(path)}, capture_output=True, text=True)
    assert child.returncode == 0, child.stderr
    assert json.loads(child.stdout)['provider_attempts'] == 0


def test_stdio_mcp_acquisition_preserves_unknown_and_reuses_observation(tmp_path):
    import asyncio
    import os
    import sys
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    settings = config(tmp_path)
    settings['allowed_tools'] = ['get_capabilities', 'indexing_evidence_matrix']
    path = tmp_path / 'config.json'; path.write_text(json.dumps(settings))
    async def exchange():
        params = StdioServerParameters(command=sys.executable, args=['-m', 'gsc_mcp.server'],
            env={**os.environ, 'GSC_MCP_AUDIT_CONFIG': str(path), 'GSC_NO_BROWSER': '1'})
        async with stdio_client(params) as streams:
            async with ClientSession(*streams) as client:
                await client.initialize()
                assert {tool.name for tool in (await client.list_tools()).tools} == set(settings['allowed_tools'])
                args = {'site': 'https://example.com/', 'urls': ['https://example.com/page']}
                # This domain property is different from the configured one and
                # must fail through the real server before any observation.
                rejected = await client.call_tool('indexing_evidence_matrix', args)
                assert rejected.isError
                args['site'] = settings['site']
                first = await client.call_tool('indexing_evidence_matrix', args)
                second = await client.call_tool('indexing_evidence_matrix', args)
                assert not first.isError and first.content == second.content
                assert json.loads(first.content[0].text)['rows'][0]['current_indexing_status'] == 'unknown'
                caps = await client.call_tool('get_capabilities', {})
                status = json.loads(caps.content[0].text)['audit_run']
                assert status['provider_attempts'] == 0
                assert status['tool_calls'] == 2
    asyncio.run(exchange())


def test_cli_validates_entire_plan_before_any_acquisition(tmp_path):
    import subprocess
    import sys
    from pathlib import Path
    api = runtime()
    settings = config(tmp_path)
    settings['allowed_tools'] = ['indexing_evidence_matrix']
    config_path = tmp_path / 'config.json'; config_path.write_text(json.dumps(settings))
    plan = [{'tool': 'indexing_evidence_matrix', 'arguments': {'site': settings['site'], 'urls': []}},
            {'tool': 'indexing_evidence_matrix', 'arguments': {'site': 'sc-domain:other.test', 'urls': []}}]
    requests = tmp_path / 'requests.json'; requests.write_text(json.dumps(plan))
    script = Path(__file__).resolve().parents[1] / 'scripts/run_bounded_audit.py'
    result = subprocess.run([sys.executable, str(script), '--config', str(config_path), '--requests', str(requests), '--output', str(tmp_path / 'output.json')], capture_output=True, text=True)
    assert result.returncode != 0
    session = api.AuditSession(settings)
    assert session.status()['tool_calls'] == 0


def test_google_credential_replay_cannot_hide_second_http_attempt(tmp_path):
    import httplib2
    from google.auth.credentials import Credentials
    from google_auth_httplib2 import AuthorizedHttp
    from googleapiclient.http import HttpRequest
    api = runtime()
    settings = config(tmp_path); settings['max_provider_attempts'] = 1
    session = api.AuditSession(settings)
    class CredentialsFixture(Credentials):
        def __init__(self): super().__init__(); self.token = 'synthetic'
        def refresh(self, request): self.token = 'refreshed-synthetic'
    class Transport:
        calls = 0
        def request(self, *args, **kwargs):
            self.calls += 1
            return httplib2.Response({'status': '401' if self.calls == 1 else '200'}), b'{}'
    transport = Transport()
    request = HttpRequest(AuthorizedHttp(CredentialsFixture(), http=transport), lambda *_: {}, 'https://example.com/api')
    with session.activate(), pytest.raises(api.AuditBudgetExceeded): api.execute_google(request)
    assert transport.calls == 1


def test_budgeted_ga4_channel_disables_transparent_transport_retries(tmp_path, monkeypatch):
    from gsc_mcp import auth
    api = runtime()
    session = api.AuditSession(config(tmp_path))
    options = []
    class Transport:
        @staticmethod
        def create_channel(**kwargs): options.extend(kwargs['options']); return 'test-channel'
        def __init__(self, *, channel): assert channel == 'test-channel'
    monkeypatch.setattr(auth, 'BetaAnalyticsDataGrpcTransport', Transport, raising=False)
    monkeypatch.setattr(auth, '_ga4_creds', lambda: 'synthetic-credentials')
    monkeypatch.setattr(auth, 'BetaAnalyticsDataClient', lambda **kwargs: kwargs)
    with session.activate(): client = auth.get_ga4_service()
    assert isinstance(client.get('transport'), Transport)
    assert ('grpc.enable_retries', 0) in options


def test_stale_google_connection_retry_is_budgeted_before_dispatch(tmp_path):
    import http.client
    import httplib2
    from googleapiclient.http import HttpRequest
    api = runtime()
    settings = config(tmp_path); settings['max_provider_attempts'] = 1
    session = api.AuditSession(settings)
    class Connection:
        sock = object()
        calls = 0
        def connect(self): self.sock = object()
        def close(self): self.sock = None
        def request(self, *args, **kwargs): self.calls += 1
        def getresponse(self):
            if self.calls == 1: raise http.client.BadStatusLine('stale')
            raise AssertionError('a second physical request bypassed the ceiling')
    connection = Connection()
    transport = httplib2.Http()
    transport.connections['https:example.com'] = connection
    request = HttpRequest(transport, lambda *_: {}, 'https://example.com/api')
    with session.activate(), pytest.raises(api.AuditBudgetExceeded): api.execute_google(request)
    assert connection.calls == 1
    assert session.status()['provider_attempts'] == 1


def test_bing_uses_its_own_scope_and_checks_all_url_parameters(tmp_path):
    api = runtime()
    settings = config(tmp_path)
    settings.update(site='https://www.example.com/', allowed_tools=['bing_url_info', 'bing_page_query_stats', 'bing_feed_details', 'bing_link_counts'])
    session = api.AuditSession(settings)
    assert session.validate_request('bing_url_info', {'site': settings['bing_site'], 'url': 'https://example.com/page'})['url'] == 'https://example.com/page'
    assert session.validate_request('bing_link_counts', {'site': settings['bing_site'], 'page': 1})['page'] == 1
    for tool, key in [('bing_page_query_stats', 'page'), ('bing_feed_details', 'feed_url'), ('bing_url_info', 'url')]:
        with pytest.raises(ValueError, match='scope'):
            session.validate_request(tool, {'site': settings['bing_site'], key: 'https://other.test/private'})


def test_sqlite_connections_are_closed_after_each_operation(tmp_path, monkeypatch):
    import sqlite3
    api = runtime()
    opened = []
    original = sqlite3.connect
    def connect(*args, **kwargs):
        connection = original(*args, **kwargs); opened.append(connection); return connection
    monkeypatch.setattr(api.sqlite3, 'connect', connect)
    session = api.AuditSession(config(tmp_path))
    session.status()
    with session.activate(): api.provider_attempt('google')
    for connection in opened:
        with pytest.raises(sqlite3.ProgrammingError, match='closed'):
            connection.execute('SELECT 1')
