from unittest.mock import MagicMock

import httpx
import pytest

from gsc_mcp.auth import get_bing_api_key
from gsc_mcp.providers.bing import (
    BingApiError,
    BingWebmasterClient,
    get_bing_client,
    parse_bing_date,
)


def _mock_http_client(monkeypatch, *responses):
    transport = MagicMock()
    transport.get.side_effect = list(responses)
    transport.post.side_effect = list(responses)
    client_cm = MagicMock()
    client_cm.__enter__.return_value = transport
    client_factory = MagicMock(return_value=client_cm)
    monkeypatch.setattr("gsc_mcp.providers.bing.httpx.Client", client_factory)
    return transport, client_factory


def test_get_bing_api_key_requires_env(monkeypatch):
    monkeypatch.delenv("BING_WEBMASTER_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="BING_WEBMASTER_API_KEY"):
        get_bing_api_key()


def test_get_bing_api_key_strips_env(monkeypatch):
    monkeypatch.setenv("BING_WEBMASTER_API_KEY", "  secret-key  ")

    assert get_bing_api_key() == "secret-key"


def test_get_bing_client_uses_env_key(monkeypatch):
    monkeypatch.setenv("BING_WEBMASTER_API_KEY", "secret-key")

    client = get_bing_client()

    assert isinstance(client, BingWebmasterClient)


def test_read_unwraps_d_and_strips_type_recursively(monkeypatch):
    response = MagicMock(status_code=200)
    response.json.return_value = {
        "d": [
            {
                "__type": "Site:#Microsoft.Bing.Webmaster.Api",
                "Url": "https://example.com",
                "Nested": {"__type": "Nested", "Value": 1},
            }
        ]
    }
    transport, client_factory = _mock_http_client(monkeypatch, response)

    result = BingWebmasterClient("secret-key").read("GetUserSites", {})

    assert result == [
        {"Url": "https://example.com", "Nested": {"Value": 1}}
    ]
    client_factory.assert_called_once_with(timeout=15, follow_redirects=False)
    transport.get.assert_called_once_with(
        "https://ssl.bing.com/webmaster/api.svc/json/GetUserSites",
        params={"apikey": "secret-key"},
    )


def test_write_posts_json_and_unwraps_d(monkeypatch):
    response = MagicMock(status_code=200)
    response.json.return_value = {"d": {"Submitted": True, "__type": "Result"}}
    transport, _ = _mock_http_client(monkeypatch, response)

    result = BingWebmasterClient("secret-key").write(
        "SubmitUrl", {"siteUrl": "https://example.com"}
    )

    assert result == {"Submitted": True}
    transport.post.assert_called_once_with(
        "https://ssl.bing.com/webmaster/api.svc/json/SubmitUrl",
        params={"apikey": "secret-key"},
        json={"siteUrl": "https://example.com"},
    )


def test_error_never_contains_api_key(monkeypatch):
    response = MagicMock(status_code=401)
    response.json.return_value = {
        "error": {"code": "InvalidApiKey", "message": "denied"}
    }
    _mock_http_client(monkeypatch, response)

    with pytest.raises(BingApiError) as exc_info:
        BingWebmasterClient("secret-key").read("GetUserSites", {})

    error = exc_info.value
    assert "secret-key" not in str(error)
    assert error.status_code == 401
    assert error.method == "GetUserSites"
    assert error.code == "InvalidApiKey"


def test_read_retries_429_without_logging_key(monkeypatch):
    throttled = MagicMock(status_code=429)
    throttled.json.return_value = {"error": {"code": "ThrottleUser"}}
    ok = MagicMock(status_code=200)
    ok.json.return_value = {"d": []}
    transport, _ = _mock_http_client(monkeypatch, throttled, ok)
    sleep = MagicMock()
    monkeypatch.setattr("gsc_mcp.providers.bing.time.sleep", sleep)

    assert BingWebmasterClient("secret-key").read("GetUserSites", {}) == []
    assert transport.get.call_count == 2
    sleep.assert_called_once()


def test_read_retries_500_response(monkeypatch):
    failed = MagicMock(status_code=500)
    failed.json.return_value = {"error": {"code": "InternalError"}}
    ok = MagicMock(status_code=200)
    ok.json.return_value = {"d": {"ok": True}}
    transport, _ = _mock_http_client(monkeypatch, failed, ok)
    monkeypatch.setattr("gsc_mcp.providers.bing.time.sleep", MagicMock())

    assert BingWebmasterClient("secret-key").read("GetUserSites", {}) == {"ok": True}
    assert transport.get.call_count == 2


def test_read_stops_after_three_retries(monkeypatch):
    responses = []
    for _ in range(4):
        failed = MagicMock(status_code=503)
        failed.json.return_value = {"error": {"code": "Unavailable"}}
        responses.append(failed)
    transport, _ = _mock_http_client(monkeypatch, *responses)
    sleep = MagicMock()
    monkeypatch.setattr("gsc_mcp.providers.bing.time.sleep", sleep)

    with pytest.raises(BingApiError) as exc_info:
        BingWebmasterClient("secret-key").read("GetUserSites", {})

    assert transport.get.call_count == 4
    assert sleep.call_count == 3
    assert exc_info.value.status_code == 503


def test_read_does_not_retry_404(monkeypatch):
    missing = MagicMock(status_code=404)
    missing.json.return_value = {"error": {"code": "NotFound"}}
    transport, _ = _mock_http_client(monkeypatch, missing)
    sleep = MagicMock()
    monkeypatch.setattr("gsc_mcp.providers.bing.time.sleep", sleep)

    with pytest.raises(BingApiError) as exc_info:
        BingWebmasterClient("secret-key").read("GetUserSites", {})

    assert transport.get.call_count == 1
    sleep.assert_not_called()
    assert exc_info.value.status_code == 404
    assert exc_info.value.code == "NotFound"


def test_timeout_is_expurgated_and_not_retried(monkeypatch):
    request = httpx.Request(
        "GET",
        "https://ssl.bing.com/webmaster/api.svc/json/GetUserSites",
        params={"apikey": "secret-key"},
    )
    transport, _ = _mock_http_client(
        monkeypatch, httpx.ReadTimeout("timed out", request=request)
    )

    with pytest.raises(BingApiError) as exc_info:
        BingWebmasterClient("secret-key").read("GetUserSites", {})

    assert transport.get.call_count == 1
    assert exc_info.value.status_code is None
    assert exc_info.value.code == "Timeout"
    assert "secret-key" not in str(exc_info.value)
    assert exc_info.value.__cause__ is None
    assert exc_info.value.__context__ is None


def test_invalid_json_is_expurgated(monkeypatch):
    response = MagicMock(status_code=200)
    response.json.side_effect = ValueError("invalid response")
    _mock_http_client(monkeypatch, response)

    with pytest.raises(BingApiError) as exc_info:
        BingWebmasterClient("secret-key").read("GetUserSites", {})

    assert exc_info.value.status_code == 200
    assert exc_info.value.code == "InvalidJson"
    assert "secret-key" not in str(exc_info.value)


@pytest.mark.parametrize(
    ("operation", "method"),
    [
        ("read", "SubmitUrl"),
        ("read", "UnknownMethod"),
        ("write", "GetUserSites"),
        ("write", "UnknownMethod"),
    ],
)
def test_method_outside_operation_allowlist_is_rejected(monkeypatch, operation, method):
    client_factory = MagicMock()
    monkeypatch.setattr("gsc_mcp.providers.bing.httpx.Client", client_factory)

    with pytest.raises(ValueError, match="not allowed"):
        getattr(BingWebmasterClient("secret-key"), operation)(method, {})

    client_factory.assert_not_called()


def test_read_returns_none_for_null_d(monkeypatch):
    response = MagicMock(status_code=200)
    response.json.return_value = {"d": None}
    _mock_http_client(monkeypatch, response)

    assert BingWebmasterClient("secret-key").read("GetUserSites", {}) is None


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("/Date(1316156400000-0700)/", "2011-09-16"),
        ("2026-09-05T00:00:00Z", "2026-09-05"),
        (None, None),
    ],
)
def test_parse_bing_date(raw, expected):
    assert parse_bing_date(raw) == expected
