import json

import defusedxml.ElementTree as ET
import httpx

from gsc_mcp.auth import get_searchconsole_service
from gsc_mcp.meta import with_meta
from gsc_mcp.retry import with_retry
from gsc_mcp.tools.analytics import get_search_analytics


@with_retry()
def list_sitemaps(site: str) -> str:
    """List all sitemaps submitted to a GSC property, with submission dates, status, and error counts."""
    svc = get_searchconsole_service()
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


@with_retry()
def submit_sitemap(site: str, sitemap_url: str) -> str:
    """Submit a new sitemap URL to a GSC property. If already submitted, GSC updates the existing entry."""
    svc = get_searchconsole_service()
    svc.sitemaps().submit(siteUrl=site, feedpath=sitemap_url).execute()
    return json.dumps(with_meta(
        {"site": site, "sitemap_url": sitemap_url, "status": "submitted"},
        tool="submit_sitemap",
        params={"site": site, "sitemap_url": sitemap_url},
    ))


@with_retry()
def sitemaps_delete(site: str, sitemap_url: str) -> str:
    """Delete a submitted sitemap from a GSC property.

    Requires the URL to end with '.xml' or contain '/sitemap' as a safety guard against
    accidental deletion. Removes the entry from GSC tracking only; does not delete the sitemap file.
    """
    if not (sitemap_url.endswith(".xml") or "/sitemap" in sitemap_url):
        raise ValueError(
            f"Refusing to delete '{sitemap_url}': path does not look like a sitemap "
            "(must end with '.xml' or contain '/sitemap')."
        )
    svc = get_searchconsole_service()
    svc.sitemaps().delete(siteUrl=site, feedpath=sitemap_url).execute()
    return json.dumps(with_meta(
        {"site": site, "sitemap_url": sitemap_url, "status": "deleted"},
        tool="sitemaps_delete",
        params={"site": site, "sitemap_url": sitemap_url},
    ))


@with_retry()
def sitemaps_get(site: str, sitemap_url: str) -> str:
    """Get details for a specific sitemap already submitted to a GSC property.

    Returns content type counts (URLs, images, videos), error and warning counts, and status flags.
    """
    svc = get_searchconsole_service()
    s = svc.sitemaps().get(siteUrl=site, feedpath=sitemap_url).execute()
    sitemap = {
        "url": s.get("path", sitemap_url),
        "last_submitted": s.get("lastSubmitted"),
        "last_downloaded": s.get("lastDownloaded"),
        "is_pending": s.get("isPending", False),
        "is_index": s.get("isSitemapsIndex", False),
        "warnings": int(s.get("warnings", 0)),
        "errors": int(s.get("errors", 0)),
        "contents": s.get("contents", []),
    }
    return json.dumps(with_meta(
        {"site": site, "sitemap": sitemap},
        tool="sitemaps_get",
        params={"site": site, "sitemap_url": sitemap_url},
    ))


def sitemap_audit(site: str, sitemap_url: str) -> str:
    """Fetch a sitemap, parse its URLs, and cross-reference with GSC indexed pages.

    Handles both regular sitemaps (<urlset>) and sitemap index files (<sitemapindex>),
    with one level of recursion for sitemap indexes. Uses defusedxml for safe XML parsing
    (prevents XXE and billion-laughs attacks from untrusted external XML).

    Returns urls_declared, urls_in_gsc, urls_missing_from_gsc, a missing_sample (up to 20),
    and a verdict: empty | fetch_error | partial | healthy.
    """
    NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

    def _fetch_xml(url: str):
        try:
            with httpx.Client(timeout=15, follow_redirects=True) as client:
                resp = client.get(url, headers={"User-Agent": "gsc-mcp-sitemap-audit/1.0"})
                resp.raise_for_status()
                return ET.fromstring(resp.content)
        except Exception:
            return None

    root = _fetch_xml(sitemap_url)
    declared_urls: list[str] = []
    is_index = False

    if root is None:
        verdict = "fetch_error"
    elif root.tag.endswith("sitemapindex"):
        is_index = True
        for loc in root.findall(".//sm:sitemap/sm:loc", NS):
            child = _fetch_xml(loc.text.strip())
            if child is not None:
                declared_urls += [
                    l.text.strip()
                    for l in child.findall(".//sm:url/sm:loc", NS)
                    if l.text
                ]
    else:
        declared_urls = [
            l.text.strip()
            for l in root.findall(".//sm:url/sm:loc", NS)
            if l.text
        ]

    gsc_raw = json.loads(
        get_search_analytics(site, days=90, dimensions=["page"], row_limit=5000)
    )
    gsc_pages = {row["page"].rstrip("/").lower() for row in gsc_raw.get("rows", [])}
    declared_set = {u.rstrip("/").lower() for u in declared_urls}

    in_gsc = declared_set & gsc_pages
    missing = declared_set - gsc_pages
    ratio = len(missing) / max(len(declared_set), 1)

    if root is None:
        verdict = "fetch_error"
    elif not declared_urls:
        verdict = "empty"
    elif ratio > 0.2:
        verdict = "partial"
    else:
        verdict = "healthy"

    return json.dumps(with_meta(
        {
            "site": site,
            "sitemap_url": sitemap_url,
            "is_index": is_index,
            "urls_declared": len(declared_urls),
            "urls_in_gsc": len(in_gsc),
            "urls_missing_from_gsc": len(missing),
            "missing_sample": sorted(missing)[:20],
            "verdict": verdict,
        },
        tool="sitemap_audit",
        params={"site": site, "sitemap_url": sitemap_url},
    ))
