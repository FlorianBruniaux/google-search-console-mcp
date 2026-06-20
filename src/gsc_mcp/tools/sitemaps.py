import json
from gsc_mcp.auth import get_gsc_service
from gsc_mcp.meta import with_meta


def list_sitemaps(site: str) -> str:
    svc = get_gsc_service()
    response = svc.sitemaps().list(siteUrl=site).execute()
    raw = response.get("sitemap", [])

    sitemaps = [
        {
            "url": s.get("path", ""),
            "last_submitted": s.get("lastSubmitted"),
            "last_downloaded": s.get("lastDownloaded"),
            "is_pending": s.get("isPending", False),
            "is_index": s.get("isSitemapsIndex", False),
            "warnings": int(s.get("warnings", 0)),
            "errors": int(s.get("errors", 0)),
            "contents": s.get("contents", []),
        }
        for s in raw
    ]

    return json.dumps(with_meta(
        {"site": site, "count": len(sitemaps), "sitemaps": sitemaps},
        tool="list_sitemaps",
        params={"site": site},
    ))


def submit_sitemap(site: str, sitemap_url: str) -> str:
    svc = get_gsc_service()
    svc.sitemaps().submit(siteUrl=site, feedpath=sitemap_url).execute()
    return json.dumps(with_meta(
        {"site": site, "sitemap_url": sitemap_url, "status": "submitted"},
        tool="submit_sitemap",
        params={"site": site, "sitemap_url": sitemap_url},
    ))
