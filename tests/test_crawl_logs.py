"""Local log fixtures and mocked registry transport, not authenticated live traffic."""
import json
from pathlib import Path

import pytest


def line(path='/public?token=SECRET', ip='192.0.2.1', ua='Googlebot', status=200,
         stamp='09/Oct/2026:12:00:00 +0200'):
    return f'{ip} - private-user [{stamp}] "GET {path} HTTP/1.1" {status} 42 "https://ref.test/?secret=SECRET" "{ua}"\n'


def run(tmp_path, content, **kwargs):
    from gsc_mcp.tools.crawl_logs import crawl_log_audit
    file = tmp_path / 'access.log'
    file.write_text(content)
    return json.loads(crawl_log_audit(str(file), site='sc-domain:example.com', **kwargs))


def test_default_parser_masks_sensitive_input_and_keeps_utc_observed_window(tmp_path, monkeypatch):
    import httpx
    monkeypatch.setattr(httpx, 'Client', lambda *a, **k: pytest.fail('default log audit must not use network'))
    result = run(tmp_path, line())
    assert result['coverage']['parsed_lines'] == 1
    assert result['observed_window']['start'] == '2026-10-09T10:00:00+00:00'
    assert result['declared_ua_counts']['googlebot'] == 1
    assert result['identity_counts']['declared_only'] == 1
    output = json.dumps(result)
    for private in ('192.0.2.1', 'SECRET', 'private-user', 'ref.test', '/public'):
        assert private not in output
    assert result['indexing_status'] == 'unavailable'


def test_explicit_public_paths_strip_query_and_keep_http_errors(tmp_path):
    result = run(tmp_path, line(status=404), include_paths=True)
    assert result['paths'][0]['path'] == '/public'
    assert result['paths'][0]['status_counts'] == {'404': 1}
    assert 'SECRET' not in json.dumps(result)


def test_common_profile_has_no_ua_or_identity_claim(tmp_path):
    result = run(tmp_path, line().split(' "https://ref.test/')[0]+'\n', profile='common')
    assert result['declared_ua_counts'] == {'unavailable': 1}
    assert result['identity_counts'] == {'declared_only': 1}


def test_invalid_and_timezone_missing_lines_leave_partial_coverage(tmp_path):
    result = run(tmp_path, line()+line(stamp='09/Oct/2026:12:00:00')+'not a log\n')
    assert result['status'] == 'partial'
    assert result['coverage']['invalid_lines'] == 2
    assert result['coverage']['parsed_lines'] == 1


def test_byte_line_and_path_limits_are_explicit(tmp_path):
    out = run(tmp_path, line('/a')+line('/b')+line('/c'), max_paths=1)
    assert out['coverage']['paths_not_retained'] == 2
    assert out['status'] == 'partial'
    out = run(tmp_path, line()*10, max_bytes=100)
    assert out['coverage']['consumed_bytes'] <= 100
    assert 'byte_limit' in out['coverage']['limits_hit']
    out = run(tmp_path, line('/'+'x'*10000)+line('/valid'), include_paths=True)
    assert out['coverage']['invalid_lines'] == 1
    assert out['paths'][0]['path'] == '/valid'


def test_foreign_absolute_request_is_excluded_instead_of_pooled(tmp_path):
    out = run(tmp_path, line('https://other.test/a')+line('/valid'))
    assert out['coverage']['excluded_lines'] == 1
    assert out['coverage']['parsed_lines'] == 1


def test_optional_registry_distinguishes_ip_membership_from_declared_bot(tmp_path, monkeypatch):
    from gsc_mcp.tools import crawl_logs
    monkeypatch.setattr(crawl_logs, '_google_ranges', lambda: (['192.0.2.0/24'],
        {'status':'observed', 'method':'published_ip_ranges', 'retrieved_at':'fixture', 'sha256':'fixture'}))
    out = run(tmp_path, line(ip='192.0.2.1')+line(ip='198.51.100.1'), verify_googlebot=True)
    assert out['identity_counts']['in_current_google_ranges'] == 1
    assert out['identity_counts']['not_in_current_google_ranges'] == 1
    assert out['verification']['historical_identity'] == 'unverified'
    assert '192.0.2.1' not in json.dumps(out)


def test_verification_failure_and_reverse_dns_only_do_not_become_verified(tmp_path, monkeypatch):
    from gsc_mcp.tools import crawl_logs
    monkeypatch.setattr(crawl_logs, '_google_ranges', lambda: ([], {'status':'unavailable', 'error':'TimeoutError'}))
    out = run(tmp_path, line(ua='Googlebot crawl-192-0-2-1.googlebot.com'), verify_googlebot=True)
    assert out['identity_counts'] == {'verification_unavailable': 1}


@pytest.mark.parametrize('options', [{'profile':'custom'}, {'max_bytes':True}, {'max_lines':0}, {'max_paths':10001}, {'limit':0}])
def test_invalid_options_fail_before_reading_file(tmp_path, options):
    with pytest.raises(ValueError):
        run(tmp_path, line(), **options)


def test_rows_are_incremental_and_summary_limit_reports_omissions(tmp_path):
    out = run(tmp_path, ''.join(line('/page/'+str(i)) for i in range(2000)), max_paths=1000, limit=3)
    assert len(out['paths']) == 3
    assert out['coverage']['paths_not_retained'] == 1000
    assert out['coverage']['summary_omitted_paths'] == 997


@pytest.mark.parametrize('payload,observed', [
    ({'prefixes':[{'ipv4Prefix':'192.0.2.0/24'}], 'creationTime':'fixture'}, True),
    ({'prefixes':[{'ipv6Prefix':'192.0.2.0/24'}]}, False),
    ({'prefixes':[]}, False),
    ('x'*262145, False),
])
def test_registry_transport_and_schema_are_bounded(monkeypatch, payload, observed):
    from gsc_mcp.tools import crawl_logs
    raw = (payload if isinstance(payload,str) else json.dumps(payload)).encode()
    class Response:
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def raise_for_status(self): pass
        def iter_bytes(self,size):
            for offset in range(0,len(raw),size): yield raw[offset:offset+size]
    class Client:
        def __init__(self,**options): assert options['follow_redirects'] is False
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def stream(self,method,url):
            assert method == 'GET' and url == crawl_logs._GOOGLE_RANGES
            return Response()
    monkeypatch.setattr(crawl_logs.httpx,'Client',Client)
    ranges, metadata = crawl_logs._google_ranges()
    assert (metadata['status'] == 'observed') is observed
    assert bool(ranges) is observed


def test_line_limit_and_invalid_month_remain_visible(tmp_path):
    out = run(tmp_path, line()*3, max_lines=1)
    assert out['coverage']['parsed_lines'] == 1
    assert out['coverage']['limits_hit'] == ['line_limit']
    out = run(tmp_path, line(stamp='09/BAD/2026:12:00:00 +0200'))
    assert out['coverage']['invalid_lines'] == 1
    assert out['coverage']['excluded_lines'] == 0


def test_missing_file_is_unavailable_without_registry_call(tmp_path, monkeypatch):
    from gsc_mcp.tools import crawl_logs
    monkeypatch.setattr(crawl_logs, '_google_ranges', lambda: pytest.fail('file validation precedes network'))
    out = json.loads(crawl_logs.crawl_log_audit(str(tmp_path/'missing.log'),site='sc-domain:example.com',verify_googlebot=True))
    assert out['status'] == 'unavailable'
    assert out['_meta']['evidence']['fields']['/coverage/parsed_lines']['basis'] is None
