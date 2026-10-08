"""Tests for gsc_mcp.url_safety module.

All tests are fully mocked -- no real DNS resolution or network connections.
"""
import socket
from unittest.mock import MagicMock, patch

import httpx
import pytest

import gsc_mcp.url_safety as url_safety
from gsc_mcp.url_safety import (
    URLSafetyError,
    is_safe_ip,
    normalize_hostname,
    validate_url,
    validate_url_strict,
    safe_httpx_get,
    safe_fetch_html,
    fetch_html_following_redirects,
)


class TestIsSafeIp:
    @pytest.mark.parametrize("address, expected", [
        ("93.184.216.34", True), ("8.8.8.8", True), ("100.64.0.1", False),
        ("100.127.255.254", False), ("10.0.0.1", False), ("127.0.0.1", False),
        ("169.254.169.254", False), ("224.0.0.1", False), ("192.0.2.1", False),
        ("2606:4700:4700::1111", True), ("::1", False), ("fc00::1", False),
        ("fe80::1", False), ("ff00::1", False), ("2001:db8::1", False),
    ])
    def test_public_unicast_contract_requires_global_address(self, address, expected):
        assert is_safe_ip(address) is expected

    def test_public_ipv4(self):
        assert is_safe_ip("93.184.216.34") is True

    def test_loopback(self):
        assert is_safe_ip("127.0.0.1") is False

    def test_private_10(self):
        assert is_safe_ip("10.0.0.1") is False

    def test_private_192(self):
        assert is_safe_ip("192.168.1.1") is False

    def test_link_local_metadata(self):
        assert is_safe_ip("169.254.169.254") is False

    def test_reserved(self):
        assert is_safe_ip("0.0.0.0") is False

    def test_invalid_string(self):
        assert is_safe_ip("not-an-ip") is False

    def test_private_172(self):
        assert is_safe_ip("172.16.0.1") is False


class TestNormalizeHostname:
    def test_lowercase(self):
        assert normalize_hostname("EXAMPLE.COM") == "example.com"

    def test_trailing_dot_stripped(self):
        assert normalize_hostname("example.com.") == "example.com"

    def test_decimal_ipv4_loopback(self):
        # 2130706433 == 127.0.0.1
        result = normalize_hostname("2130706433")
        assert result == "127.0.0.1"

    def test_hex_ipv4(self):
        result = normalize_hostname("0x7f000001")
        assert result == "127.0.0.1"

    def test_metadata_fqdn_trailing_dot(self):
        # metadata.google.internal. should normalize to metadata.google.internal
        result = normalize_hostname("metadata.google.internal.")
        assert result == "metadata.google.internal"

    def test_empty_raises(self):
        with pytest.raises(URLSafetyError):
            normalize_hostname("")


class TestValidateUrl:
    def test_valid_https(self):
        assert validate_url("https://example.com/page") is True

    def test_valid_http(self):
        assert validate_url("http://example.com/") is True

    def test_ftp_rejected(self):
        assert validate_url("ftp://example.com/") is False

    def test_localhost_rejected(self):
        assert validate_url("http://localhost/") is False

    def test_metadata_endpoint_ipv4(self):
        assert validate_url("http://169.254.169.254/latest/meta-data/") is False

    def test_metadata_hostname(self):
        assert validate_url("http://metadata.google.internal/") is False

    def test_decimal_encoded_loopback(self):
        # 2130706433 == 127.0.0.1
        assert validate_url("http://2130706433/") is False

    def test_hex_encoded_loopback(self):
        assert validate_url("http://0x7f000001/") is False

    def test_fqdn_trailing_dot_metadata_bypass(self):
        # metadata.google.internal. (trailing dot) must still be blocked
        assert validate_url("http://metadata.google.internal./") is False

    def test_userinfo_rejected(self):
        assert validate_url("http://user:pass@example.com/") is False

    def test_no_hostname(self):
        assert validate_url("http:///path") is False

    def test_private_ip_literal_rejected(self):
        assert validate_url("http://10.0.0.1/") is False

    def test_public_ip_literal_accepted(self):
        assert validate_url("http://93.184.216.34/") is True


class TestValidateUrlStrict:
    def test_valid_url_resolves(self):
        fake_addrinfo = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 80))]
        with patch("socket.getaddrinfo", return_value=fake_addrinfo):
            url, ip = validate_url_strict("http://example.com/")
        assert ip == "93.184.216.34"

    def test_private_ip_blocks(self):
        fake_addrinfo = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("192.168.1.1", 80))]
        with patch("socket.getaddrinfo", return_value=fake_addrinfo):
            with pytest.raises(URLSafetyError, match="non-public IP"):
                validate_url_strict("http://internal.example.com/")

    def test_dns_failure_raises(self):
        with patch("socket.getaddrinfo", side_effect=socket.gaierror("NXDOMAIN")):
            with pytest.raises(URLSafetyError, match="DNS resolution failed"):
                validate_url_strict("http://nonexistent.invalid/")

    def test_metadata_blocked_before_dns(self):
        with patch("socket.getaddrinfo") as mock_dns:
            with pytest.raises(URLSafetyError, match="Blocked hostname"):
                validate_url_strict("http://metadata.google.internal/")
            mock_dns.assert_not_called()

    def test_ip_literal_private_blocked(self):
        with pytest.raises(URLSafetyError, match="Blocked IP literal"):
            validate_url_strict("http://10.0.0.1/")

    def test_ip_literal_public_accepted(self):
        url, ip = validate_url_strict("http://93.184.216.34/")
        assert ip == "93.184.216.34"

    def test_metadata_ipv4_literal_blocked(self):
        with pytest.raises(URLSafetyError):
            validate_url_strict("http://169.254.169.254/")


class TestValidateSameOrigin:
    def test_accepts_same_https_origin(self):
        url_safety.validate_same_origin(
            "https://example.com",
            "https://example.com/a",
        )

    def test_accepts_explicit_default_https_port(self):
        url_safety.validate_same_origin(
            "https://example.com:443",
            "https://example.com/a",
        )

    @pytest.mark.parametrize(
        "candidate",
        [
            "https://sub.example.com/a",
            "https://example.com.evil.test/a",
            "https://example.com:444/a",
            "http://example.com/a",
            "https://user:pass@example.com/a",
        ],
    )
    def test_rejects_candidate_outside_exact_origin(self, candidate):
        with pytest.raises(URLSafetyError):
            url_safety.validate_same_origin("https://example.com", candidate)

    def test_malformed_candidate_raises_safety_error(self):
        with pytest.raises(URLSafetyError):
            url_safety.validate_same_origin(
                "https://example.com",
                "https://[malformed",
            )

    @pytest.mark.parametrize(
        "site",
        [
            "http://example.com",
            "https://example.com/path",
            "https://example.com?query=1",
            "https://example.com?",
            "https://example.com#fragment",
            "https://example.com#",
            "https://user:pass@example.com",
        ],
    )
    def test_rejects_site_that_is_not_a_plain_https_origin(self, site):
        with pytest.raises(URLSafetyError):
            url_safety.validate_same_origin(site, "https://example.com/a")

    def test_candidate_may_contain_query_and_fragment(self):
        url_safety.validate_same_origin(
            "https://example.com",
            "https://example.com/a?query=1#fragment",
        )

    def test_does_not_resolve_dns(self):
        with patch("socket.getaddrinfo") as mock_dns:
            url_safety.validate_same_origin(
                "https://example.com",
                "https://example.com/a",
            )
        mock_dns.assert_not_called()


class TestSafeHttpxGet:
    def test_calls_httpx_with_pinned_dns(self):
        fake_addrinfo = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 80))]
        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("socket.getaddrinfo", return_value=fake_addrinfo):
            with patch("httpx.Client") as mock_client_cls:
                mock_client = MagicMock()
                mock_client.__enter__ = MagicMock(return_value=mock_client)
                mock_client.__exit__ = MagicMock(return_value=False)
                mock_client.get.return_value = mock_response
                mock_client_cls.return_value = mock_client

                resp = safe_httpx_get("http://example.com/")
                assert resp.status_code == 200

    def test_blocked_url_raises(self):
        with pytest.raises(URLSafetyError):
            safe_httpx_get("http://169.254.169.254/")

    def test_private_hostname_raises(self):
        with pytest.raises(URLSafetyError):
            safe_httpx_get("http://localhost/")


class TestSafeFetchHtml:
    def test_returns_html_and_status(self):
        fake_addrinfo = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 80))]
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html><head><title>Test</title></head></html>"

        with patch("socket.getaddrinfo", return_value=fake_addrinfo):
            with patch("httpx.Client") as mock_client_cls:
                mock_client = MagicMock()
                mock_client.__enter__ = MagicMock(return_value=mock_client)
                mock_client.__exit__ = MagicMock(return_value=False)
                mock_client.get.return_value = mock_response
                mock_client_cls.return_value = mock_client

                html, status = safe_fetch_html("http://example.com/")
                assert status == 200
                assert "Test" in html

    def test_blocked_url_raises_safety_error(self):
        with pytest.raises(URLSafetyError):
            safe_fetch_html("http://169.254.169.254/")


class TestFetchHtmlFollowingRedirects:
    """Bounded, same-site redirect following on top of safe_fetch_html."""

    @staticmethod
    def _client(responses: dict[str, tuple[int, dict]]):
        def fake_get(url, **_):
            status, headers = responses[url]
            return httpx.Response(status, headers=headers, text="<html></html>",
                                  request=httpx.Request("GET", url))
        client = MagicMock()
        client.__enter__ = MagicMock(return_value=client)
        client.__exit__ = MagicMock(return_value=False)
        client.get.side_effect = fake_get
        return client

    @pytest.fixture(autouse=True)
    def _public_dns(self):
        fake = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 80))]
        with patch("socket.getaddrinfo", return_value=fake):
            yield

    @pytest.mark.parametrize("status", [301, 302, 303, 307, 308])
    def test_follows_redirect_statuses(self, status):
        client = self._client({
            "http://example.com/": (status, {"location": "https://example.com/"}),
            "https://example.com/": (200, {}),
        })
        with patch("httpx.Client", return_value=client):
            _html, code, final = fetch_html_following_redirects("http://example.com/")
        assert code == 200
        assert final == "https://example.com/"

    @pytest.mark.parametrize("status", [304, 404, 500])
    def test_location_on_non_redirect_status_is_not_followed(self, status):
        client = self._client({
            "https://example.com/": (status, {"location": "https://example.com/other"}),
        })
        with patch("httpx.Client", return_value=client):
            with pytest.raises(httpx.HTTPStatusError):
                fetch_html_following_redirects("https://example.com/")
        assert client.get.call_count == 1

    def test_www_prefix_is_same_site(self):
        client = self._client({
            "https://www.example.com/": (301, {"location": "https://example.com/"}),
            "https://example.com/": (200, {}),
        })
        with patch("httpx.Client", return_value=client):
            _html, code, final = fetch_html_following_redirects("https://www.example.com/")
        assert code == 200
        assert final == "https://example.com/"

    def test_cross_host_redirect_raises(self):
        client = self._client({
            "https://example.com/": (301, {"location": "https://evil.example.net/"}),
        })
        with patch("httpx.Client", return_value=client):
            with pytest.raises(URLSafetyError, match="Cross-site redirect refused"):
                fetch_html_following_redirects("https://example.com/")
        assert client.get.call_count == 1

    @pytest.mark.parametrize("target", ["https://example.com:not-a-port/", "https://[::1/"])
    def test_malformed_location_raises_url_safety_error(self, target):
        client = self._client({
            "https://example.com/": (301, {"location": target}),
        })
        with patch("httpx.Client", return_value=client):
            with pytest.raises(URLSafetyError, match="invalid port or authority"):
                fetch_html_following_redirects("https://example.com/")
        assert client.get.call_count == 1

    def test_subdomain_is_not_same_site(self):
        client = self._client({
            "https://example.com/": (301, {"location": "https://cdn.example.com/"}),
        })
        with patch("httpx.Client", return_value=client):
            with pytest.raises(URLSafetyError, match="Cross-site redirect refused"):
                fetch_html_following_redirects("https://example.com/")


class TestRedirectObserverDNS:
    """Keep URL validation/pinning real; replace only external resolver/HTTP transport."""

    @staticmethod
    def _budget():
        import time
        return url_safety.FetchObservationBudget(20, time.monotonic() + 60)

    def test_connection_dns_is_pinned_against_second_answer(self, monkeypatch):
        calls, connection_ips = [], []
        def resolver(*args, **kwargs):
            calls.append(args)
            ip = "93.184.216.34" if len(calls) == 1 else "10.0.0.1"
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, 443))]
        monkeypatch.setattr(socket, "getaddrinfo", resolver)
        actual_client = httpx.Client
        def handle(request):
            connection_ips.append(socket.getaddrinfo(request.url.host, 443)[0][4][0])
            return httpx.Response(200)
        monkeypatch.setattr(httpx, "Client", lambda **kwargs: actual_client(
            transport=httpx.MockTransport(handle), **kwargs))
        result = url_safety.observe_get_redirects("https://example.com/a", site_url="https://example.com/", budget=self._budget())
        assert result["status_code"] == 200
        assert connection_ips == ["93.184.216.34"] and len(calls) == 1
        assert socket.getaddrinfo is resolver

    def test_same_host_redirect_gets_fresh_dns_validation(self, monkeypatch):
        calls, sent = [], []
        def resolver(*args, **kwargs):
            calls.append(args)
            ip = "93.184.216.34" if len(calls) == 1 else "10.0.0.1"
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, 443))]
        monkeypatch.setattr(socket, "getaddrinfo", resolver)
        actual_client = httpx.Client
        def handle(request):
            sent.append(str(request.url))
            return httpx.Response(301, headers={"location": "/b"})
        monkeypatch.setattr(httpx, "Client", lambda **kwargs: actual_client(
            transport=httpx.MockTransport(handle), **kwargs))
        budget = self._budget()
        result = url_safety.observe_get_redirects("https://example.com/a", site_url="https://example.com/", budget=budget)
        assert result["availability_reason"] == "dns_refused"
        assert result["last_observed_status"] == 301 and result["status_code"] is None
        assert result["last_requested_url"] == "https://example.com/a"
        assert sent == ["https://example.com/a"] and len(calls) == 2
        assert budget.requests_started == 1 and budget.dns_refusals == 1

    def test_mixed_dns_answers_are_refused_before_http(self, monkeypatch):
        monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **k: [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443)),
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.1", 443)),
        ])
        with patch("httpx.Client") as client:
            result = url_safety.observe_get_redirects("https://example.com/a", site_url="https://example.com/", budget=self._budget())
        assert result["availability_reason"] == "dns_refused"
        assert result["attempted"] is False
        client.assert_not_called()

    def test_environment_proxy_cannot_send_credentials(self, monkeypatch):
        monkeypatch.setenv("HTTP_PROXY", "http://user:secret@127.0.0.1:8888")
        monkeypatch.setenv("HTTPS_PROXY", "http://user:secret@127.0.0.1:8888")
        monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **k: [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))])
        actual_client, requests = httpx.Client, []
        def factory(**kwargs):
            assert kwargs["trust_env"] is False and kwargs["follow_redirects"] is False
            def handler(request):
                requests.append(request)
                return httpx.Response(200)
            return actual_client(transport=httpx.MockTransport(handler), **kwargs)
        monkeypatch.setattr(httpx, "Client", factory)
        result = url_safety.observe_get_redirects("https://example.com/a", site_url="https://example.com/", budget=self._budget())
        assert result["status_code"] == 200
        assert requests[0].headers["accept-encoding"] == "identity"
        assert "authorization" not in requests[0].headers and "proxy-authorization" not in requests[0].headers

    def test_pin_lock_contention_is_unavailable_without_started_request(self, monkeypatch):
        monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **k: [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))])
        budget = self._budget()
        with url_safety._pin_dns("example.com", "93.184.216.34", 443):
            result = url_safety.observe_get_redirects("https://example.com/a", site_url="https://example.com/", budget=budget)
        assert result["availability_reason"] == "dns_pin_unavailable"
        assert result["attempted"] is False and budget.requests_started == 0


    @pytest.mark.parametrize("url", ["https://100.64.0.1/", "https://100.127.255.254/"])
    def test_observer_refuses_non_global_literal_without_http(self, url):
        with patch("httpx.Client") as client, patch("socket.getaddrinfo") as dns:
            result = url_safety.observe_get_redirects(url, site_url=url, budget=self._budget())
        assert result["outcome"] == "unavailable" and result["availability_reason"] == "unsafe_url"
        assert result["attempted"] is False and result["status_code"] is None
        client.assert_not_called()
        dns.assert_not_called()

    @pytest.mark.parametrize("addresses", [["100.64.0.1"], ["93.184.216.34", "100.64.0.1"]])
    def test_observer_refuses_every_non_global_dns_answer_including_mixed_set(self, monkeypatch, addresses):
        monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **k: [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, 443)) for ip in addresses])
        with patch("httpx.Client") as client:
            result = url_safety.observe_get_redirects("https://example.com/a", site_url="https://example.com/", budget=self._budget())
        assert result["availability_reason"] == "dns_refused" and result["attempted"] is False
        assert result["status_code"] is None
        client.assert_not_called()

    def test_non_global_dns_redirect_retains_predecessor_without_second_http(self, monkeypatch):
        calls, sent = [], []
        def resolver(*args, **kwargs):
            calls.append(args)
            addresses = ["93.184.216.34"] if len(calls) == 1 else ["93.184.216.34", "100.64.0.1"]
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, 443)) for ip in addresses]
        monkeypatch.setattr(socket, "getaddrinfo", resolver)
        actual_client = httpx.Client
        def handler(request):
            sent.append(str(request.url))
            return httpx.Response(302, headers={"location": "/b"})
        monkeypatch.setattr(httpx, "Client", lambda **kwargs: actual_client(
            transport=httpx.MockTransport(handler), **kwargs))
        result = url_safety.observe_get_redirects("https://example.com/a", site_url="https://example.com/", budget=self._budget())
        assert result["availability_reason"] == "dns_refused"
        assert result["last_observed_status"] == 302 and result["status_code"] is None
        assert sent == ["https://example.com/a"] and len(calls) == 2
