"""Content quality, hreflang audit, and technical meta audit tools.

Filler-phrase list adapted from scripts/content_quality.py in claude-seo
(https://github.com/AgriciDaniel/claude-seo, MIT License, Copyright (c) 2026 agricidaniel).
Hreflang validation rules derived from skills/seo-hreflang/SKILL.md (MIT, same source).
All Python implementation is original. The _AI_PATTERNS list from claude-seo
(Wikipedia AI Cleanup, CC BY-SA 4.0) is intentionally excluded.
"""

from __future__ import annotations

import json
import re
import urllib.robotparser
from collections import Counter
from html.parser import HTMLParser

import httpx

from gsc_mcp.meta import with_meta
from gsc_mcp.url_safety import URLSafetyError, safe_fetch_html, validate_url_strict


# ---------------------------------------------------------------------------
# HTML parsers
# ---------------------------------------------------------------------------

class _TextExtractor(HTMLParser):
    """Return visible text after stripping non-content tags."""

    _SKIP: frozenset[str] = frozenset({
        "script", "style", "nav", "footer", "header", "noscript", "iframe",
    })

    def __init__(self):
        super().__init__()
        self._depth = 0
        self._chunks: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() in self._SKIP:
            self._depth += 1

    def handle_endtag(self, tag):
        if tag.lower() in self._SKIP and self._depth > 0:
            self._depth -= 1

    def handle_data(self, data):
        if self._depth == 0:
            stripped = data.strip()
            if stripped:
                self._chunks.append(stripped)

    @property
    def text(self) -> str:
        return " ".join(self._chunks)


class _MetaParser(HTMLParser):
    """Extract title, meta tags, canonical, hreflang links, viewport, html lang."""

    def __init__(self):
        super().__init__()
        self.title: str | None = None
        self.meta_description: str | None = None
        self.meta_robots: str | None = None
        self.canonical: str | None = None
        self.viewport: str | None = None
        self.html_lang: str | None = None
        self.hreflang: list[dict] = []
        self._in_title = False
        self._title_buf: list[str] = []

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        t = tag.lower()

        if t == "html":
            self.html_lang = d.get("lang")
        elif t == "title":
            self._in_title = True
            self._title_buf = []
        elif t == "meta":
            name = d.get("name", "").lower()
            content = d.get("content", "")
            if name == "description":
                self.meta_description = content
            elif name == "robots":
                self.meta_robots = content
            elif name == "viewport":
                self.viewport = content
        elif t == "link":
            rel = d.get("rel", "").lower()
            if "canonical" in rel:
                self.canonical = d.get("href")
            if "alternate" in rel:
                hreflang = d.get("hreflang")
                if hreflang:
                    self.hreflang.append({
                        "lang": hreflang,
                        "href": d.get("href", ""),
                    })

    def handle_endtag(self, tag):
        if tag.lower() == "title":
            self._in_title = False
            self.title = "".join(self._title_buf).strip() or None

    def handle_data(self, data):
        if self._in_title:
            self._title_buf.append(data)


# ---------------------------------------------------------------------------
# content_quality
# ---------------------------------------------------------------------------

# Filler phrases from scripts/content_quality.py in claude-seo (MIT, agricidaniel).
_FILLER_PHRASES: tuple[str, ...] = (
    "it's important to note that",
    "in this article, we'll explore",
    "in this article we will explore",
    "in today's fast-paced world",
    "in today's digital age",
    "in today's competitive landscape",
    "needless to say",
    "at the end of the day",
    "when it comes to",
    "when all is said and done",
    "in the realm of",
    "in the world of",
    "the bottom line is",
    "without further ado",
    "first and foremost",
    "last but not least",
    "for what it's worth",
    "it goes without saying",
    "as we all know",
    "the truth is that",
    "the fact of the matter is",
    "more often than not",
    "let's dive in",
    "let's dive into",
    "let's take a closer look",
    "let's take a deeper look",
)

_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z'\-]*")
_NUMBER_RE = re.compile(r"\b\d+(?:[.,]\d+)?(?:%|st|nd|rd|th)?\b")
_ENTITY_RE = re.compile(r"\b(?:[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b")


def _bigram_repetition(tokens: list[str]) -> float:
    if len(tokens) < 4:
        return 0.0
    bigrams = [f"{tokens[i]} {tokens[i + 1]}" for i in range(len(tokens) - 1)]
    counts = Counter(bigrams)
    repeated = sum(1 for v in counts.values() if v > 1)
    return repeated / max(1, len(counts))


def content_quality(url: str) -> str:
    """Analyse page content quality against Google QRG signals (E-E-A-T heuristics).

    Fetches the URL, extracts visible text, then scores against thin content,
    filler language, information density (named entities + numbers per token),
    and bigram repetition. No Google API calls. No authentication required.

    Filler phrase list adapted from claude-seo (agricidaniel, MIT).
    Verdicts: good | needs_work | thin_content | fetch_error.
    """
    try:
        html, _status = safe_fetch_html(url)
    except (URLSafetyError, httpx.HTTPError) as exc:
        return json.dumps(with_meta(
            {"url": url, "error": str(exc), "verdict": "fetch_error"},
            tool="content_quality",
            params={"url": url},
        ))

    extractor = _TextExtractor()
    extractor.feed(html)
    text = extractor.text

    tokens = [t.lower() for t in _TOKEN_RE.findall(text)]
    n_tokens = len(tokens)
    unique = len(set(tokens))

    lowered = text.lower()
    filler_hits = [p for p in _FILLER_PHRASES if p in lowered]

    entities = len(_ENTITY_RE.findall(text))
    numbers = len(_NUMBER_RE.findall(text))
    density_per_100 = (entities + numbers) * 100.0 / max(1, n_tokens)
    information_density = round(min(1.0, density_per_100 / 10.0), 3)

    rep = _bigram_repetition(tokens)
    rep_score = int(round(rep * 100))

    scale = max(1.0, n_tokens / 1000.0)
    filler_score = min(100, int(round(len(filler_hits) / scale * 25)))

    flags: list[str] = []
    if filler_score >= 50:
        flags.append("filler")
    if information_density < 0.20:
        flags.append("low-density")
    if rep_score >= 30:
        flags.append("repetitive")
    if n_tokens < 300:
        flags.append("thin-content")

    overall = int(round(
        (100 - filler_score) * 0.35
        + information_density * 100 * 0.35
        + (100 - rep_score) * 0.20
        + min(100, n_tokens / 10.0) * 0.10
    ))

    if n_tokens < 300:
        verdict = "thin_content"
    elif overall >= 60:
        verdict = "good"
    else:
        verdict = "needs_work"

    return json.dumps(with_meta(
        {
            "url": url,
            "word_count": n_tokens,
            "unique_tokens": unique,
            "filler_score": filler_score,
            "filler_hits": filler_hits[:10],
            "information_density": information_density,
            "repetition_score": rep_score,
            "overall_quality": overall,
            "flags": flags,
            "verdict": verdict,
        },
        tool="content_quality",
        params={"url": url},
    ))


# ---------------------------------------------------------------------------
# hreflang_audit
# ---------------------------------------------------------------------------

# ISO 639-1 two-letter language codes (full set + extended zh variants).
_VALID_LANG_CODES: frozenset[str] = frozenset({
    "aa", "ab", "ae", "af", "ak", "am", "an", "ar", "as", "av", "ay", "az",
    "ba", "be", "bg", "bh", "bi", "bm", "bn", "bo", "br", "bs", "ca", "ce",
    "ch", "co", "cr", "cs", "cu", "cv", "cy", "da", "de", "dv", "dz", "ee",
    "el", "en", "eo", "es", "et", "eu", "fa", "ff", "fi", "fj", "fo", "fr",
    "fy", "ga", "gd", "gl", "gn", "gu", "gv", "ha", "he", "hi", "ho", "hr",
    "ht", "hu", "hy", "hz", "ia", "id", "ie", "ig", "ii", "ik", "io", "is",
    "it", "iu", "ja", "jv", "ka", "kg", "ki", "kj", "kk", "kl", "km", "kn",
    "ko", "kr", "ks", "ku", "kv", "kw", "ky", "la", "lb", "lg", "li", "ln",
    "lo", "lt", "lu", "lv", "mg", "mh", "mi", "mk", "ml", "mn", "mr", "ms",
    "mt", "my", "na", "nb", "nd", "ne", "ng", "nl", "nn", "no", "nr", "nv",
    "ny", "oc", "oj", "om", "or", "os", "pa", "pi", "pl", "ps", "pt", "qu",
    "rm", "rn", "ro", "ru", "rw", "sa", "sc", "sd", "se", "sg", "si", "sk",
    "sl", "sm", "sn", "so", "sq", "sr", "ss", "st", "su", "sv", "sw", "ta",
    "te", "tg", "th", "ti", "tk", "tl", "tn", "to", "tr", "ts", "tt", "tw",
    "ty", "ug", "uk", "ur", "uz", "va", "ve", "vi", "vo", "wa", "wo", "xh",
    "yi", "yo", "za", "zh", "zu",
    "zh-hans", "zh-hant",
})

_REGION_RE = re.compile(r"^[A-Z]{2}$")


def _validate_lang_code(code: str) -> list[str]:
    """Return issue strings for an hreflang code, or [] if valid."""
    if code == "x-default":
        return []
    parts = code.lower().split("-")
    lang = parts[0]
    region = parts[1].upper() if len(parts) > 1 else None
    issues: list[str] = []

    if f"{lang}-{parts[1]}" if len(parts) > 1 else lang not in _VALID_LANG_CODES:
        if lang == "jp":
            issues.append(f"'{code}': use 'ja' for Japanese, not 'jp'")
        elif len(lang) == 3:
            issues.append(f"'{code}': use ISO 639-1 two-letter code (e.g. 'en' not 'eng')")
        elif lang not in _VALID_LANG_CODES:
            issues.append(f"'{code}': '{lang}' is not a recognised ISO 639-1 code")

    if region:
        if not _REGION_RE.match(region):
            issues.append(f"'{code}': region must be ISO 3166-1 Alpha-2 uppercase (e.g. 'en-US')")
        elif region == "UK":
            issues.append(f"'{code}': use 'GB' not 'UK' for United Kingdom")

    return issues


def hreflang_audit(url: str) -> str:
    """Fetch a URL and validate its hreflang implementation.

    Checks: missing x-default, invalid ISO 639-1 language codes, invalid
    ISO 3166-1 region codes, missing self-referencing tag, and mixed
    HTTP/HTTPS in the alternate set. Single-page audit: does not follow
    each alternate URL to verify bidirectional return tags.

    Validation rules derived from skills/seo-hreflang/SKILL.md in claude-seo
    (agricidaniel, MIT). No authentication required.
    Verdicts: valid | issues_found | no_hreflang | fetch_error.
    """
    try:
        html, _status = safe_fetch_html(url)
    except (URLSafetyError, httpx.HTTPError) as exc:
        return json.dumps(with_meta(
            {"url": url, "error": str(exc), "verdict": "fetch_error"},
            tool="hreflang_audit",
            params={"url": url},
        ))

    parser = _MetaParser()
    parser.feed(html)
    tags = parser.hreflang

    if not tags:
        return json.dumps(with_meta(
            {"url": url, "tags": [], "issues": [], "verdict": "no_hreflang"},
            tool="hreflang_audit",
            params={"url": url},
        ))

    issues: list[dict] = []

    # Self-referencing tag
    canonical = parser.canonical or url
    url_norms = {canonical.rstrip("/"), url.rstrip("/")}
    has_self_ref = any((t["href"] or "").rstrip("/") in url_norms for t in tags)
    if not has_self_ref:
        issues.append({
            "severity": "critical",
            "message": "Missing self-referencing hreflang tag (every page must include itself)",
        })

    # x-default
    has_x_default = any(t["lang"] == "x-default" for t in tags)
    if not has_x_default:
        issues.append({"severity": "high", "message": "Missing x-default hreflang tag"})

    # Language/region code validation
    for tag in tags:
        for msg in _validate_lang_code(tag["lang"]):
            issues.append({"severity": "high", "message": msg, "tag": tag})

    # Protocol consistency
    protos = set()
    for tag in tags:
        href = tag.get("href", "")
        if href.startswith("https://"):
            protos.add("https")
        elif href.startswith("http://"):
            protos.add("http")
    if len(protos) > 1:
        issues.append({
            "severity": "medium",
            "message": "Mixed HTTP/HTTPS in hreflang set — standardise to HTTPS",
        })

    verdict = "valid" if not issues else "issues_found"
    return json.dumps(with_meta(
        {
            "url": url,
            "tags_count": len(tags),
            "tags": tags,
            "has_x_default": has_x_default,
            "has_self_ref": has_self_ref,
            "issues": issues,
            "verdict": verdict,
        },
        tool="hreflang_audit",
        params={"url": url},
    ))


# ---------------------------------------------------------------------------
# page_technical_audit
# ---------------------------------------------------------------------------

_TITLE_OPTIMAL = (30, 60)
_DESC_OPTIMAL = (50, 160)
_SECURITY_HEADERS = ("x-frame-options", "x-content-type-options", "referrer-policy")


def page_technical_audit(url: str) -> str:
    """Audit on-page technical SEO: meta tags, canonical, robots.txt, security headers.

    Fetches the URL (follow_redirects=False for SSRF safety) and /robots.txt.
    Checks: title and meta description length, canonical presence and consistency,
    meta robots directives, viewport tag, HTML lang attribute, security response
    headers (X-Frame-Options, X-Content-Type-Options, Referrer-Policy), redirect
    detection, and whether Googlebot is blocked in robots.txt.

    For pages behind redirects, supply the final canonical URL directly.
    No Google API calls. No authentication required.
    Verdicts: healthy | issues_found | fetch_error.
    """
    try:
        validate_url_strict(url)
    except URLSafetyError as exc:
        return json.dumps(with_meta(
            {"url": url, "error": str(exc), "verdict": "fetch_error"},
            tool="page_technical_audit",
            params={"url": url},
        ))

    try:
        with httpx.Client(timeout=15, follow_redirects=False) as client:
            resp = client.get(url, headers={"User-Agent": "gsc-mcp-technical-audit/1.0"})
    except httpx.HTTPError as exc:
        return json.dumps(with_meta(
            {"url": url, "error": str(exc), "verdict": "fetch_error"},
            tool="page_technical_audit",
            params={"url": url},
        ))

    resp_headers = dict(resp.headers)
    html = resp.text
    issues: list[dict] = []
    findings: dict = {}

    # Redirect detection (3xx — raise_for_status doesn't raise on these)
    redirected = resp.status_code in (301, 302, 303, 307, 308)
    findings["status_code"] = resp.status_code
    findings["redirected"] = redirected
    if redirected:
        location = resp_headers.get("location", "")
        findings["redirect_target"] = location
        issues.append({
            "severity": "low",
            "check": "redirect",
            "message": f"URL redirects ({resp.status_code}) to {location} — audit the final URL directly",
        })

    if resp.status_code >= 400:
        return json.dumps(with_meta(
            {"url": url, "error": f"HTTP {resp.status_code}", "verdict": "fetch_error"},
            tool="page_technical_audit",
            params={"url": url},
        ))

    # HTML meta extraction
    meta = _MetaParser()
    meta.feed(html)

    # Title
    findings["title"] = meta.title
    findings["title_length"] = len(meta.title) if meta.title else 0
    if not meta.title:
        issues.append({"severity": "high", "check": "title", "message": "Missing <title> tag"})
    elif len(meta.title) < _TITLE_OPTIMAL[0]:
        issues.append({"severity": "medium", "check": "title",
                        "message": f"Title too short ({len(meta.title)} chars, optimal {_TITLE_OPTIMAL[0]}-{_TITLE_OPTIMAL[1]})"})
    elif len(meta.title) > _TITLE_OPTIMAL[1]:
        issues.append({"severity": "low", "check": "title",
                        "message": f"Title too long ({len(meta.title)} chars, optimal {_TITLE_OPTIMAL[0]}-{_TITLE_OPTIMAL[1]})"})

    # Meta description
    findings["meta_description"] = meta.meta_description
    findings["description_length"] = len(meta.meta_description) if meta.meta_description else 0
    if not meta.meta_description:
        issues.append({"severity": "medium", "check": "meta_description", "message": "Missing meta description"})
    elif len(meta.meta_description) < _DESC_OPTIMAL[0]:
        issues.append({"severity": "low", "check": "meta_description",
                        "message": f"Meta description too short ({len(meta.meta_description)} chars, optimal {_DESC_OPTIMAL[0]}-{_DESC_OPTIMAL[1]})"})
    elif len(meta.meta_description) > _DESC_OPTIMAL[1]:
        issues.append({"severity": "low", "check": "meta_description",
                        "message": f"Meta description too long ({len(meta.meta_description)} chars, optimal {_DESC_OPTIMAL[0]}-{_DESC_OPTIMAL[1]})"})

    # Meta robots
    findings["meta_robots"] = meta.meta_robots
    if meta.meta_robots:
        lr = meta.meta_robots.lower()
        if "noindex" in lr:
            issues.append({"severity": "critical", "check": "meta_robots",
                            "message": f"Page has noindex directive: '{meta.meta_robots}'"})
        if "nofollow" in lr:
            issues.append({"severity": "medium", "check": "meta_robots",
                            "message": f"Page has nofollow directive: '{meta.meta_robots}'"})

    # Canonical
    findings["canonical"] = meta.canonical
    if not meta.canonical:
        issues.append({"severity": "medium", "check": "canonical", "message": "Missing canonical link tag"})
    elif meta.canonical.rstrip("/") != url.rstrip("/"):
        issues.append({"severity": "high", "check": "canonical",
                        "message": f"Canonical ({meta.canonical}) differs from requested URL ({url})"})

    # Viewport
    findings["viewport"] = meta.viewport
    if not meta.viewport:
        issues.append({"severity": "medium", "check": "viewport",
                        "message": "Missing viewport meta tag (affects mobile usability)"})

    # HTML lang
    findings["html_lang"] = meta.html_lang
    if not meta.html_lang:
        issues.append({"severity": "low", "check": "html_lang",
                        "message": "Missing lang attribute on <html> element"})

    # Security headers
    sec: dict = {}
    for h in _SECURITY_HEADERS:
        val = resp_headers.get(h)
        sec[h] = val
        if not val:
            issues.append({"severity": "low", "check": "security_headers",
                            "message": f"Missing security header: {h}"})
    findings["security_headers"] = sec

    # Robots.txt (safe fetch + stdlib parser, same origin already validated)
    from urllib.parse import urlparse as _urlparse
    parsed = _urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    findings["robots_txt_blocks_googlebot"] = None
    try:
        robots_text, robots_status = safe_fetch_html(robots_url)
        if robots_status < 400:
            rp = urllib.robotparser.RobotFileParser()
            rp.set_url(robots_url)
            rp.parse(robots_text.splitlines())
            path = parsed.path or "/"
            can_fetch = rp.can_fetch("Googlebot", path)
            findings["robots_txt_blocks_googlebot"] = not can_fetch
            if not can_fetch:
                issues.append({"severity": "critical", "check": "robots_txt",
                                "message": f"robots.txt blocks Googlebot from {path}"})
    except (URLSafetyError, httpx.HTTPError):
        pass

    critical_count = sum(1 for i in issues if i.get("severity") == "critical")
    verdict = "issues_found" if issues else "healthy"

    return json.dumps(with_meta(
        {
            "url": url,
            "findings": findings,
            "issues": issues,
            "issues_count": len(issues),
            "critical_count": critical_count,
            "verdict": verdict,
        },
        tool="page_technical_audit",
        params={"url": url},
    ))
