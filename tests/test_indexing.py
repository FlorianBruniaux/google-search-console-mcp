import json
import httpx
import pytest
from unittest.mock import patch, MagicMock
from googleapiclient.errors import HttpError
import gsc_mcp.tools.indexing as indexing
from gsc_mcp.tools.indexing import indexnow_submit, submit_url, submit_batch
from gsc_mcp.quota import QuotaTracker
from gsc_mcp.url_safety import URLSafetyError

URL = "https://example.com/page"
SITE = "https://example.com/"


def _make_mock_indexing_svc():
    svc = MagicMock()
    svc.urlNotifications.return_value.publish.return_value.execute.return_value = {
        "urlNotificationMetadata": {"url": URL, "latestUpdate": {"type": "URL_UPDATED"}}
    }

    batch_call_count = {"n": 0}

    def new_batch(**kwargs):
        batch_call_count["n"] += 1
        batch = MagicMock()
        batch._added = []

        def add(request, request_id=None, callback=None):
            batch._added.append((request_id, callback))

        batch.add = add

        def execute():
            for req_id, cb in batch._added:
                if cb:
                    cb(req_id, {"status": "OK"}, None)

        batch.execute = execute
        return batch

    svc.new_batch_http_request = new_batch
    svc._batch_call_count = batch_call_count
    return svc


def _make_indexnow_client(status_code: int = 200):
    response = MagicMock()
    response.status_code = status_code
    client = MagicMock()
    client.__enter__ = MagicMock(return_value=client)
    client.__exit__ = MagicMock(return_value=False)
    client.post.return_value = response
    return client


def test_submit_url(mock_indexing_service):
    mock_indexing_service.urlNotifications.return_value.publish.return_value.execute.return_value = {
        "urlNotificationMetadata": {"url": URL}
    }
    with patch("gsc_mcp.tools.indexing.get_indexing_service", return_value=mock_indexing_service):
        result = json.loads(submit_url(URL))

    assert result["url"] == URL
    assert result["status"] == "submitted"
    assert result["type"] == "URL_UPDATED"
    assert "_meta" in result


def test_submit_url_retries_on_429(mock_indexing_service):
    resp = MagicMock()
    resp.status = 429
    http_error = HttpError(resp=resp, content=b"Too Many Requests")

    execute_mock = mock_indexing_service.urlNotifications.return_value.publish.return_value.execute
    execute_mock.side_effect = [http_error, http_error, {"urlNotificationMetadata": {"url": URL}}]

    with patch("gsc_mcp.tools.indexing.get_indexing_service", return_value=mock_indexing_service):
        with patch("gsc_mcp.retry.time.sleep"):
            result = json.loads(submit_url(URL))

    assert result["status"] == "submitted"
    assert execute_mock.call_count == 3


def test_submit_url_credentials_error_propagates():
    with patch(
        "gsc_mcp.tools.indexing.get_indexing_service",
        side_effect=RuntimeError("No credentials"),
    ):
        with pytest.raises(RuntimeError, match="No credentials"):
            submit_url(URL)


def test_submit_batch_true_http_batch():
    svc = _make_mock_indexing_svc()
    urls = [f"https://example.com/page-{i}" for i in range(5)]

    with patch("gsc_mcp.tools.indexing.get_indexing_service", return_value=svc):
        result = json.loads(submit_batch(urls))

    assert result["submitted"] == 5
    assert result["errors"] == 0
    assert "_meta" in result
    assert svc._batch_call_count["n"] == 1


def test_submit_batch_chunks_at_100():
    svc = _make_mock_indexing_svc()
    urls = [f"https://example.com/page-{i}" for i in range(150)]

    with patch("gsc_mcp.tools.indexing.get_indexing_service", return_value=svc):
        result = json.loads(submit_batch(urls))

    assert svc._batch_call_count["n"] == 2
    assert result["submitted"] == 150


def test_submit_batch_quota_check():
    svc = _make_mock_indexing_svc()
    urls = [f"https://example.com/page-{i}" for i in range(5)]
    quota = QuotaTracker(limit=200, warn_at=13)
    quota.consume(13)

    with patch("gsc_mcp.tools.indexing.get_indexing_service", return_value=svc):
        with patch("gsc_mcp.tools.indexing._default_quota", quota):
            result = json.loads(submit_batch(urls, "URL_UPDATED"))

    assert result.get("quota_warning") is True


def test_submit_batch_quota_exceeded():
    svc = _make_mock_indexing_svc()
    urls = [f"https://example.com/page-{i}" for i in range(10)]
    quota = QuotaTracker(limit=5, warn_at=4)

    with patch("gsc_mcp.tools.indexing.get_indexing_service", return_value=svc):
        with patch("gsc_mcp.tools.indexing._default_quota", quota):
            with pytest.raises(RuntimeError, match="quota"):
                submit_batch(urls, "URL_UPDATED")


def test_submit_batch_closure_independence():
    svc = _make_mock_indexing_svc()
    urls = ["https://example.com/a", "https://example.com/b", "https://example.com/c"]

    with patch("gsc_mcp.tools.indexing.get_indexing_service", return_value=svc):
        result = json.loads(submit_batch(urls))

    reported_urls = [r["url"] for r in result["results"]]
    assert len(set(reported_urls)) == 3


@pytest.mark.parametrize(
    "key",
    [
        "aB3-5678",
        "a" * 128,
    ],
)
def test_validate_indexnow_key_accepts_protocol_alphabet_and_boundaries(key):
    indexing.validate_indexnow_key(key)


@pytest.mark.parametrize(
    "key",
    [
        "a" * 7,
        "a" * 129,
        "abc defgh",
        "abc/defgh",
        "abc_defgh",
        "abc.defgh",
    ],
)
def test_validate_indexnow_key_rejects_invalid_values(key):
    with pytest.raises(ValueError):
        indexing.validate_indexnow_key(key)


def test_indexnow_rejects_invalid_key_before_url_validation_or_http():
    with patch("gsc_mcp.tools.indexing.validate_url_strict") as strict, \
         patch("gsc_mcp.tools.indexing.httpx.Client") as client:
        with pytest.raises(ValueError):
            indexnow_submit(
                "https://example.com",
                "short",
                ["https://example.com/a"],
            )
    strict.assert_not_called()
    client.assert_not_called()


def test_indexnow_rejects_empty_url_list_without_http():
    with patch("gsc_mcp.tools.indexing.httpx.Client") as client:
        with pytest.raises(ValueError):
            indexnow_submit("https://example.com", "valid-key", [])
    client.assert_not_called()


def test_indexnow_accepts_ten_thousand_urls():
    urls = ["https://example.com/a"] * 10_000
    client = _make_indexnow_client(200)
    with patch(
        "gsc_mcp.tools.indexing.validate_url_strict",
        side_effect=lambda url: (url, "93.184.216.34"),
    ), patch("gsc_mcp.tools.indexing.httpx.Client", return_value=client):
        result = json.loads(indexnow_submit("https://example.com", "valid-key", urls))

    assert result["submitted"] == 10_000
    client.post.assert_called_once()


def test_indexnow_rejects_more_than_ten_thousand_urls_without_http():
    urls = ["https://example.com/a"] * 10_001
    with patch("gsc_mcp.tools.indexing.httpx.Client") as client:
        with pytest.raises(ValueError):
            indexnow_submit("https://example.com", "valid-key", urls)
    client.assert_not_called()


def test_indexnow_counts_invalid_and_cross_origin_urls():
    client = _make_indexnow_client(200)
    urls = [
        "https://example.com/ok",
        "https://sub.example.com/wrong-origin",
        "https://private.example.com/blocked",
    ]

    def validate(url):
        if "private" in url:
            raise URLSafetyError("blocked")
        return url, "93.184.216.34"

    with patch("gsc_mcp.tools.indexing.validate_url_strict", side_effect=validate), \
         patch("gsc_mcp.tools.indexing.httpx.Client", return_value=client):
        result = json.loads(indexnow_submit("https://example.com", "valid-key", urls))

    assert result["submitted"] == 1
    assert result["skipped_invalid"] == 2
    assert result["verdict"] == "partial"


def test_indexnow_does_not_post_when_all_urls_are_invalid():
    with patch(
        "gsc_mcp.tools.indexing.validate_url_strict",
        side_effect=URLSafetyError("blocked"),
    ), patch("gsc_mcp.tools.indexing.httpx.Client") as client:
        result = json.loads(indexnow_submit(
            "https://example.com",
            "valid-key",
            ["https://private.example.com/a"],
        ))

    assert result["status"] == "error"
    assert result["submitted"] == 0
    assert result["skipped_invalid"] == 1
    client.assert_not_called()


def test_indexnow_counts_malformed_url_as_invalid():
    with patch("gsc_mcp.tools.indexing.httpx.Client") as client:
        result = json.loads(indexnow_submit(
            "https://example.com",
            "valid-key",
            ["https://[malformed"],
        ))

    assert result["status"] == "error"
    assert result["skipped_invalid"] == 1
    client.assert_not_called()


@pytest.mark.parametrize(
    "site",
    [
        "http://example.com",
        "https://example.com/path",
        "https://example.com?query=1",
        "https://example.com#fragment",
    ],
)
def test_indexnow_rejects_invalid_site_origin_without_http(site):
    with patch("gsc_mcp.tools.indexing.httpx.Client") as client:
        with pytest.raises(URLSafetyError):
            indexnow_submit(site, "valid-key", ["https://example.com/a"])
    client.assert_not_called()


@pytest.mark.parametrize(
    ("status_code", "key_validation"),
    [(200, "verified"), (202, "pending")],
)
def test_indexnow_received_status_does_not_claim_indexation(status_code, key_validation):
    client = _make_indexnow_client(status_code)
    with patch(
        "gsc_mcp.tools.indexing.validate_url_strict",
        side_effect=lambda url: (url, "93.184.216.34"),
    ), patch("gsc_mcp.tools.indexing.httpx.Client", return_value=client):
        serialized = indexnow_submit(
            "https://example.com",
            "valid-key",
            ["https://example.com/a"],
        )
    result = json.loads(serialized)

    assert result["status"] == "received"
    assert result["key_validation"] == key_validation
    assert "indexed" not in serialized.lower()
    assert "valid-key" not in serialized


@pytest.mark.parametrize("status_code", [400, 403, 422, 429])
def test_indexnow_protocol_rejections_return_only_status_code(status_code):
    client = _make_indexnow_client(status_code)
    client.post.return_value.text = "arbitrary upstream body with valid-key"
    with patch(
        "gsc_mcp.tools.indexing.validate_url_strict",
        side_effect=lambda url: (url, "93.184.216.34"),
    ), patch("gsc_mcp.tools.indexing.httpx.Client", return_value=client):
        serialized = indexnow_submit(
            "https://example.com",
            "valid-key",
            ["https://example.com/a"],
        )
    result = json.loads(serialized)

    assert result["status"] == "rejected"
    assert result["status_code"] == status_code
    assert "arbitrary upstream body" not in serialized
    assert "valid-key" not in serialized


def test_indexnow_timeout_returns_redacted_stable_category():
    client = _make_indexnow_client()
    client.post.side_effect = httpx.TimeoutException(
        "timeout for https://internal.example/valid-key"
    )
    with patch(
        "gsc_mcp.tools.indexing.validate_url_strict",
        side_effect=lambda url: (url, "93.184.216.34"),
    ), patch("gsc_mcp.tools.indexing.httpx.Client", return_value=client):
        serialized = indexnow_submit(
            "https://example.com",
            "valid-key",
            ["https://example.com/a"],
        )
    result = json.loads(serialized)

    assert result["status"] == "error"
    assert result["error_category"] == "timeout"
    assert "internal.example" not in serialized
    assert "valid-key" not in serialized


def test_indexnow_network_error_returns_redacted_stable_category():
    client = _make_indexnow_client()
    client.post.side_effect = httpx.ConnectError(
        "connection failed for https://internal.example/valid-key"
    )
    with patch(
        "gsc_mcp.tools.indexing.validate_url_strict",
        side_effect=lambda url: (url, "93.184.216.34"),
    ), patch("gsc_mcp.tools.indexing.httpx.Client", return_value=client):
        serialized = indexnow_submit(
            "https://example.com",
            "valid-key",
            ["https://example.com/a"],
        )
    result = json.loads(serialized)

    assert result["status"] == "error"
    assert result["error_category"] == "transport_error"
    assert "internal.example" not in serialized
    assert "valid-key" not in serialized
