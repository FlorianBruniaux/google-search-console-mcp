import pytest
import time
from unittest.mock import MagicMock, patch
from gsc_mcp.meta import with_meta
from gsc_mcp.retry import with_retry
from gsc_mcp.quota import QuotaTracker


# ---- meta ----

def test_with_meta_adds_meta_block():
    result = with_meta({"rows": []}, tool="get_search_analytics", params={"site": "example.com"})
    assert "_meta" in result
    assert result["_meta"]["tool"] == "get_search_analytics"
    assert result["_meta"]["params"]["site"] == "example.com"


def test_with_meta_preserves_data():
    data = {"rows": [{"keys": ["q"], "clicks": 10}]}
    result = with_meta(data, tool="test", params={})
    assert result["rows"] == data["rows"]


def test_with_meta_returns_dict():
    result = with_meta({}, tool="x", params={})
    assert isinstance(result, dict)


# ---- retry ----

def test_retry_succeeds_on_first_try():
    func = MagicMock(return_value="ok")
    decorated = with_retry()(func)
    assert decorated() == "ok"
    assert func.call_count == 1


def test_retry_retries_on_429():
    from googleapiclient.errors import HttpError
    from unittest.mock import call
    import httplib2

    resp = MagicMock()
    resp.status = 429

    error = HttpError(resp=resp, content=b"rate limited")
    func = MagicMock(side_effect=[error, error, "ok"])

    decorated = with_retry(max_retries=3, base_delay=0.01)(func)
    result = decorated()
    assert result == "ok"
    assert func.call_count == 3


def test_retry_raises_after_max_retries():
    from googleapiclient.errors import HttpError

    resp = MagicMock()
    resp.status = 500
    error = HttpError(resp=resp, content=b"server error")
    func = MagicMock(side_effect=error)

    decorated = with_retry(max_retries=2, base_delay=0.01)(func)
    with pytest.raises(HttpError):
        decorated()
    assert func.call_count == 3


def test_retry_does_not_retry_404():
    from googleapiclient.errors import HttpError

    resp = MagicMock()
    resp.status = 404
    error = HttpError(resp=resp, content=b"not found")
    func = MagicMock(side_effect=error)

    decorated = with_retry(max_retries=3, base_delay=0.01)(func)
    with pytest.raises(HttpError):
        decorated()
    assert func.call_count == 1


# ---- quota ----

def test_quota_tracker_initial_state():
    q = QuotaTracker(limit=200, warn_at=180)
    assert q.remaining() == 200


def test_quota_tracker_consume():
    q = QuotaTracker(limit=200, warn_at=180)
    q.consume(10)
    assert q.remaining() == 190


def test_quota_tracker_check_raises_when_exceeded():
    q = QuotaTracker(limit=10, warn_at=8)
    q.consume(9)
    with pytest.raises(RuntimeError, match="quota"):
        q.check(5)


def test_quota_tracker_should_warn():
    q = QuotaTracker(limit=200, warn_at=180)
    q.consume(179)
    assert not q.should_warn()
    q.consume(1)
    assert q.should_warn()


def test_quota_tracker_check_ok_below_limit():
    q = QuotaTracker(limit=200, warn_at=180)
    q.consume(100)
    q.check(50)
