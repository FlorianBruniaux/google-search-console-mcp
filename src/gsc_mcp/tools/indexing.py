import json
from urllib.parse import urlparse

import httpx
from googleapiclient.errors import HttpError  # noqa: F401 — imported for @with_retry HttpError detection

from gsc_mcp.auth import get_indexing_service
from gsc_mcp.meta import with_meta
from gsc_mcp.quota import QuotaTracker
from gsc_mcp.constants import QUOTA_INDEXING_LIMIT, QUOTA_INDEXING_WARN_AT
from gsc_mcp.retry import with_retry
from gsc_mcp.url_safety import URLSafetyError, validate_url_strict

_INDEXNOW_ENDPOINT = "https://api.indexnow.org/indexnow"

_BATCH_SIZE = 100

_default_quota = QuotaTracker(limit=QUOTA_INDEXING_LIMIT, warn_at=QUOTA_INDEXING_WARN_AT)


@with_retry()
def submit_url(url: str, url_type: str = "URL_UPDATED") -> str:
    """Submit a single URL to the Google Indexing API for crawl notification.

    url_type must be 'URL_UPDATED' (page added or changed, default) or 'URL_DELETED' (page removed).
    Requires a service account with Indexing API access — OAuth is not sufficient.
    Transient 429/5xx errors are retried automatically (up to 3 times). Credential errors
    and non-retryable failures propagate to the caller.
    """
    svc = get_indexing_service()
    svc.urlNotifications().publish(body={"url": url, "type": url_type}).execute()
    return json.dumps(with_meta(
        {"url": url, "status": "submitted", "type": url_type},
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


@with_retry()
def submit_batch(urls: list[str], url_type: str = "URL_UPDATED") -> str:
    """Submit multiple URLs to the Google Indexing API in HTTP batches of 100.

    Returns per-URL results, total submitted/error counts, and remaining daily quota.
    Daily limit is 200 requests total. A quota_warning is added to the response when
    usage exceeds 180. url_type: 'URL_UPDATED' (default) or 'URL_DELETED'.
    """
    _default_quota.check(len(urls))
    svc = get_indexing_service()
    results: list[dict] = []

    for chunk_start in range(0, len(urls), _BATCH_SIZE):
        chunk = urls[chunk_start: chunk_start + _BATCH_SIZE]
        batch = svc.new_batch_http_request()
        for url in chunk:
            request = svc.urlNotifications().publish(body={"url": url, "type": url_type})
            batch.add(request, request_id=url, callback=_make_callback(results, url))
        batch.execute()

    _default_quota.consume(len(urls))

    submitted = sum(1 for r in results if r["status"] == "submitted")
    errors = sum(1 for r in results if r["status"] == "error")
    quota_warning = _default_quota.should_warn()

    payload: dict = {
        "total": len(urls),
        "submitted": submitted,
        "errors": errors,
        "quota_remaining": _default_quota.remaining(),
        "results": results,
    }
    if quota_warning:
        payload["quota_warning"] = True

    return json.dumps(with_meta(payload, tool="submit_batch", params={"url_count": len(urls), "type": url_type}))


def indexnow_submit(site: str, key: str, urls: list[str]) -> str:
    """Submit URLs to IndexNow, notifying Bing, Yandex, Seznam, and Naver simultaneously.

    IndexNow is an open protocol independent of Google. One POST to api.indexnow.org
    dispatches to all four participating engines. Each URL is validated with
    validate_url_strict (SSRF-safe) before submission. Invalid URLs are skipped and
    counted in skipped_invalid. The key must be 8-128 characters; you are responsible
    for hosting the key file at {site}/{key}.txt.

    Verdicts: ok (all valid, 200/202) | partial (some skipped, 200/202) | error.
    No Google API calls. No Google authentication required.
    """
    valid_urls: list[str] = []
    skipped_invalid = 0
    for u in urls:
        try:
            validate_url_strict(u)
            valid_urls.append(u)
        except URLSafetyError:
            skipped_invalid += 1

    if not valid_urls:
        return json.dumps(with_meta(
            {
                "site": site,
                "submitted": 0,
                "skipped_invalid": skipped_invalid,
                "status_code": None,
                "verdict": "error",
            },
            tool="indexnow_submit",
            params={"site": site, "url_count": len(urls)},
        ))

    parsed = urlparse(site)
    host = parsed.hostname or site
    key_location = f"{site.rstrip('/')}/{key}.txt"

    payload = {
        "host": host,
        "key": key,
        "keyLocation": key_location,
        "urlList": valid_urls,
    }

    try:
        with httpx.Client(timeout=15) as client:
            resp = client.post(
                _INDEXNOW_ENDPOINT,
                json=payload,
                headers={"Content-Type": "application/json; charset=utf-8"},
            )
    except httpx.HTTPError as exc:
        return json.dumps(with_meta(
            {
                "site": site,
                "submitted": 0,
                "skipped_invalid": skipped_invalid,
                "status_code": None,
                "error": str(exc),
                "verdict": "error",
            },
            tool="indexnow_submit",
            params={"site": site, "url_count": len(urls)},
        ))

    status = resp.status_code
    if status in (200, 202):
        verdict = "ok" if skipped_invalid == 0 else "partial"
    else:
        verdict = "error"

    return json.dumps(with_meta(
        {
            "site": site,
            "submitted": len(valid_urls),
            "skipped_invalid": skipped_invalid,
            "status_code": status,
            "verdict": verdict,
        },
        tool="indexnow_submit",
        params={"site": site, "url_count": len(urls)},
    ))
