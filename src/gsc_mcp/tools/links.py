"""Internal linking audit.

Rules encoded here come from a working SEO consultant (call transcript, 2026-08-06):
a link that only exists in the footer or the main nav carries far less weight than
the same link placed in the body of a page, and internal linking is worth as much
as off-site link building when it is done deliberately.

No Google API calls, no authentication. Same contract as schema_validate and
page_technical_audit: fetch the public URL, parse, report.
"""

from __future__ import annotations

import json
import time
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit

import httpx

from gsc_mcp.meta import with_meta
from gsc_mcp.tools.analytics import get_search_analytics
from gsc_mcp.url_safety import URLSafetyError, safe_fetch_html


# Semantic containers that demote a link. `role` values cover sites that still
# use <div role="navigation"> instead of <nav>.
_ZONE_TAGS: dict[str, str] = {
    "nav": "nav",
    "footer": "footer",
    "header": "header",
    "aside": "aside",
}
_ZONE_ROLES: dict[str, str] = {
    "navigation": "nav",
    "contentinfo": "footer",
    "banner": "header",
    "complementary": "aside",
}

# Zones where a link is structural rather than editorial.
_DEMOTED_ZONES = frozenset({"nav", "footer", "header", "aside"})

# Anchors that tell Google (and a screen reader) nothing about the target.
_GENERIC_ANCHORS = frozenset({
    # French
    "ici", "cliquez ici", "clique ici", "cliquer ici", "en savoir plus",
    "savoir plus", "lire la suite", "lire plus", "voir plus", "voir",
    "plus", "détails", "details", "découvrir", "decouvrir", "cette page",
    "ce lien", "lien", "suite",
    # English
    "here", "click here", "read more", "learn more", "more", "see more",
    "this page", "this link", "link", "details", "continue", "continue reading",
})


class _LinkParser(HTMLParser):
    """Collect every <a href> with the semantic zone it sits in.

    A stack is used rather than a flag because these containers nest in the wild
    (a <nav> inside a <header> is common). The zone reported for a link is the
    innermost demoting container, or "body" when the stack is empty.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._zone_stack: list[tuple[str, str]] = []  # (tag, zone)
        self._in_anchor = False
        self._anchor_chunks: list[str] = []
        self._anchor_attrs: dict = {}
        self.links: list[dict] = []

    def _current_zone(self) -> str:
        return self._zone_stack[-1][1] if self._zone_stack else "body"

    def handle_starttag(self, tag: str, attrs) -> None:
        attr = dict(attrs)
        tag_lower = tag.lower()

        zone = _ZONE_TAGS.get(tag_lower)
        if zone is None:
            role = (attr.get("role") or "").lower()
            zone = _ZONE_ROLES.get(role)
        if zone is not None:
            self._zone_stack.append((tag_lower, zone))
            return

        if tag_lower == "a" and "href" in attr:
            # Nested <a> is invalid HTML; if it happens, the outer one wins.
            if self._in_anchor:
                return
            self._in_anchor = True
            self._anchor_chunks = []
            self._anchor_attrs = attr

    def handle_endtag(self, tag: str) -> None:
        tag_lower = tag.lower()

        if self._zone_stack and self._zone_stack[-1][0] == tag_lower:
            self._zone_stack.pop()
            return

        if tag_lower == "a" and self._in_anchor:
            self._in_anchor = False
            self.links.append({
                "href": self._anchor_attrs.get("href", ""),
                "anchor": " ".join("".join(self._anchor_chunks).split()),
                "zone": self._current_zone(),
                "rel": (self._anchor_attrs.get("rel") or "").lower(),
            })
            self._anchor_attrs = {}

    def handle_data(self, data: str) -> None:
        if self._in_anchor:
            self._anchor_chunks.append(data)


def _classify(links: list[dict], page_url: str) -> list[dict]:
    """Resolve hrefs against the page URL and tag each link internal or external."""
    page_host = urlsplit(page_url).netloc.lower()
    page_path = urlsplit(page_url).path.rstrip("/") or "/"
    out: list[dict] = []

    for link in links:
        href = link["href"].strip()
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue

        absolute = urljoin(page_url, href)
        parts = urlsplit(absolute)
        if parts.scheme not in ("http", "https"):
            continue

        target_path = parts.path.rstrip("/") or "/"
        internal = parts.netloc.lower() == page_host

        out.append({
            **link,
            "url": absolute,
            "path": target_path,
            "internal": internal,
            "self_link": internal and target_path == page_path,
            "nofollow": "nofollow" in link["rel"],
        })

    return out


def internal_links_audit(url: str) -> str:
    """Audit the internal linking of a single page, weighted by where each link sits.

    Extracts every <a href> and tags it with its semantic zone (body, nav, footer,
    header, aside). A link in the body carries editorial weight; the same link in
    the footer or main nav is structural and counts for much less.

    Reports internal targets that appear ONLY in demoted zones (the highest-value
    finding), generic anchor text, internal links marked nofollow, and self-links.

    No Google API calls. No authentication required.
    Verdicts: healthy | issues_found | fetch_error.
    """
    params = {"url": url}
    try:
        html, _status = safe_fetch_html(url)
    except (URLSafetyError, httpx.HTTPError) as exc:
        return json.dumps(with_meta(
            {"url": url, "error": str(exc), "verdict": "fetch_error"},
            tool="internal_links_audit",
            params=params,
        ))

    parser = _LinkParser()
    parser.feed(html)
    links = _classify(parser.links, url)

    internal = [link for link in links if link["internal"]]
    external = [link for link in links if not link["internal"]]

    by_zone: dict[str, int] = {}
    for link in internal:
        by_zone[link["zone"]] = by_zone.get(link["zone"], 0) + 1

    body_paths = {link["path"] for link in internal if link["zone"] == "body"}
    demoted_paths: dict[str, dict] = {}
    for link in internal:
        if link["zone"] in _DEMOTED_ZONES and not link["self_link"]:
            demoted_paths.setdefault(link["path"], {
                "path": link["path"],
                "url": link["url"],
                "anchor": link["anchor"],
                "zones": [],
            })
            zones = demoted_paths[link["path"]]["zones"]
            if link["zone"] not in zones:
                zones.append(link["zone"])

    footer_only = [
        entry for path, entry in demoted_paths.items() if path not in body_paths
    ]
    footer_only.sort(key=lambda e: e["path"])

    generic_anchors = [
        {"url": link["url"], "anchor": link["anchor"], "zone": link["zone"]}
        for link in internal
        if link["anchor"].lower().strip(" .:!?»«\"'") in _GENERIC_ANCHORS
    ]
    empty_anchors = [
        {"url": link["url"], "zone": link["zone"]}
        for link in internal
        if not link["anchor"]
    ]
    nofollow_internal = [
        {"url": link["url"], "anchor": link["anchor"], "zone": link["zone"]}
        for link in internal
        if link["nofollow"]
    ]
    self_links = [link for link in internal if link["self_link"]]

    body_count = by_zone.get("body", 0)
    demoted_count = sum(count for zone, count in by_zone.items() if zone in _DEMOTED_ZONES)

    issues: list[dict] = []

    if footer_only:
        issues.append({
            "severity": "high",
            "check": "footer_only_links",
            "message": (
                f"{len(footer_only)} internal target(s) are linked only from nav/footer/aside. "
                "Moving the important ones into the body of a relevant page gives them "
                "materially more weight."
            ),
        })

    if internal and body_count == 0:
        issues.append({
            "severity": "high",
            "check": "no_body_links",
            "message": "No internal link sits in the body of the page; every one is structural.",
        })
    elif internal and body_count < demoted_count / 4:
        issues.append({
            "severity": "medium",
            "check": "body_link_ratio",
            "message": (
                f"Only {body_count} internal link(s) in the body against {demoted_count} "
                "in nav/footer/aside. Editorial linking is thin."
            ),
        })

    if generic_anchors:
        issues.append({
            "severity": "medium",
            "check": "generic_anchor",
            "message": (
                f"{len(generic_anchors)} internal link(s) use a non-descriptive anchor "
                "(\"en savoir plus\", \"click here\", ...). The anchor is a ranking signal for the target."
            ),
        })

    if empty_anchors:
        issues.append({
            "severity": "medium",
            "check": "empty_anchor",
            "message": f"{len(empty_anchors)} internal link(s) have no anchor text at all.",
        })

    if nofollow_internal:
        issues.append({
            "severity": "medium",
            "check": "nofollow_internal",
            "message": (
                f"{len(nofollow_internal)} internal link(s) carry rel=nofollow, "
                "which throws away the weight they would otherwise pass."
            ),
        })

    if not internal:
        issues.append({
            "severity": "high",
            "check": "no_internal_links",
            "message": "The page has no internal links at all.",
        })

    return json.dumps(with_meta(
        {
            "url": url,
            "total_links": len(links),
            "internal_count": len(internal),
            "external_count": len(external),
            "by_zone": by_zone,
            "body_links": body_count,
            "demoted_links": demoted_count,
            "footer_only_targets": footer_only[:30],
            "footer_only_count": len(footer_only),
            "generic_anchors": generic_anchors[:20],
            "empty_anchors": empty_anchors[:20],
            "nofollow_internal": nofollow_internal[:20],
            "self_link_count": len(self_links),
            "issues": issues,
            "verdict": "issues_found" if issues else "healthy",
        },
        tool="internal_links_audit",
        params=params,
    ))


# ---------------------------------------------------------------------------
# link_equity_map
# ---------------------------------------------------------------------------

# Page-two territory. A page here is close enough that one body link can move it,
# which is not true of a page already in the top 3 or one buried at position 60.
_STRIKING_MIN = 11.0
_STRIKING_MAX = 20.0

# Crawl guard rails. A tool that silently truncates reads as "I covered the site".
_MAX_PAGES_CEILING = 100
_DEFAULT_DELAY = 0.2


def _normalize_path(url: str) -> str:
    """Path only, trailing slash stripped, so /x and /x/ are one target."""
    path = urlsplit(url).path or "/"
    return path.rstrip("/") or "/"


def link_equity_map(
    site: str,
    days: int = 90,
    max_pages: int = 25,
    delay_seconds: float = _DEFAULT_DELAY,
) -> str:
    """Map internal link flow across a site's most-visible pages and cross it with GSC.

    Takes the pages with the most impressions over `days`, crawls each one, and
    builds a directed graph of internal links tagged by the zone they sit in.
    Joining that graph to the Search Console numbers answers the question a link
    audit on a single page cannot: which pages are close to page one and receive
    no editorial link at all.

    Outputs, in descending order of how actionable they are:
    - underlinked_striking_distance: positions 11-20 with no body inbound link.
      Placing one internal link here is the cheapest ranking move available.
    - orphan_candidates: pages with impressions and no body inbound link.
    - footer_only_targets: linked from nav/footer/aside and from no page body.
    - hub_pages: the pages distributing the most body links.

    Coverage is bounded by max_pages (hard ceiling 100). Only crawled pages act as
    link sources, so "orphan" means "no link found among the pages crawled", never
    a site-wide certainty. pages_crawled and pages_failed are always reported.

    Verdicts: healthy | issues_found | no_data.
    """
    max_pages = max(1, min(max_pages, _MAX_PAGES_CEILING))
    params = {"site": site, "days": days, "max_pages": max_pages}

    gsc = json.loads(get_search_analytics(site, days, dimensions=["page"]))
    rows = [r for r in gsc.get("rows", []) if r.get("page")]
    if not rows:
        return json.dumps(with_meta(
            {"site": site, "verdict": "no_data",
             "message": f"No page-level Search Console rows over {days} days."},
            tool="link_equity_map",
            params=params,
        ))

    rows.sort(key=lambda r: r.get("impressions", 0), reverse=True)
    targeted = rows[:max_pages]

    # GSC facts, keyed by normalised path so they join with parsed hrefs.
    gsc_by_path: dict[str, dict] = {}
    for row in rows:
        gsc_by_path[_normalize_path(row["page"])] = {
            "url": row["page"],
            "clicks": row.get("clicks", 0),
            "impressions": row.get("impressions", 0),
            "position": row.get("position"),
        }

    body_inbound: dict[str, set[str]] = {}
    demoted_inbound: dict[str, set[str]] = {}
    body_outbound: dict[str, set[str]] = {}
    crawled: list[str] = []
    failed: list[dict] = []

    for i, row in enumerate(targeted):
        page_url = row["page"]
        if i and delay_seconds:
            time.sleep(delay_seconds)
        try:
            html, _status = safe_fetch_html(page_url)
        except (URLSafetyError, httpx.HTTPError) as exc:
            failed.append({"url": page_url, "error": str(exc)})
            continue

        source = _normalize_path(page_url)
        crawled.append(source)

        parser = _LinkParser()
        parser.feed(html)
        for link in _classify(parser.links, page_url):
            if not link["internal"] or link["self_link"]:
                continue
            target = link["path"]
            if link["zone"] == "body":
                body_inbound.setdefault(target, set()).add(source)
                body_outbound.setdefault(source, set()).add(target)
            else:
                demoted_inbound.setdefault(target, set()).add(source)

    def _entry(path: str, extra: dict | None = None) -> dict:
        facts = gsc_by_path.get(path, {})
        out = {
            "path": path,
            "url": facts.get("url"),
            "clicks": facts.get("clicks"),
            "impressions": facts.get("impressions"),
            "position": facts.get("position"),
            "body_inbound": len(body_inbound.get(path, ())),
            "demoted_inbound": len(demoted_inbound.get(path, ())),
        }
        if extra:
            out.update(extra)
        return out

    # Only judge pages GSC actually knows about; a path we never saw in the data
    # has no traffic history to reason from.
    known_paths = set(gsc_by_path)

    underlinked_striking = [
        _entry(path)
        for path, facts in gsc_by_path.items()
        if facts.get("position") is not None
        and _STRIKING_MIN <= facts["position"] <= _STRIKING_MAX
        and not body_inbound.get(path)
    ]
    underlinked_striking.sort(key=lambda e: e["impressions"] or 0, reverse=True)

    orphan_candidates = [
        _entry(path)
        for path, facts in gsc_by_path.items()
        if (facts.get("impressions") or 0) > 0 and not body_inbound.get(path)
    ]
    orphan_candidates.sort(key=lambda e: e["impressions"] or 0, reverse=True)

    footer_only = [
        _entry(path, {"linked_from": sorted(sources)[:5]})
        for path, sources in demoted_inbound.items()
        if not body_inbound.get(path)
    ]
    footer_only.sort(key=lambda e: (e["impressions"] or 0), reverse=True)

    hub_pages = sorted(
        (
            {"path": source, "body_links_out": len(targets)}
            for source, targets in body_outbound.items()
        ),
        key=lambda e: e["body_links_out"],
        reverse=True,
    )

    issues: list[dict] = []
    if underlinked_striking:
        issues.append({
            "severity": "high",
            "check": "underlinked_striking_distance",
            "message": (
                f"{len(underlinked_striking)} page(s) sit at position "
                f"{int(_STRIKING_MIN)}-{int(_STRIKING_MAX)} with no body link pointing at them. "
                "One internal link each is the cheapest move on this list."
            ),
        })
    if orphan_candidates:
        issues.append({
            "severity": "medium",
            "check": "orphan_candidates",
            "message": (
                f"{len(orphan_candidates)} page(s) earn impressions with no body link "
                f"found across the {len(crawled)} page(s) crawled."
            ),
        })
    if footer_only:
        issues.append({
            "severity": "medium",
            "check": "footer_only_targets",
            "message": f"{len(footer_only)} internal target(s) live only in nav, footer or aside.",
        })
    if failed:
        issues.append({
            "severity": "low",
            "check": "crawl_incomplete",
            "message": f"{len(failed)} page(s) could not be fetched; coverage is partial.",
        })

    return json.dumps(with_meta(
        {
            "site": site,
            "days": days,
            "pages_in_gsc": len(rows),
            "pages_targeted": len(targeted),
            "pages_crawled": len(crawled),
            "pages_failed": len(failed),
            "failed_sample": failed[:10],
            "coverage_note": (
                f"Link sources are limited to the {len(crawled)} crawled page(s) out of "
                f"{len(rows)} known to Search Console. A page reported here as having no "
                "inbound link may still be linked from a page outside that set."
            ),
            "known_paths": len(known_paths),
            "underlinked_striking_distance": underlinked_striking[:30],
            "orphan_candidates": orphan_candidates[:30],
            "footer_only_targets": footer_only[:30],
            "hub_pages": hub_pages[:10],
            "issues": issues,
            "verdict": "issues_found" if issues else "healthy",
        },
        tool="link_equity_map",
        params=params,
    ))
