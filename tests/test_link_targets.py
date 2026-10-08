"""Destination observations through a real observer and mocked network boundaries."""

import json
import socket
import time
from contextlib import contextmanager

import httpx
import pytest

import gsc_mcp.url_safety as safety


@pytest.fixture
def network(monkeypatch):
    routes, sent, closed, clients = {}, [], [], []
    monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **k: [
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))
    ])

    class Stream(httpx.SyncByteStream):
        def __init__(self, body, unread):
            self.body, self.unread = body, unread

        def __iter__(self):
            if self.unread:
                raise AssertionError("destination response body was consumed")
            yield from self.body

        def close(self):
            closed.append(True)

    class Client:
        def __init__(self, **kwargs):
            clients.append(kwargs)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        @contextmanager
        def stream(self, method, url):
            assert method == "GET"
            sent.append(url)
            route = routes[url]
            if isinstance(route, Exception):
                raise route
            status, headers, body, unread = route
            response = httpx.Response(status, headers=headers, stream=Stream(body, unread),
                                      request=httpx.Request(method, url))
            try:
                yield response
            finally:
                response.close()

    monkeypatch.setattr(httpx, "Client", Client)
    return routes, sent, closed, clients


def audit(*args, **kwargs):
    from gsc_mcp.tools.link_targets import link_targets_audit
    return json.loads(link_targets_audit(*args, **kwargs))


def test_terminal_status_and_anchor_associations(network):
    routes, sent, closed, clients = network
    routes["https://example.com/start"] = (301, {"location": "https://www.example.com/dir/page"}, [], True)
    routes["https://www.example.com/dir/page"] = (200, {}, [b'''<nav><a href="../x?y=1#part">One</a></nav>
        <footer><a href="/x?y=1#other" rel="nofollow">Two</a></footer>
        <a href="/x?y=2">Three</a><a href="/x/?y=1">Slash</a>
        <a href="/x?a=1&amp;b=2">Order</a><a href="/x?b=2&amp;a=1">Reverse</a>'''], False)
    for url, status in [("https://www.example.com/x?y=1", 404), ("https://www.example.com/x?y=2", 500),
                        ("https://www.example.com/x/?y=1", 204), ("https://www.example.com/x?a=1&b=2", 200),
                        ("https://www.example.com/x?b=2&a=1", 410)]:
        routes[url] = (status, {}, [], True)
    result = audit("https://example.com/start")
    assert result["source_requested_url"] == "https://example.com/start"
    assert result["source_final_url"] == "https://www.example.com/dir/page"
    assert result["coverage"] == "complete"
    assert result["distinct_in_scope_targets"] == 5
    first = result["targets"][0]
    assert first["status_code"] == 404 and first["outcome"] == "observed"
    assert [link["zone"] for link in first["source_links"]] == ["nav", "footer"]
    assert first["source_links"][0]["href"] == "../x?y=1#part"
    assert result["budgets"]["requests_started"] == 7
    assert len(sent) == len(closed) == 7
    assert all(c["trust_env"] is False and c["follow_redirects"] is False for c in clients)


def test_failed_and_skipped_targets_are_unavailable(network):
    routes, sent, *_ = network
    routes["https://example.com/"] = (200, {}, [b'<a href="/a">A</a><a href="/b">B</a><a href="/c">C</a>'], False)
    routes["https://example.com/a"] = httpx.ReadTimeout("private diagnostic")
    result = audit("https://example.com/", max_targets=2, max_requests=2)
    assert [t["availability_reason"] for t in result["targets"]] == ["timeout", "skipped_request_budget", "skipped_target_budget"]
    assert result["coverage"] == "partial"
    assert result["budgets"]["requests_started"] == len(sent) == 2
    assert "private diagnostic" not in json.dumps(result)
    assert all(t["status_code"] is None for t in result["targets"])


@pytest.mark.parametrize("kwargs", [{"max_targets": True}, {"max_targets": 0}, {"max_targets": 101},
                                        {"max_requests": False}, {"max_requests": 201}])
def test_invalid_budgets_fail_before_network(network, kwargs):
    with pytest.raises(ValueError):
        audit("https://example.com/", **kwargs)
    assert network[1] == []


def test_source_incomplete_prevents_zero_failure_claim(network):
    routes, sent, *_ = network
    routes["https://example.com/"] = (200, {"content-encoding": "gzip"}, [b'zip'], False)
    result = audit("https://example.com/")
    assert result["coverage"] == "unavailable"
    assert result["source_observation"]["availability_reason"] == "unsupported_content_encoding"
    assert result["targets"] == []


def test_malformed_external_and_scheme_links_are_counted_without_fetch(network):
    routes, sent, *_ = network
    routes["https://example.com/"] = (200, {}, [b'''<a href="https://[malformed">Bad</a>
      <a href="https://user:secret@example.com/">Credentials</a><a href="https://example.com.evil.test/">Outside</a>
      <a href="mailto:person@example.com">Mail</a><a href="#part">Fragment</a><a href="">Empty</a>
      <a href="/ok">OK</a>'''], False)
    routes["https://example.com/ok"] = (200, {}, [], True)
    result = audit("https://example.com/")
    assert result["excluded_reasons"] == {"invalid_url": 2, "external": 1, "non_http_scheme": 1, "fragment_only": 1, "empty_href": 1}
    assert result["total_anchors"] == 7
    assert len(sent) == 2
    assert "secret" not in json.dumps(result)


def observe(url, **kwargs):
    budget = kwargs.pop("budget", None) or safety.FetchObservationBudget(20, time.monotonic() + 60)
    return safety.observe_get_redirects(url, site_url="https://example.com/", budget=budget, **kwargs)


@pytest.mark.parametrize("status", [301, 302, 303, 307, 308])
def test_redirect_headers_are_kept_and_target_bodies_never_read(network, status):
    routes, sent, closed, _ = network
    routes["https://example.com/a"] = (status, {"location": "/b"}, [], True)
    routes["https://example.com/b"] = (404, {"location": "/never"}, [], True)
    result = observe("https://example.com/a")
    assert result["status_code"] == 404 and result["final_url"] == "https://example.com/b"
    assert [h["status_code"] for h in result["hops"]] == [status, 404]
    assert result["hops"][0]["next_url"] == "https://example.com/b"
    assert len(sent) == len(closed) == 2


def test_timeout_does_not_attribute_predecessor_status_to_next_url(network):
    routes, *_ = network
    routes["https://example.com/a"] = (301, {"location": "/b"}, [], True)
    routes["https://example.com/b"] = httpx.ReadTimeout("timeout")
    result = observe("https://example.com/a")
    assert result["status_code"] is None and result["final_url"] is None
    assert result["last_observed_status"] == 301
    assert result["last_response_url"] == "https://example.com/a"
    assert result["last_requested_url"] == "https://example.com/b"
    assert result["availability_reason"] == "timeout"


@pytest.mark.parametrize("destination", ["https://localhost/", "https://127.0.0.1/", "https://10.0.0.1/",
    "https://169.254.169.254/", "https://2130706433/", "https://example.com.evil.test/",
    "https://sub.example.com/", "https://example.com:444/", "https://user:secret@example.com/",
    "https://%65xample.com/", "https://example.com\\evil/", "https://[malformed", "https://example.com:0/",
    "https://example.com:65536/", "https://example.com:no/", "https://example.com/#@evil", "https://example.com/\n"])
def test_redirect_refused_before_rejected_url_is_requested(network, destination):
    routes, sent, closed, _ = network
    routes["https://example.com/a"] = (302, {"location": destination}, [], True)
    result = observe("https://example.com/a")
    assert result["outcome"] == "unavailable" and result["status_code"] is None
    assert result["last_observed_status"] == 302
    assert sent == ["https://example.com/a"] and len(closed) == 1
    assert "secret" not in json.dumps(result)


@pytest.mark.parametrize("location, reason", [("#fragment", "redirect_loop"), ("/a", "redirect_loop"), (None, "redirect_missing_location")])
def test_redirect_stops_have_no_inferred_terminal_status(network, location, reason):
    routes, sent, *_ = network
    routes["https://example.com/a"] = (302, {} if location is None else {"location": location}, [], True)
    result = observe("https://example.com/a")
    assert result["availability_reason"] == reason
    assert result["status_code"] is None and len(sent) == 1


def test_source_raw_body_cap_and_stream_closure(network):
    routes, _, closed, _ = network
    routes["https://example.com/a"] = (200, {}, [b"abcd", b"ef"], False)
    result = observe("https://example.com/a", max_body_bytes=5)
    assert result["body"] == b"abcde" and result["body_complete"] is False
    assert result["availability_reason"] == "source_body_limit"
    assert len(closed) == 1


def test_request_and_deadline_budget_stop_before_another_hop(network):
    routes, sent, *_ = network
    routes["https://example.com/a"] = (302, {"location": "/b"}, [], True)
    budget = safety.FetchObservationBudget(1, time.monotonic() + 60)
    result = observe("https://example.com/a", budget=budget)
    assert result["availability_reason"] == "skipped_request_budget" and budget.requests_started == 1
    result = observe("https://example.com/a", budget=safety.FetchObservationBudget(1, time.monotonic() - 1))
    assert result["availability_reason"] == "skipped_deadline"
    assert sent == ["https://example.com/a"]


def test_content_length_limit_refuses_without_body_read(network):
    routes, _, closed, _ = network
    routes["https://example.com/a"] = (200, {"content-length": "6"}, [], True)
    result = observe("https://example.com/a", max_body_bytes=5)
    assert result["body"] == b"" and result["availability_reason"] == "source_body_limit"
    assert len(closed) == 1


def test_deadline_is_checked_before_source_body_read(network, monkeypatch):
    routes, _, closed, _ = network
    routes["https://example.com/a"] = (200, {}, [], True)
    # Socket/header work overruns the deadline; consuming body after that is a bug.
    ticks = iter([0, 0, 0, 0, 0, 61, 61, 61, 61])
    monkeypatch.setattr(safety.time, "monotonic", lambda: next(ticks))
    result = observe("https://example.com/a", budget=safety.FetchObservationBudget(20, 60), max_body_bytes=5)
    assert result["availability_reason"] == "skipped_deadline"
    assert len(closed) == 1


@pytest.mark.parametrize("terminal", [304, 404])
def test_location_on_non_redirect_status_is_never_followed(network, terminal):
    routes, sent, *_ = network
    routes["https://example.com/a"] = (terminal, {"location": "/b"}, [], True)
    result = observe("https://example.com/a")
    assert result["status_code"] == terminal and result["outcome"] == "observed"
    assert sent == ["https://example.com/a"]


def test_redirect_hop_limit_bounds_physical_requests(network):
    routes, sent, *_ = network
    for index in range(6):
        routes[f"https://example.com/{index}"] = (302, {"location": f"/{index + 1}"}, [], True)
    result = observe("https://example.com/0")
    assert result["availability_reason"] == "redirect_hop_budget"
    assert len(result["hops"]) == len(sent) == 6


def test_explicit_default_ports_and_www_alias_share_scope_but_not_identity(network):
    routes, sent, *_ = network
    routes["https://example.com/a"] = (302, {"location": "http://www.example.com:80/b"}, [], True)
    routes["http://www.example.com/b"] = (200, {}, [], True)
    result = observe("https://example.com:443/a")
    assert result["final_url"] == "http://www.example.com/b"
    assert sent == ["https://example.com/a", "http://www.example.com/b"]


def test_nonstandard_port_cannot_transition_to_default_port(network):
    routes, sent, *_ = network
    routes["https://example.com:444/a"] = (302, {"location": "https://example.com/b"}, [], True)
    result = safety.observe_get_redirects("https://example.com:444/a", site_url="https://example.com:444/",
                                         budget=safety.FetchObservationBudget(20, time.monotonic() + 60))
    assert result["availability_reason"] == "out_of_scope_redirect"
    assert sent == ["https://example.com:444/a"]


@pytest.mark.parametrize("url", ["https://user:secret@example.com/", "https://127.0.0.1/", "https://[2606:4700:4700::1111]/"])
def test_direct_refusal_keeps_attempt_and_status_empty(network, url):
    result = observe(url)
    assert result["attempted"] is False and result["last_requested_url"] is None
    assert result["status_code"] is None and network[1] == []


def test_source_non_success_has_unavailable_coverage(network):
    routes, sent, *_ = network
    routes["https://example.com/"] = (404, {}, [], True)
    result = audit("https://example.com/")
    assert result["source_observation"]["outcome"] == "observed"
    assert result["coverage"] == "unavailable" and len(sent) == 1


def test_deadline_overrun_is_reported_and_subsequent_targets_skipped(network, monkeypatch):
    routes, sent, *_ = network
    routes["https://example.com/"] = (200, {}, [b'<a href="/a">A</a><a href="/b">B</a>'], False)
    routes["https://example.com/a"] = (200, {}, [], True)
    actual_observe = safety.observe_get_redirects
    clock = [0.0]
    monkeypatch.setattr(safety.time, "monotonic", lambda: clock[0])
    def slow_target(url, **kwargs):
        result = actual_observe(url, **kwargs)
        if url.endswith("/a"):
            clock[0] = 61.0
        return result
    monkeypatch.setattr("gsc_mcp.tools.link_targets.observe_get_redirects", slow_target)
    result = audit("https://example.com/")
    assert result["budgets"]["deadline_overrun"] is True
    assert result["targets"][1]["availability_reason"] == "skipped_deadline"
    assert sent == ["https://example.com/", "https://example.com/a"]


def test_empty_query_anchors_preserve_resolution_and_fetch_identities(network):
    routes, sent, *_ = network
    routes["https://example.com/start?old=1"] = (200, {}, [b'''<a href="?">Clear</a>
      <a href="?#part">Clear fragment</a><a href="/a?">Empty path query</a>
      <a href="/a?#part">Empty path query fragment</a><a href="/a">No query</a>
      <a href="/a?x=1">Nonempty</a><a href="#part">Source fragment</a>
      <a href="https://example.com/a?">Absolute empty</a><a href="//example.com/a?">Protocol empty</a>'''], False)
    for target in ["https://example.com/start?", "https://example.com/a?", "https://example.com/a", "https://example.com/a?x=1"]:
        routes[target] = (200, {}, [], True)
    result = audit("https://example.com/start?old=1")
    assert [t["requested_url"] for t in result["targets"]] == [
        "https://example.com/start?", "https://example.com/a?", "https://example.com/a", "https://example.com/a?x=1"]
    assert result["targets"][0]["source_links"][1]["absolute_url"] == "https://example.com/start?#part"
    assert result["targets"][1]["source_links"][1]["absolute_url"] == "https://example.com/a?#part"
    assert len(result["targets"][1]["source_links"]) == 4
    assert len(sent) == 5


@pytest.mark.parametrize("location, target", [
    ("?", "https://example.com/start?"), ("?#part", "https://example.com/start?"),
    ("/a?", "https://example.com/a?"), ("/a?#part", "https://example.com/a?"),
    ("https://example.com/a?", "https://example.com/a?"), ("//example.com/a?", "https://example.com/a?"),
])
def test_empty_query_source_redirects_keep_cleared_query(network, location, target):
    routes, sent, *_ = network
    routes["https://example.com/start?old=1"] = (301, {"location": location}, [], True)
    routes[target] = (200, {}, [b'<a href="?">Self query</a>'], False)
    result = audit("https://example.com/start?old=1", max_requests=2)
    assert result["source_final_url"] == target
    assert result["source_observation"]["hops"][0]["next_url"].split("#")[0] == target
    assert sent == ["https://example.com/start?old=1", target]
    assert result["targets"][0]["requested_url"] == target


@pytest.mark.parametrize("location, target", [
    ("?", "https://example.com/start?"), ("?#part", "https://example.com/start?"),
    ("/a?", "https://example.com/a?"), ("/a?#part", "https://example.com/a?"),
    ("https://example.com/a?", "https://example.com/a?"), ("//example.com/a?", "https://example.com/a?"),
])
def test_empty_query_destination_redirects_keep_cleared_query(network, location, target):
    routes, sent, *_ = network
    routes["https://example.com/start?old=1"] = (302, {"location": location}, [], True)
    routes[target] = (404, {}, [], True)
    result = observe("https://example.com/start?old=1")
    assert result["status_code"] == 404 and result["final_url"] == target
    assert sent == ["https://example.com/start?old=1", target]


def test_httpx_transport_receives_explicit_empty_queries(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **k: [
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))])
    actual_client, paths = httpx.Client, []
    class Body(httpx.SyncByteStream):
        def __iter__(self):
            yield b'<a href="?">Clear</a><a href="/a?">Empty</a><a href="/a">None</a><a href="/a?x=1">Value</a>'
    def handler(request):
        paths.append(request.url.raw_path)
        return httpx.Response(200, stream=Body()) if len(paths) == 1 else httpx.Response(404)
    monkeypatch.setattr(httpx, "Client", lambda **kwargs: actual_client(
        transport=httpx.MockTransport(handler), **kwargs))
    result = audit("https://example.com/start?old=1")
    assert paths == [b"/start?old=1", b"/start?", b"/a?", b"/a", b"/a?x=1"]
    assert [t["status_code"] for t in result["targets"]] == [404, 404, 404, 404]


@pytest.mark.parametrize("location, second_path", [
    ("?", b"/start?"), ("?#part", b"/start?"), ("/a?", b"/a?"), ("/a?#part", b"/a?"),
    ("https://example.com/a?", b"/a?"), ("//example.com/a?", b"/a?"),
])
def test_httpx_transport_redirect_request_preserves_empty_query(monkeypatch, location, second_path):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **k: [
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))])
    actual_client, paths = httpx.Client, []
    def handler(request):
        paths.append(request.url.raw_path)
        return httpx.Response(302, headers={"location": location}) if len(paths) == 1 else httpx.Response(404)
    monkeypatch.setattr(httpx, "Client", lambda **kwargs: actual_client(
        transport=httpx.MockTransport(handler), **kwargs))
    result = observe("https://example.com/start?old=1")
    assert paths == [b"/start?old=1", second_path]
    assert result["status_code"] == 404 and result["outcome"] == "observed"


def test_unrequested_target_has_no_measured_elapsed_duration(network):
    routes, *_ = network
    routes["https://example.com/"] = (200, {}, [b'<a href="/a">A</a><a href="/b">B</a>'], False)
    routes["https://example.com/a"] = (200, {}, [], True)
    result = audit("https://example.com/", max_targets=1)
    skipped = result["targets"][1]
    assert skipped["elapsed_ms"] is None
    assert result["_meta"]["evidence"]["fields"]["/targets/1/elapsed_ms"]["confidence_tier"] == "unavailable"


@pytest.mark.parametrize("reference, expected", [
    ("#fragment", "https://example.com/a?#fragment"),
    ("", "https://example.com/a?"),
    ("#part?x=1", "https://example.com/a?#part?x=1"),
    ("/a", "https://example.com/a"),
    ("/b", "https://example.com/b"),
    ("?x=1", "https://example.com/a?x=1"),
    ("?", "https://example.com/a?"),
    ("/b?", "https://example.com/b?"),
])
def test_empty_base_query_inheritance_depends_on_reference(reference, expected):
    assert safety.resolve_observation_reference("https://example.com/a?", reference) == expected


@pytest.mark.parametrize("base_url, raw_path", [
    ("https://example.com/a?", b"/a?"),
    ("https://example.com/a?old=1", b"/a?old=1"),
])
def test_httpx_fragment_redirect_inherits_query_and_loops_without_second_get(monkeypatch, base_url, raw_path):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **k: [
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))])
    actual_client, paths = httpx.Client, []
    def handler(request):
        paths.append(request.url.raw_path)
        return httpx.Response(302, headers={"location": "#fragment"}) if len(paths) == 1 else httpx.Response(200)
    monkeypatch.setattr(httpx, "Client", lambda **kwargs: actual_client(
        transport=httpx.MockTransport(handler), **kwargs))
    result = observe(base_url)
    assert paths == [raw_path]
    assert result["availability_reason"] == "redirect_loop"
    assert result["status_code"] is None and result["last_observed_status"] == 302
    assert result["hops"][0]["next_url"] == base_url + "#fragment"
