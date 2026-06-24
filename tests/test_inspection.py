import json
import pytest
from unittest.mock import patch, MagicMock, call
from googleapiclient.errors import HttpError
from gsc_mcp.tools.inspection import inspect_url, batch_url_inspection, check_indexing_issues

SITE = "https://example.com/"
URL = "https://example.com/page"


def _mock_inspect_response(verdict="PASS", robots_txt_state="ALLOWED", indexing_state="INDEXING_ALLOWED"):
    return {
        "inspectionResult": {
            "indexStatusResult": {
                "verdict": verdict,
                "robotsTxtState": robots_txt_state,
                "indexingState": indexing_state,
                "lastCrawlTime": "2024-01-01T00:00:00Z",
                "pageFetchState": "SUCCESSFUL",
                "googleCanonical": URL,
                "userCanonical": URL,
            }
        }
    }


def test_inspect_url_indexed(mock_gsc_service):
    mock_gsc_service.urlInspection.return_value.index.return_value.inspect.return_value.execute.return_value = (
        _mock_inspect_response()
    )
    with patch("gsc_mcp.tools.inspection.get_searchconsole_service", return_value=mock_gsc_service):
        result = json.loads(inspect_url(URL, SITE))

    assert result["url"] == URL
    assert result["verdict"] == "PASS"
    assert "_meta" in result


def test_inspect_url_not_indexed(mock_gsc_service):
    mock_gsc_service.urlInspection.return_value.index.return_value.inspect.return_value.execute.return_value = (
        _mock_inspect_response(verdict="FAIL")
    )
    with patch("gsc_mcp.tools.inspection.get_searchconsole_service", return_value=mock_gsc_service):
        result = json.loads(inspect_url(URL, SITE))

    assert result["verdict"] == "FAIL"


def test_batch_url_inspection(mock_gsc_service):
    mock_gsc_service.urlInspection.return_value.index.return_value.inspect.return_value.execute.return_value = (
        _mock_inspect_response()
    )
    urls = [f"https://example.com/page-{i}" for i in range(3)]
    with patch("gsc_mcp.tools.inspection.get_searchconsole_service", return_value=mock_gsc_service):
        result = json.loads(batch_url_inspection(urls, SITE))

    assert len(result["results"]) == 3
    assert "_meta" in result


def test_batch_url_inspection_max_10(mock_gsc_service):
    urls = [f"https://example.com/page-{i}" for i in range(15)]
    with patch("gsc_mcp.tools.inspection.get_searchconsole_service", return_value=mock_gsc_service):
        with pytest.raises(ValueError, match="max 10"):
            batch_url_inspection(urls, SITE)


def test_check_indexing_issues(mock_gsc_service):
    not_indexed = _mock_inspect_response(verdict="FAIL", indexing_state="BLOCKED_BY_PAGE")
    mock_gsc_service.urlInspection.return_value.index.return_value.inspect.return_value.execute.return_value = not_indexed
    urls = ["https://example.com/a", "https://example.com/b"]
    with patch("gsc_mcp.tools.inspection.get_searchconsole_service", return_value=mock_gsc_service):
        result = json.loads(check_indexing_issues(urls, SITE))

    assert "summary" in result
    assert "issues" in result
    assert "_meta" in result
    for issue in result["issues"]:
        assert "category" in issue
        assert issue["category"] in (
            "not_indexed", "robots_blocked", "fetch_error", "canonical_issue", "indexed"
        )


def test_batch_url_inspection_retry_no_duplicate(mock_gsc_service):
    """A transient 429 on URL #2 must not duplicate URL #1 in the output."""
    url_a = "https://example.com/a"
    url_b = "https://example.com/b"

    ok_response = _mock_inspect_response()

    # Build a fake HttpError for status 429
    resp_mock = MagicMock()
    resp_mock.status = 429
    error_429 = HttpError(resp=resp_mock, content=b"rate limited")

    # execute() for URL b: fail once with 429, then succeed
    execute_mock = MagicMock(side_effect=[error_429, ok_response])

    def inspect_side_effect(body):
        request = MagicMock()
        # URL a always succeeds; URL b fails on first attempt
        if body["inspectionUrl"] == url_b:
            request.execute = execute_mock
        else:
            request.execute = MagicMock(return_value=ok_response)
        return request

    mock_gsc_service.urlInspection.return_value.index.return_value.inspect.side_effect = (
        inspect_side_effect
    )

    with patch("gsc_mcp.tools.inspection.get_searchconsole_service", return_value=mock_gsc_service):
        # Patch time.sleep so the retry is instant
        with patch("gsc_mcp.retry.time.sleep"):
            result = json.loads(batch_url_inspection([url_a, url_b], SITE))

    assert result["count"] == 2
    assert len(result["results"]) == 2
    urls_in_result = [r["url"] for r in result["results"]]
    assert urls_in_result.count(url_a) == 1, "URL a must appear exactly once (no duplicate from retry)"
    assert urls_in_result.count(url_b) == 1
