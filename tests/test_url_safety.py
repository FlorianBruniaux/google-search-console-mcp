"""Tests for gsc_mcp.url_safety module.

All tests are fully mocked -- no real DNS resolution or network connections.
"""
import socket
from unittest.mock import MagicMock, patch

import pytest

from gsc_mcp.url_safety import (
    URLSafetyError,
    is_safe_ip,
    normalize_hostname,
    validate_url,
    validate_url_strict,
    safe_httpx_get,
    safe_fetch_html,
)


class TestIsSafeIp:
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
