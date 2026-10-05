import json
import runpy
from datetime import date
from pathlib import Path

import httpx
import pytest

from gsc_mcp.providers.bing import BingApiError, BingWebmasterClient, READ_METHODS
from scripts.validate_bing_live import (
    MissingConfigurationError,
    build_read_calls,
    describe_shape,
    load_config,
    main,
    run_canary,
)


def test_describe_shape_drops_values():
    secret_payload = [
        {
            "Query": "private customer query",
            "Url": "https://private.example/internal",
            "Clicks": 42,
            "Date": "/Date(1788566400000+0000)/",
        }
    ]

    result = json.dumps(describe_shape(secret_payload))

    assert "private customer query" not in result
    assert "private.example" not in result
    assert "42" not in result
    assert result == json.dumps(
        {
            "type": "list",
            "count": 1,
            "item_keys": ["Clicks", "Date", "Query", "Url"],
            "item_types": {
                "Clicks": ["int"],
                "Date": ["str"],
                "Query": ["str"],
                "Url": ["str"],
            },
        }
    )


def test_describe_shape_redacts_non_field_dictionary_keys():
    secret_payload = [
        {
            "SafeField": "private customer query",
            "https://private.example/internal": "another private value",
        }
    ]

    result = describe_shape(secret_payload)
    serialized = json.dumps(result)

    assert "private.example" not in serialized
    assert "private customer query" not in serialized
    assert result == {
        "type": "list",
        "count": 1,
        "item_keys": ["<redacted-key>"],
        "item_types": {
            "<redacted-key>": ["str"],
        },
    }


def test_describe_shape_redacts_identifier_like_unknown_field_names():
    secret_payload = [
        {
            "Clicks": 1,
            "privateCustomerQuery": "another private value",
        }
    ]

    result = describe_shape(secret_payload)
    serialized = json.dumps(result)

    assert "privateCustomerQuery" not in serialized
    assert result == {
        "type": "list",
        "count": 1,
        "item_keys": ["<redacted-key>", "Clicks"],
        "item_types": {
            "<redacted-key>": ["str"],
            "Clicks": ["int"],
        },
    }


def test_load_config_refuses_missing_or_blank_required_values():
    environment = {
        "BING_WEBMASTER_API_KEY": " ",
        "BING_TEST_SITE": "site-secret",
    }

    with pytest.raises(MissingConfigurationError) as exc_info:
        load_config(environment)

    assert exc_info.value.missing == (
        "BING_WEBMASTER_API_KEY",
        "BING_TEST_PAGE",
        "BING_TEST_FEED",
        "BING_TEST_QUERY",
    )
    assert "site-secret" not in str(exc_info.value)


def test_build_read_calls_covers_the_read_contract_with_exact_parameters():
    config = {
        "BING_WEBMASTER_API_KEY": "api-key-secret",
        "BING_TEST_SITE": "site-secret",
        "BING_TEST_PAGE": "page-secret",
        "BING_TEST_FEED": "feed-secret",
        "BING_TEST_QUERY": "query-secret",
    }

    calls = build_read_calls(config, today=date(2026, 9, 5))

    assert calls == (
        ("GetUserSites", {}),
        ("GetQueryStats", {"siteUrl": "site-secret"}),
        ("GetPageStats", {"siteUrl": "site-secret"}),
        (
            "GetPageQueryStats",
            {"siteUrl": "site-secret", "page": "page-secret"},
        ),
        ("GetRankAndTrafficStats", {"siteUrl": "site-secret"}),
        ("GetCrawlStats", {"siteUrl": "site-secret"}),
        ("GetCrawlIssues", {"siteUrl": "site-secret"}),
        ("GetCrawlSettings", {"siteUrl": "site-secret"}),
        (
            "GetUrlInfo",
            {"siteUrl": "site-secret", "url": "page-secret"},
        ),
        (
            "GetUrlTrafficInfo",
            {"siteUrl": "site-secret", "url": "page-secret"},
        ),
        ("GetFeeds", {"siteUrl": "site-secret"}),
        (
            "GetFeedDetails",
            {"siteUrl": "site-secret", "feedUrl": "feed-secret"},
        ),
        (
            "GetKeywordStats",
            {"q": "query-secret", "country": "US", "language": "en"},
        ),
        (
            "GetRelatedKeywords",
            {
                "q": "query-secret",
                "country": "US",
                "language": "en",
                "startDate": "2026-08-06",
                "endDate": "2026-09-05",
            },
        ),
        ("GetLinkCounts", {"siteUrl": "site-secret", "page": 0}),
        (
            "GetUrlLinks",
            {"siteUrl": "site-secret", "link": "page-secret", "page": 0},
        ),
        ("GetUrlSubmissionQuota", {"siteUrl": "site-secret"}),
    )


def test_build_read_calls_uses_link_parameter_for_get_url_links():
    config = {
        "BING_WEBMASTER_API_KEY": "api-key-secret",
        "BING_TEST_SITE": "site-secret",
        "BING_TEST_PAGE": "page-secret",
        "BING_TEST_FEED": "feed-secret",
        "BING_TEST_QUERY": "query-secret",
    }

    calls = build_read_calls(config, today=date(2026, 9, 5))
    params = dict(calls)["GetUrlLinks"]

    assert params == {
        "siteUrl": "site-secret",
        "link": "page-secret",
        "page": 0,
    }
    assert "url" not in params


def test_run_canary_calls_only_reads_and_never_serializes_payload_values():
    config = {
        "BING_WEBMASTER_API_KEY": "api-key-secret",
        "BING_TEST_SITE": "https://site-secret.example",
        "BING_TEST_PAGE": "https://site-secret.example/page-secret",
        "BING_TEST_FEED": "https://site-secret.example/feed-secret.xml",
        "BING_TEST_QUERY": "private customer query",
    }

    class ReadOnlyRecordingClient:
        def __init__(self):
            self.read_methods = []

        def read_with_status(self, method, params):
            self.read_methods.append(method)
            return (
                [
                    {
                        "AuthenticationCode": "authentication-secret",
                        "Clicks": 42,
                        "Date": "/Date(1788566400000+0000)/",
                        "DnsVerificationCode": "dns-secret",
                        "IsVerified": True,
                        "Query": config["BING_TEST_QUERY"],
                        "Url": config["BING_TEST_PAGE"],
                    }
                ],
                207,
            )

        def write(self, method, body):
            raise AssertionError(f"mutation attempted: {method}")

    client = ReadOnlyRecordingClient()

    report = run_canary(client, config, today=date(2026, 9, 5))
    serialized = json.dumps(report)

    assert len(client.read_methods) == 17
    assert set(client.read_methods) == READ_METHODS
    assert report["verified_site_present"] is True
    assert report["methods"][1]["http_status"] == 207
    assert report["methods"][1]["observed_min_date"] == "2026-09-05"
    assert report["methods"][1]["observed_max_date"] == "2026-09-05"
    for forbidden in (
        *config.values(),
        "authentication-secret",
        "dns-secret",
        "42",
    ):
        assert forbidden not in serialized


def test_run_canary_records_actual_success_status():
    config = {
        "BING_WEBMASTER_API_KEY": "api-key-secret",
        "BING_TEST_SITE": "site-secret",
        "BING_TEST_PAGE": "page-secret",
        "BING_TEST_FEED": "feed-secret",
        "BING_TEST_QUERY": "query-secret",
    }

    class StatusReadClient:
        def read(self, method, params):
            raise AssertionError("status-losing read path used")

        def read_with_status(self, method, params):
            payload = [{"IsVerified": True}] if method == "GetUserSites" else []
            return payload, 206

    report = run_canary(StatusReadClient(), config, today=date(2026, 9, 5))

    assert report["methods"][0]["ok"] is True
    assert report["methods"][0]["http_status"] == 206


def test_run_canary_redacts_unexpected_errors_and_continues():
    config = {
        "BING_WEBMASTER_API_KEY": "api-key-secret",
        "BING_TEST_SITE": "site-secret",
        "BING_TEST_PAGE": "page-secret",
        "BING_TEST_FEED": "feed-secret",
        "BING_TEST_QUERY": "query-secret",
    }

    class FailingReadClient:
        def __init__(self):
            self.read_methods = []

        def read_with_status(self, method, params):
            self.read_methods.append(method)
            if method == "GetPageStats":
                raise RuntimeError(
                    "private failure api-key-secret site-secret query-secret"
                )
            return [], 200

    client = FailingReadClient()

    report = run_canary(client, config, today=date(2026, 9, 5))
    failed = next(
        record for record in report["methods"] if record["method"] == "GetPageStats"
    )
    serialized = json.dumps(report)

    assert failed == {
        "method": "GetPageStats",
        "ok": False,
        "error": "unexpected_error",
    }
    assert len(client.read_methods) == 17
    for forbidden in config.values():
        assert forbidden not in serialized


def test_run_canary_keeps_only_expurgated_bing_error_metadata():
    config = {
        "BING_WEBMASTER_API_KEY": "api-key-secret",
        "BING_TEST_SITE": "site-secret",
        "BING_TEST_PAGE": "page-secret",
        "BING_TEST_FEED": "feed-secret",
        "BING_TEST_QUERY": "query-secret",
    }

    class BingErrorClient:
        def read_with_status(self, method, params):
            if method == "GetCrawlStats":
                raise BingApiError(403, method, "AccessDenied")
            return [], 200

    report = run_canary(BingErrorClient(), config, today=date(2026, 9, 5))
    failed = next(
        record for record in report["methods"] if record["method"] == "GetCrawlStats"
    )

    assert failed == {
        "method": "GetCrawlStats",
        "ok": False,
        "http_status": 403,
        "error_category": "api_error",
    }


def test_real_client_error_code_cannot_leak_private_query(monkeypatch):
    import gsc_mcp.providers.bing as bing

    config = {
        "BING_WEBMASTER_API_KEY": "api-key-secret",
        "BING_TEST_SITE": "site-secret",
        "BING_TEST_PAGE": "page-secret",
        "BING_TEST_FEED": "feed-secret",
        "BING_TEST_QUERY": "privateCustomerQuery",
    }
    real_client = httpx.Client

    def handler(request):
        return httpx.Response(
            400,
            json={"error": {"code": "privateCustomerQuery"}},
        )

    def client_factory(**kwargs):
        return real_client(transport=httpx.MockTransport(handler), **kwargs)

    monkeypatch.setattr(bing.httpx, "Client", client_factory)

    report = run_canary(
        BingWebmasterClient(config["BING_WEBMASTER_API_KEY"]),
        config,
        today=date(2026, 9, 5),
    )
    serialized = json.dumps(report)

    assert "privateCustomerQuery" not in serialized
    assert report["methods"][0] == {
        "method": "GetUserSites",
        "ok": False,
        "http_status": 400,
        "error_category": "api_error",
    }


def test_main_refuses_missing_environment_before_constructing_client(
    monkeypatch, capsys
):
    import scripts.validate_bing_live as validator

    for name in validator.REQUIRED_ENVIRONMENT:
        monkeypatch.delenv(name, raising=False)

    def fail_if_constructed(api_key):
        raise AssertionError("client construction must not happen")

    monkeypatch.setattr(validator, "BingWebmasterClient", fail_if_constructed)

    assert main() == 2
    assert json.loads(capsys.readouterr().out) == {
        "ok": False,
        "error": "missing_configuration",
        "missing": list(validator.REQUIRED_ENVIRONMENT),
    }


def test_direct_entrypoint_uses_defined_redactor_without_network(
    monkeypatch, capsys
):
    import gsc_mcp.providers.bing as bing

    environment = {
        "BING_WEBMASTER_API_KEY": "api-key-secret",
        "BING_TEST_SITE": "site-secret",
        "BING_TEST_PAGE": "page-secret",
        "BING_TEST_FEED": "feed-secret",
        "BING_TEST_QUERY": "query-secret",
    }
    for name, value in environment.items():
        monkeypatch.setenv(name, value)

    class OfflineClient:
        def __init__(self, api_key):
            assert api_key == "api-key-secret"

        def read_with_status(self, method, params):
            if method == "GetUserSites":
                return [{"IsVerified": True, "Url": "site-secret"}], 200
            return [], 200

    monkeypatch.setattr(bing, "BingWebmasterClient", OfflineClient)
    script = Path(__file__).parents[1] / "scripts" / "validate_bing_live.py"

    with pytest.raises(SystemExit) as exc_info:
        runpy.run_path(script, run_name="__main__")

    assert exc_info.value.code == 0
    serialized = capsys.readouterr().out
    assert len(json.loads(serialized)["methods"]) == 17
    for forbidden in environment.values():
        assert forbidden not in serialized
