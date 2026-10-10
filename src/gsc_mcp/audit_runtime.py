"""Optional read-only acquisition with a durable, shared attempt ceiling.

Only explicitly instrumented Google/Bing/GA4 API calls are counted. Credential
refresh and ancillary HTML/CrUX requests are outside this contract. No setting
is enabled by default, and observations are cached only within this session.
"""
from contextlib import contextmanager
from contextvars import ContextVar
import hashlib
import inspect
import json
import os
from pathlib import Path
import re
import sqlite3
from threading import RLock
from urllib.parse import urlsplit

_CURRENT = ContextVar('gsc_audit_session', default=None)
READ_ONLY_TOOLS = frozenset({
    'get_capabilities', 'list_properties', 'get_site_details', 'get_search_analytics',
    'get_performance_overview', 'compare_search_periods', 'search_change_breakdown',
    'search_weekday_reference', 'traffic_drops', 'check_alerts', 'seo_lost_queries',
    'seo_cannibalization', 'quick_wins', 'seo_striking_distance', 'inspect_url',
    'batch_url_inspection', 'check_indexing_issues', 'list_sitemaps', 'sitemaps_get',
    'ga4_ai_referrals', 'ga4_organic_landing_pages', 'ga4_traffic_sources',
    'ga4_page_performance', 'ga4_realtime', 'ga4_user_behavior',
    'ga4_conversion_funnel', 'ga4_funnel', 'traffic_health_check', 'compare_search_engines',
    'indexing_evidence_matrix', 'bing_sites_list', 'bing_query_stats', 'bing_page_stats',
    'bing_page_query_stats', 'bing_rank_traffic_stats', 'bing_crawl_stats',
    'bing_crawl_issues', 'bing_crawl_settings_get', 'bing_url_info', 'bing_url_traffic',
    'bing_feeds_list', 'bing_feed_details', 'bing_url_submission_quota',
    'bing_link_counts', 'bing_url_links',
})


class AuditBudgetExceeded(RuntimeError):
    """A call was refused before its provider attempt."""


def provider_attempt(provider):
    session = _CURRENT.get()
    if session is not None:
        session._reserve('provider', provider)


def execute_google(request):
    if _CURRENT.get() is not None:
        from googleapiclient.http import HttpRequest
        from google_auth_httplib2 import AuthorizedHttp
        import httplib2
        if isinstance(request, HttpRequest):
            transport = request.http
            while isinstance(transport, AuthorizedHttp): transport = transport.http
            if not getattr(transport, '_gsc_audit_instrumented', False):
                if isinstance(transport, httplib2.Http):
                    original = transport._conn_request
                    def counted_connection(conn, *args, **kwargs):
                        # Covers existing and newly created connections, including
                        # httplib2's internal stale-connection retry loop.
                        if not getattr(conn, '_gsc_audit_instrumented', False):
                            dispatch = conn.request
                            def counted_dispatch(*args, **kwargs):
                                provider_attempt('google')
                                return dispatch(*args, **kwargs)
                            conn.request = counted_dispatch
                            conn._gsc_audit_instrumented = True
                        return original(conn, *args, **kwargs)
                    transport._conn_request = counted_connection
                else:
                    original = transport.request
                    def counted(*args, **kwargs):
                        provider_attempt('google')
                        return original(*args, **kwargs)
                    transport.request = counted
                transport._gsc_audit_instrumented = True
        else:
            # Controlled non-HTTP adapters count their dispatch boundary.
            provider_attempt('google')
    return request.execute()


def call_ga4(method, *args, **kwargs):
    provider_attempt('ga4')
    if _CURRENT.get() is not None:
        # GAPIC retry must not hide additional physical attempts inside one call.
        kwargs['retry'] = None
    return method(*args, **kwargs)


def audit_active():
    return _CURRENT.get() is not None


class AuditSession:
    def __init__(self, config):
        required = {'run_id', 'site', 'bing_site', 'ledger_path', 'max_provider_attempts',
                    'max_tool_calls', 'allowed_tools'}
        if not isinstance(config, dict) or not required <= set(config) or set(config) - required - {'ga4_property', 'max_native_calls'}:
            raise ValueError('Invalid audit configuration fields')
        if not isinstance(config['run_id'], str) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,96}', config['run_id']):
            raise ValueError('Invalid run identifier')
        for field in ('max_provider_attempts', 'max_tool_calls'):
            if type(config[field]) is not int or not 1 <= config[field] <= 10000:
                raise ValueError('Invalid audit bound')
        if type(config.get('max_native_calls', 2)) is not int or not 1 <= config.get('max_native_calls', 2) <= 64:
            raise ValueError('Invalid native attempt bound')
        tools = config['allowed_tools']
        if not isinstance(tools, list) or not tools or any(not isinstance(t, str) or t not in READ_ONLY_TOOLS for t in tools):
            raise ValueError('Audit tools must be allowed read-only tools')
        if any(t.startswith('ga4_') or t == 'traffic_health_check' for t in tools):
            prop = config.get('ga4_property')
            if not isinstance(prop, str) or not re.fullmatch(r'(properties/)?[0-9]+', prop):
                raise ValueError('GA4 audit tools require an explicit property scope')
        for field in ('site', 'bing_site', 'ledger_path'):
            if not isinstance(config[field], str) or not config[field]:
                raise ValueError('Invalid audit scope/path')
        site = config['site']
        if site.startswith('sc-domain:'):
            domain = site[10:]
            parsed = urlsplit('https://' + domain)
            if not domain or parsed.hostname != domain or parsed.path or parsed.query or parsed.fragment or parsed.port or parsed.username:
                raise ValueError('Invalid domain scope')
        else:
            self._url(site)
        self._url(config['bing_site'])
        self.config = dict(config, allowed_tools=sorted(set(tools)))
        self.path = Path(config['ledger_path'])
        if not self.path.is_absolute() or not self.path.parent.is_dir() or self.path.is_symlink():
            raise ValueError('Ledger requires an absolute nonsymlink path in an existing directory')
        self.lock = RLock()
        self.cache = {}
        self.cache_bytes = 0
        self.digest = hashlib.sha256(json.dumps(self.config, sort_keys=True).encode()).hexdigest()
        # Create private state without changing unrelated files or parent permissions.
        if not self.path.exists():
            fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.close(fd)
        with self._db() as db:
            db.execute('CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, digest TEXT NOT NULL, provider INTEGER NOT NULL, tool INTEGER NOT NULL)')
            db.execute('BEGIN IMMEDIATE')
            db.execute('INSERT OR IGNORE INTO runs VALUES (?, ?, 0, 0)', (config['run_id'], self.digest))
            stored = db.execute('SELECT digest FROM runs WHERE id=?', (config['run_id'],)).fetchone()[0]
            if stored != self.digest:
                raise ValueError('Audit run configuration changed; choose a new run identifier')
            db.execute('CREATE TABLE IF NOT EXISTS native_runs (id TEXT PRIMARY KEY, attempts INTEGER NOT NULL)')
            db.execute('INSERT OR IGNORE INTO native_runs VALUES (?, 0)', (config['run_id'],))

    @contextmanager
    def _db(self):
        connection = sqlite3.connect(self.path, timeout=10)
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    @staticmethod
    def _url(value):
        try:
            parsed = urlsplit(value)
            if parsed.scheme not in {'http', 'https'} or not parsed.hostname or parsed.username or parsed.password:
                raise ValueError()
            parsed.port
            return parsed
        except (ValueError, TypeError):
            raise ValueError('Invalid URL scope') from None

    def _scope(self, name, arguments):
        if 'property_id' in arguments:
            expected = self.config['ga4_property']
            requested = arguments['property_id']
            if requested is not None and requested.removeprefix('properties/') != expected.removeprefix('properties/'):
                raise ValueError('GA4 property outside audit scope')
            arguments['property_id'] = expected
        for key in ('site', 'site_url', 'google_site', 'bing_site'):
            if key in arguments:
                expected = self.config['bing_site'] if name.startswith('bing_') or key == 'bing_site' else self.config['site']
                if arguments[key] != expected:
                    raise ValueError('Tool property outside audit scope')
        urls = [arguments[key] for key in ('url', 'feed_url', 'sitemap_url') if key in arguments]
        if name == 'bing_page_query_stats':
            urls.append(arguments['page'])
        urls += arguments.get('urls', [])
        for value in urls:
            parsed = self._url(value)
            site = self.config['bing_site' if name.startswith('bing_') else 'site']
            if site.startswith('sc-domain:'):
                domain = site[10:]
                match = parsed.hostname == domain or parsed.hostname.endswith('.' + domain)
            else:
                prefix = self._url(site)
                match = (parsed.scheme, parsed.netloc) == (prefix.scheme, prefix.netloc) and parsed.path.startswith(prefix.path)
            if not match:
                raise ValueError('URL outside audit scope')

    def _reserve(self, kind, provider=None):
        limit = self.config['max_provider_attempts' if kind == 'provider' else 'max_tool_calls']
        with self._db() as db:
            db.execute('BEGIN IMMEDIATE')
            used = db.execute(f'SELECT {kind} FROM runs WHERE id=?', (self.config['run_id'],)).fetchone()[0]
            if used >= limit:
                raise AuditBudgetExceeded(f'{kind}_attempt_budget_exhausted')
            db.execute(f'UPDATE runs SET {kind}={kind}+1 WHERE id=?', (self.config['run_id'],))

    def reserve_native(self):
        """Reserve before a native invocation, including failed invocations."""
        with self._db() as db:
            db.execute('BEGIN IMMEDIATE')
            used = db.execute('SELECT attempts FROM native_runs WHERE id=?', (self.config['run_id'],)).fetchone()[0]
            if used >= self.config.get('max_native_calls', 2):
                raise AuditBudgetExceeded('native_attempt_budget_exhausted')
            db.execute('UPDATE native_runs SET attempts=attempts+1 WHERE id=?', (self.config['run_id'],))

    @contextmanager
    def activate(self):
        token = _CURRENT.set(self)
        try:
            yield self
        finally:
            _CURRENT.reset(token)

    def validate_request(self, name, arguments):
        from gsc_mcp.registry import TOOLS
        if name not in self.config['allowed_tools']:
            raise ValueError('Tool is not allowed in this audit')
        bound = inspect.signature(TOOLS[name]).bind(**arguments)
        bound.apply_defaults()
        self._scope(name, bound.arguments)
        return dict(bound.arguments)

    def call(self, name, arguments):
        from gsc_mcp.registry import TOOLS
        arguments = self.validate_request(name, arguments)
        key = json.dumps([name, arguments], sort_keys=True, ensure_ascii=False)
        # Serialize acquisition in this session: duplicate concurrent requests
        # share one immutable JSON response rather than race into the provider.
        with self.lock:
            self._reserve('tool')
            if key in self.cache:
                return self.cache[key]
            with self.activate():
                result = TOOLS[name](**arguments)
            if not isinstance(result, str) or len(result.encode()) > 2_000_000:
                raise ValueError('Audit observation exceeds byte budget')
            json.loads(result)
            if self.cache_bytes + len(result.encode()) > 8_000_000:
                raise ValueError('Audit shared observations exceed byte budget')
            self.cache[key] = result
            self.cache_bytes += len(result.encode())
            return result

    def status(self):
        with self._db() as db:
            provider, tool = db.execute('SELECT provider, tool FROM runs WHERE id=?', (self.config['run_id'],)).fetchone()
            native = db.execute('SELECT attempts FROM native_runs WHERE id=?', (self.config['run_id'],)).fetchone()[0]
        return {'run_id': self.config['run_id'], 'site': self.config['site'],
                'provider_attempts': provider, 'tool_calls': tool,
                'native_attempts': native, 'max_native_calls': self.config.get('max_native_calls', 2),
                'max_provider_attempts': self.config['max_provider_attempts'],
                'cache_scope': 'session', 'acquisition': 'serialized',
                'budget_scope': 'Google HTTP including attached authentication replays, Bing HTTP and GA4 RPC dispatch; excludes credential resolution and ancillary fetches'}


def session_from_environment():
    path = os.environ.get('GSC_MCP_AUDIT_CONFIG')
    if not path:
        return None
    with open(path, 'rb') as handle:
        raw = handle.read(65537)
    if len(raw) > 65536:
        raise ValueError('Audit configuration exceeds byte limit')
    return AuditSession(json.loads(raw))
