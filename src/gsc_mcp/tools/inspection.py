import json
from gsc_mcp.auth import get_gsc_service
from gsc_mcp.meta import with_meta

_MAX_BATCH = 10


def _categorize(result: dict) -> str:
    verdict = result.get("verdict", "")
    robots = result.get("robotsTxtState", "")
    indexing = result.get("indexingState", "")
    fetch = result.get("pageFetchState", "")
    google_canonical = result.get("googleCanonical", "")
    user_canonical = result.get("userCanonical", "")

    if verdict == "PASS":
        return "indexed"
    if "BLOCKED_BY_ROBOTS_TXT" in robots:
        return "robots_blocked"
    if fetch not in ("", "SUCCESSFUL"):
        return "fetch_error"
    if google_canonical and user_canonical and google_canonical != user_canonical:
        return "canonical_issue"
    return "not_indexed"


def _parse_inspection(url: str, response: dict) -> dict:
    index_result = response.get("inspectionResult", {}).get("indexStatusResult", {})
    return {
        "url": url,
        "verdict": index_result.get("verdict", "UNKNOWN"),
        "robots_txt_state": index_result.get("robotsTxtState", "UNKNOWN"),
        "indexing_state": index_result.get("indexingState", "UNKNOWN"),
        "last_crawl": index_result.get("lastCrawlTime"),
        "page_fetch_state": index_result.get("pageFetchState"),
        "google_canonical": index_result.get("googleCanonical"),
        "user_canonical": index_result.get("userCanonical"),
        "category": _categorize(index_result),
    }


def inspect_url(url: str, site: str) -> str:
    svc = get_gsc_service()
    body = {"inspectionUrl": url, "siteUrl": site}
    response = svc.urlInspection().index().inspect(body=body).execute()
    parsed = _parse_inspection(url, response)
    return json.dumps(with_meta(parsed, tool="inspect_url", params={"url": url, "site": site}))


def batch_url_inspection(urls: list[str], site: str) -> str:
    if len(urls) > _MAX_BATCH:
        raise ValueError(f"batch_url_inspection supports max 10 URLs, got {len(urls)}")

    svc = get_gsc_service()
    results = []
    for url in urls:
        body = {"inspectionUrl": url, "siteUrl": site}
        response = svc.urlInspection().index().inspect(body=body).execute()
        results.append(_parse_inspection(url, response))

    return json.dumps(with_meta(
        {"site": site, "count": len(results), "results": results},
        tool="batch_url_inspection",
        params={"site": site, "url_count": len(urls)},
    ))


def check_indexing_issues(urls: list[str], site: str) -> str:
    if len(urls) > _MAX_BATCH:
        raise ValueError(f"check_indexing_issues supports max 10 URLs, got {len(urls)}")

    svc = get_gsc_service()
    issues = []
    summary: dict[str, int] = {
        "indexed": 0,
        "not_indexed": 0,
        "robots_blocked": 0,
        "fetch_error": 0,
        "canonical_issue": 0,
    }

    for url in urls:
        body = {"inspectionUrl": url, "siteUrl": site}
        response = svc.urlInspection().index().inspect(body=body).execute()
        parsed = _parse_inspection(url, response)
        summary[parsed["category"]] = summary.get(parsed["category"], 0) + 1
        if parsed["category"] != "indexed":
            issues.append(parsed)

    return json.dumps(with_meta(
        {"site": site, "summary": summary, "issues": issues},
        tool="check_indexing_issues",
        params={"site": site, "url_count": len(urls)},
    ))
