import json
import re
from urllib.parse import urlparse

import httpx
from googleapiclient.errors import HttpError  # noqa: F401 — imported for @with_retry HttpError detection

from gsc_mcp.auth import get_indexing_service
from gsc_mcp.meta import with_meta
from gsc_mcp.quota import QuotaTracker
from gsc_mcp.constants import QUOTA_INDEXING_LIMIT, QUOTA_INDEXING_WARN_AT
from gsc_mcp.retry import with_retry
from gsc_mcp.url_safety import (
    validate_same_origin,
    validate_url_strict,
)

_INDEXNOW_ENDPOINT = "https://api.indexnow.org/indexnow"
_INDEXNOW_KEY_RE = re.compile(r"^[A-Za-z0-9-]{8,128}$")
_INDEXNOW_MAX_URLS = 10_000

_BATCH_SIZE = 100

_default_quota = QuotaTracker(limit=QUOTA_INDEXING_LIMIT, warn_at=QUOTA_INDEXING_WARN_AT)


def validate_indexnow_key(key: str) -> None:
    """Reject IndexNow keys outside the protocol's length and alphabet."""
    if not _INDEXNOW_KEY_RE.fullmatch(key):
        raise ValueError("IndexNow key must contain 8-128 letters, digits, or hyphens")


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

    Each URL must pass strict SSRF validation and match site's exact HTTPS origin.
    A 200 or 202 means only that the notification was received, never that a URL
    was crawled or indexed. The key is sent to IndexNow but never returned in output.
    """
    validate_indexnow_key(key)
    if not 1 <= len(urls) <= _INDEXNOW_MAX_URLS:
        raise ValueError("IndexNow requires between 1 and 10000 URLs")
    validate_same_origin(site, site)

    valid_urls: list[str] = []
    skipped_invalid = 0
    for u in urls:
        try:
            validate_url_strict(u)
            validate_same_origin(site, u)
            valid_urls.append(u)
        except ValueError:
            skipped_invalid += 1

    if not valid_urls:
        return json.dumps(with_meta(
            {
                "site": site,
                "submitted": 0,
                "skipped_invalid": skipped_invalid,
                "status_code": None,
                "status": "error",
                "error_category": "no_valid_urls",
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
    except httpx.TimeoutException:
        return json.dumps(with_meta(
            {
                "site": site,
                "submitted": 0,
                "skipped_invalid": skipped_invalid,
                "status_code": None,
                "status": "error",
                "error_category": "timeout",
                "verdict": "error",
            },
            tool="indexnow_submit",
            params={"site": site, "url_count": len(urls)},
        ))
    except httpx.HTTPError:
        return json.dumps(with_meta(
            {
                "site": site,
                "submitted": 0,
                "skipped_invalid": skipped_invalid,
                "status_code": None,
                "status": "error",
                "error_category": "transport_error",
                "verdict": "error",
            },
            tool="indexnow_submit",
            params={"site": site, "url_count": len(urls)},
        ))

    status = resp.status_code
    if status in (200, 202):
        verdict = "ok" if skipped_invalid == 0 else "partial"
        protocol_status = "received"
        key_validation = "verified" if status == 200 else "pending"
        submitted = len(valid_urls)
    else:
        verdict = "error"
        protocol_status = "rejected"
        key_validation = None
        submitted = 0

    result = {
        "site": site,
        "submitted": submitted,
        "skipped_invalid": skipped_invalid,
        "status_code": status,
        "status": protocol_status,
        "verdict": verdict,
    }
    if key_validation is not None:
        result["key_validation"] = key_validation

    return json.dumps(with_meta(
        result,
        tool="indexnow_submit",
        params={"site": site, "url_count": len(urls)},
    ))
