import json
from gsc_mcp.auth import get_indexing_service
from gsc_mcp.meta import with_meta
from gsc_mcp.quota import QuotaTracker
from gsc_mcp.constants import QUOTA_INDEXING_LIMIT, QUOTA_INDEXING_WARN_AT

_BATCH_SIZE = 100

_default_quota = QuotaTracker(limit=QUOTA_INDEXING_LIMIT, warn_at=QUOTA_INDEXING_WARN_AT)


def submit_url(url: str, url_type: str = "URL_UPDATED") -> str:
    svc = get_indexing_service()
    try:
        svc.urlNotifications().publish(body={"url": url, "type": url_type}).execute()
        status = "submitted"
    except Exception as exc:
        return json.dumps(with_meta(
            {"url": url, "status": "error", "error": str(exc)},
            tool="submit_url",
            params={"url": url, "type": url_type},
        ))

    return json.dumps(with_meta(
        {"url": url, "status": status, "type": url_type},
        tool="submit_url",
        params={"url": url, "type": url_type},
    ))


def _make_callback(results: list, url: str):
    def callback(request_id, response, exception):
        if exception:
            results.append({"url": url, "status": "error", "error": str(exception)})
        else:
            results.append({"url": url, "status": "submitted"})
    return callback


def _submit_batch_impl(urls: list[str], url_type: str, quota: QuotaTracker) -> str:
    quota.check(len(urls))
    svc = get_indexing_service()
    results: list[dict] = []

    for chunk_start in range(0, len(urls), _BATCH_SIZE):
        chunk = urls[chunk_start: chunk_start + _BATCH_SIZE]
        batch = svc.new_batch_http_request()
        for url in chunk:
            request = svc.urlNotifications().publish(body={"url": url, "type": url_type})
            batch.add(request, request_id=url, callback=_make_callback(results, url))
        batch.execute()

    quota.consume(len(urls))

    submitted = sum(1 for r in results if r["status"] == "submitted")
    errors = sum(1 for r in results if r["status"] == "error")
    quota_warning = quota.should_warn()

    payload: dict = {
        "total": len(urls),
        "submitted": submitted,
        "errors": errors,
        "quota_remaining": quota.remaining(),
        "results": results,
    }
    if quota_warning:
        payload["quota_warning"] = True

    return json.dumps(with_meta(payload, tool="submit_batch", params={"url_count": len(urls), "type": url_type}))


def submit_batch(urls: list[str], url_type: str = "URL_UPDATED") -> str:
    return _submit_batch_impl(urls, url_type, _default_quota)
