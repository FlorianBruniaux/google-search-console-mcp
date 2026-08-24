"""Tests for internal_links_audit.

All fetches are mocked; no network access. safe_fetch_html is patched at the call
site (gsc_mcp.tools.links.safe_fetch_html), matching the convention used by the
content.py tests.
"""

import json
from unittest.mock import patch

import httpx
import pytest

from gsc_mcp.tools.links import internal_links_audit, link_equity_map
from gsc_mcp.url_safety import URLSafetyError

PAGE = "https://example.com/guide/seo"


def _audit(html, url=PAGE):
    with patch("gsc_mcp.tools.links.safe_fetch_html", return_value=(html, 200)):
        return json.loads(internal_links_audit(url))


# ---------------------------------------------------------------------------
# Zone attribution
# ---------------------------------------------------------------------------

def test_links_tagged_with_their_zone():
    html = """
    <html><body>
      <header><a href="/home">Accueil</a></header>
      <nav><a href="/services">Nos services</a></nav>
      <main><p>Voir notre <a href="/audit-seo">audit SEO complet</a>.</p></main>
      <aside><a href="/blog">Blog</a></aside>
      <footer><a href="/mentions">Mentions legales</a></footer>
    </body></html>
    """
    result = _audit(html)
    assert result["by_zone"] == {"header": 1, "nav": 1, "body": 1, "aside": 1, "footer": 1}
    assert result["body_links"] == 1
    assert result["demoted_links"] == 4


def test_nested_zones_report_innermost():
    """A <nav> inside a <header> reports nav, and the stack unwinds correctly."""
    html = """
    <html><body>
      <header>
        <a href="/logo">Logo</a>
        <nav><a href="/services">Services</a></nav>
      </header>
      <p><a href="/apres">Un lien de corps apres le header</a></p>
    </body></html>
    """
    result = _audit(html)
    assert result["by_zone"]["header"] == 1
    assert result["by_zone"]["nav"] == 1
    assert result["by_zone"]["body"] == 1


def test_role_attribute_demotes_like_semantic_tag():
    html = """
    <html><body>
      <div role="contentinfo"><a href="/cgv">CGV</a></div>
      <div role="navigation"><a href="/tarifs">Tarifs</a></div>
      <p><a href="/corps">Lien de corps</a></p>
    </body></html>
    """
    result = _audit(html)
    assert result["by_zone"]["footer"] == 1
    assert result["by_zone"]["nav"] == 1
    assert result["by_zone"]["body"] == 1


# ---------------------------------------------------------------------------
# The core finding: footer-only targets
# ---------------------------------------------------------------------------

def test_footer_only_target_is_flagged():
    html = """
    <html><body>
      <main><p>Rien ici.</p></main>
      <footer><a href="/prestation-importante">Notre prestation phare</a></footer>
    </body></html>
    """
    result = _audit(html)
    paths = [entry["path"] for entry in result["footer_only_targets"]]
    assert paths == ["/prestation-importante"]
    assert result["footer_only_count"] == 1
    assert result["verdict"] == "issues_found"
    assert any(i["check"] == "footer_only_links" and i["severity"] == "high"
               for i in result["issues"])


def test_target_present_in_body_is_not_footer_only():
    """Same target linked from both body and footer is fine; the body link counts."""
    html = """
    <html><body>
      <main><p>Voir notre <a href="/prestation">prestation phare</a>.</p></main>
      <footer><a href="/prestation">Prestation</a></footer>
    </body></html>
    """
    result = _audit(html)
    assert result["footer_only_targets"] == []
    assert result["footer_only_count"] == 0


def test_trailing_slash_variants_match_as_one_target():
    html = """
    <html><body>
      <main><a href="/prestation/">Notre prestation</a></main>
      <footer><a href="/prestation">Prestation</a></footer>
    </body></html>
    """
    result = _audit(html)
    assert result["footer_only_count"] == 0


# ---------------------------------------------------------------------------
# Anchors, rel, self-links
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("anchor", ["en savoir plus", "Cliquez ici", "read more", "ici", "Voir plus"])
def test_generic_anchors_detected_fr_and_en(anchor):
    html = f'<html><body><main><a href="/cible">{anchor}</a></main></body></html>'
    result = _audit(html)
    assert len(result["generic_anchors"]) == 1
    assert any(i["check"] == "generic_anchor" for i in result["issues"])


def test_descriptive_anchor_not_flagged():
    html = '<html><body><main><a href="/cible">audit SEO technique complet</a></main></body></html>'
    result = _audit(html)
    assert result["generic_anchors"] == []
    assert not any(i["check"] == "generic_anchor" for i in result["issues"])


def test_empty_anchor_detected():
    html = '<html><body><main><a href="/cible"><img src="x.png"></a></main></body></html>'
    result = _audit(html)
    assert len(result["empty_anchors"]) == 1
    assert any(i["check"] == "empty_anchor" for i in result["issues"])


def test_nofollow_on_internal_link_flagged():
    html = '<html><body><main><a href="/cible" rel="nofollow">audit complet</a></main></body></html>'
    result = _audit(html)
    assert len(result["nofollow_internal"]) == 1
    assert any(i["check"] == "nofollow_internal" for i in result["issues"])


def test_self_link_counted_and_excluded_from_footer_only():
    html = f"""
    <html><body>
      <main><p>Texte</p></main>
      <footer><a href="{PAGE}">Cette page</a></footer>
    </body></html>
    """
    result = _audit(html)
    assert result["self_link_count"] == 1
    assert result["footer_only_count"] == 0


# ---------------------------------------------------------------------------
# Internal vs external, ignored schemes
# ---------------------------------------------------------------------------

def test_external_links_separated():
    html = """
    <html><body><main>
      <a href="/interne">Guide interne detaille</a>
      <a href="https://autre-site.com/page">Ressource externe</a>
    </main></body></html>
    """
    result = _audit(html)
    assert result["internal_count"] == 1
    assert result["external_count"] == 1


def test_non_http_schemes_and_fragments_ignored():
    html = """
    <html><body><main>
      <a href="mailto:hello@example.com">Mail</a>
      <a href="tel:+33100000000">Tel</a>
      <a href="#section">Ancre</a>
      <a href="javascript:void(0)">JS</a>
      <a href="/reel">Un vrai lien interne</a>
    </main></body></html>
    """
    result = _audit(html)
    assert result["total_links"] == 1
    assert result["internal_count"] == 1


def test_relative_href_resolved_against_page_url():
    html = '<html><body><main><a href="avance">Guide avance</a></main></body></html>'
    result = _audit(html)
    assert result["internal_count"] == 1


# ---------------------------------------------------------------------------
# Verdicts and error paths
# ---------------------------------------------------------------------------

def test_healthy_page_has_no_issues():
    html = """
    <html><body>
      <main>
        <p>Voir le <a href="/guide-technique">guide technique complet</a> et
        notre <a href="/audit">methode d audit detaillee</a>.</p>
      </main>
      <footer><a href="/guide-technique">Guide technique</a></footer>
    </body></html>
    """
    result = _audit(html)
    assert result["issues"] == []
    assert result["verdict"] == "healthy"


def test_page_without_internal_links_flagged():
    html = '<html><body><main><a href="https://ailleurs.com/x">Externe</a></main></body></html>'
    result = _audit(html)
    assert result["internal_count"] == 0
    assert any(i["check"] == "no_internal_links" for i in result["issues"])


def test_url_safety_error_returns_fetch_error():
    with patch("gsc_mcp.tools.links.safe_fetch_html", side_effect=URLSafetyError("blocked host")):
        result = json.loads(internal_links_audit("http://169.254.169.254/"))
    assert result["verdict"] == "fetch_error"
    assert "blocked host" in result["error"]


def test_http_error_returns_fetch_error():
    with patch("gsc_mcp.tools.links.safe_fetch_html", side_effect=httpx.ConnectError("boom")):
        result = json.loads(internal_links_audit(PAGE))
    assert result["verdict"] == "fetch_error"


def test_meta_block_present():
    result = _audit("<html><body><main><a href='/x'>Guide detaille</a></main></body></html>")
    assert result["_meta"]["tool"] == "internal_links_audit"
    assert result["_meta"]["params"] == {"url": PAGE}


# ---------------------------------------------------------------------------
# link_equity_map
# ---------------------------------------------------------------------------

SITE = "https://example.com/"


def _gsc_pages(rows):
    """Shape of get_search_analytics(dimensions=["page"])."""
    return json.dumps({
        "rows": [
            {
                "page": r["page"],
                "clicks": r.get("clicks", 0),
                "impressions": r.get("impressions", 0),
                "ctr": 0.0,
                "position": r.get("position", 50.0),
            }
            for r in rows
        ],
        "_meta": {"tool": "get_search_analytics", "params": {}},
    })


def _equity(gsc_rows, pages_html, **kwargs):
    """Run link_equity_map with mocked GSC and a url -> html map."""
    def fake_fetch(url, **_):
        for candidate, html in pages_html.items():
            if url == candidate:
                return (html, 200)
        raise httpx.ConnectError(f"no mock for {url}")

    with patch("gsc_mcp.tools.links.get_search_analytics", return_value=_gsc_pages(gsc_rows)), \
         patch("gsc_mcp.tools.links.safe_fetch_html", side_effect=fake_fetch):
        kwargs.setdefault("delay_seconds", 0)
        return json.loads(link_equity_map(SITE, **kwargs))


def test_striking_distance_page_without_body_link_is_top_finding():
    """Position 11-20 with no body inbound link is the cheapest ranking move."""
    hub = "https://example.com/guide"
    target = "https://example.com/audit-seo"
    result = _equity(
        [
            {"page": hub, "clicks": 100, "impressions": 2000, "position": 3.0},
            {"page": target, "clicks": 1, "impressions": 900, "position": 12.4},
        ],
        {
            hub: "<html><body><main><p>Rien vers la cible.</p></main>"
                 "<footer><a href='/audit-seo'>Audit SEO</a></footer></body></html>",
            target: "<html><body><main><p>Page cible.</p></main></body></html>",
        },
    )
    paths = [e["path"] for e in result["underlinked_striking_distance"]]
    assert paths == ["/audit-seo"]
    assert result["underlinked_striking_distance"][0]["impressions"] == 900
    assert result["underlinked_striking_distance"][0]["demoted_inbound"] == 1
    assert any(i["check"] == "underlinked_striking_distance" and i["severity"] == "high"
               for i in result["issues"])


def test_body_link_clears_the_striking_distance_finding():
    hub = "https://example.com/guide"
    target = "https://example.com/audit-seo"
    result = _equity(
        [
            {"page": hub, "clicks": 100, "impressions": 2000, "position": 3.0},
            {"page": target, "clicks": 1, "impressions": 900, "position": 12.4},
        ],
        {
            hub: "<html><body><main><p>Voir l <a href='/audit-seo'>audit SEO complet</a>.</p>"
                 "</main></body></html>",
            target: "<html><body><main><p>Page cible.</p></main></body></html>",
        },
    )
    assert result["underlinked_striking_distance"] == []
    # The hub itself stays an orphan candidate: nothing in the crawled set links
    # to it. Only the target was rescued by the body link.
    orphan_paths = [e["path"] for e in result["orphan_candidates"]]
    assert "/audit-seo" not in orphan_paths
    assert orphan_paths == ["/guide"]


def test_position_outside_11_20_is_not_striking_distance():
    hub = "https://example.com/guide"
    top = "https://example.com/deja-premier"
    result = _equity(
        [
            {"page": hub, "clicks": 100, "impressions": 2000, "position": 3.0},
            {"page": top, "clicks": 50, "impressions": 800, "position": 2.1},
        ],
        {
            hub: "<html><body><main><p>Rien.</p></main></body></html>",
            top: "<html><body><main><p>Page.</p></main></body></html>",
        },
    )
    assert result["underlinked_striking_distance"] == []


def test_hub_pages_ranked_by_outbound_body_links():
    hub = "https://example.com/hub"
    leaf = "https://example.com/leaf"
    result = _equity(
        [
            {"page": hub, "clicks": 10, "impressions": 500, "position": 5.0},
            {"page": leaf, "clicks": 5, "impressions": 200, "position": 6.0},
        ],
        {
            hub: "<html><body><main><a href='/leaf'>Feuille</a>"
                 "<a href='/autre'>Autre page</a></main></body></html>",
            leaf: "<html><body><main><p>Rien.</p></main></body></html>",
        },
    )
    assert result["hub_pages"][0] == {"path": "/hub", "body_links_out": 2}


def test_crawl_failure_reported_not_swallowed():
    ok = "https://example.com/ok"
    broken = "https://example.com/casse"
    result = _equity(
        [
            {"page": ok, "clicks": 10, "impressions": 500, "position": 5.0},
            {"page": broken, "clicks": 2, "impressions": 100, "position": 9.0},
        ],
        {ok: "<html><body><main><p>Rien.</p></main></body></html>"},
    )
    assert result["pages_crawled"] == 1
    assert result["pages_failed"] == 1
    assert result["failed_sample"][0]["url"] == broken
    assert any(i["check"] == "crawl_incomplete" for i in result["issues"])


def test_max_pages_capped_and_coverage_reported():
    rows = [
        {"page": f"https://example.com/p{i}", "clicks": 0, "impressions": 100 - i, "position": 30.0}
        for i in range(10)
    ]
    html = {r["page"]: "<html><body><main><p>x</p></main></body></html>" for r in rows}
    result = _equity(rows, html, max_pages=3)
    assert result["pages_in_gsc"] == 10
    assert result["pages_targeted"] == 3
    assert result["pages_crawled"] == 3
    assert "3 crawled page(s) out of 10" in result["coverage_note"]


def test_max_pages_ceiling_enforced():
    rows = [{"page": "https://example.com/a", "clicks": 1, "impressions": 5, "position": 30.0}]
    html = {rows[0]["page"]: "<html><body><main><p>x</p></main></body></html>"}
    result = _equity(rows, html, max_pages=9999)
    assert result["_meta"]["params"]["max_pages"] == 100


def test_no_gsc_rows_returns_no_data():
    with patch("gsc_mcp.tools.links.get_search_analytics", return_value=_gsc_pages([])):
        result = json.loads(link_equity_map(SITE, delay_seconds=0))
    assert result["verdict"] == "no_data"


def test_equity_map_meta_block():
    rows = [{"page": "https://example.com/a", "clicks": 1, "impressions": 5, "position": 30.0}]
    html = {rows[0]["page"]: "<html><body><main><p>x</p></main></body></html>"}
    result = _equity(rows, html)
    assert result["_meta"]["tool"] == "link_equity_map"
