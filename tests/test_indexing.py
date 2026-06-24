import json
import pytest
from unittest.mock import patch, MagicMock
from googleapiclient.errors import HttpError
from gsc_mcp.tools.indexing import submit_url, submit_batch, _submit_batch_impl
from gsc_mcp.quota import QuotaTracker

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
        result = json.loads(_submit_batch_impl(urls, "URL_UPDATED", quota))

    assert result.get("quota_warning") is True


def test_submit_batch_quota_exceeded():
    svc = _make_mock_indexing_svc()
    urls = [f"https://example.com/page-{i}" for i in range(10)]
    quota = QuotaTracker(limit=5, warn_at=4)

    with patch("gsc_mcp.tools.indexing.get_indexing_service", return_value=svc):
        with pytest.raises(RuntimeError, match="quota"):
            _submit_batch_impl(urls, "URL_UPDATED", quota)


def test_submit_batch_closure_independence():
    svc = _make_mock_indexing_svc()
    urls = ["https://example.com/a", "https://example.com/b", "https://example.com/c"]

    with patch("gsc_mcp.tools.indexing.get_indexing_service", return_value=svc):
        result = json.loads(submit_batch(urls))

    reported_urls = [r["url"] for r in result["results"]]
    assert len(set(reported_urls)) == 3
