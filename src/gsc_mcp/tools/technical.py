import json
import os
import re
import urllib.robotparser
from html.parser import HTMLParser
from typing import Optional
from urllib.parse import urlparse

import httpx

from gsc_mcp.meta import with_meta
from gsc_mcp.content_trust import observe_untrusted_content
from gsc_mcp.page_challenges import detect_challenge_page
from gsc_mcp.url_safety import (
    URLSafetyError,
    fetch_html_following_redirects,
    safe_fetch_html,
    validate_url_strict,
)

_REQUIRED_FIELDS = {
    "LocalBusiness":       ["name", "@type"],
    "Organization":        ["name", "@type"],
    "FAQPage":             ["mainEntity"],
    "Article":             ["headline", "author", "datePublished"],
    "BlogPosting":         ["headline", "author", "datePublished"],
    "WebSite":             ["name", "url"],
    "BreadcrumbList":      ["itemListElement"],
    "Product":             ["name", "offers"],
    "SoftwareApplication": ["name"],
}

# Google recommends these properties; absence does not invalidate a schema.
# This local field-presence check is not a Google rich-result eligibility test.
# https://developers.google.com/search/docs/appearance/structured-data/software-app
_RECOMMENDED_FIELDS = {
    "SoftwareApplication": ["applicationCategory", "operatingSystem"],
}


_DEPRECATED_RICH_RESULTS = {
    "FAQPage":              "deprecated for rich results May 2026 (Google Search Central)",
    "HowTo":               "deprecated for rich results September 2023",
    "ClaimReview":         "deprecated for rich results June 2025",
    "EstimatedSalary":     "deprecated for rich results June 2025",
    "VehicleListing":      "deprecated for rich results June 2025",
    "SpecialAnnouncement": "deprecated for rich results June 2025",
}


_PATTERN_RECOMMENDATIONS = [
    (r"/faq",      "FAQPage"),
    (r"/blog/",    "BlogPosting"),
    (r"/contact",  "ContactPage"),
    (r"/product",  "Product"),
    (r"/glossary", "DefinedTermSet"),
]


def _primary_type(schema_type) -> str:
    """Reduce a list-valued @type (["Person", "Organization"]) to one string.

    Prefers the first entry that has a required-fields rule, so validation is
    as strict as the data allows; falls back to the first entry.
    """
    if isinstance(schema_type, list):
        names = [t for t in schema_type if isinstance(t, str)]
        if not names:
            return "Unknown"
        return next((t for t in names if t in _REQUIRED_FIELDS), names[0])
    return schema_type if isinstance(schema_type, str) else "Unknown"


class _JsonLdExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self._in_ld = False
        self._chunks: list[str] = []
        self.schemas: list[dict] = []

    def handle_starttag(self, tag, attrs):
        if tag == "script" and dict(attrs).get("type") == "application/ld+json":
            self._in_ld = True
            self._chunks = []

    def handle_endtag(self, tag):
        if tag == "script" and self._in_ld:
            self._in_ld = False
            raw = "".join(self._chunks).strip()
            if raw:
                try:
                    data = json.loads(raw)
                    self._collect_schemas(data)
                except json.JSONDecodeError:
                    pass

    def _collect_schemas(self, data) -> None:
        if isinstance(data, list):
            for item in data:
                self._collect_schemas(item)
        elif isinstance(data, dict):
            # A graph wrapper is not itself an entity unless it has a type.
            if "@type" in data or "@graph" not in data:
                self.schemas.append(data)
            if "@graph" in data:
                self._collect_schemas(data["@graph"])

    def handle_data(self, data):
        if self._in_ld:
            self._chunks.append(data)


def schema_validate(url: str) -> str:
    """Fetch a URL and validate its JSON-LD structured data schemas.

    Detects all <script type="application/ld+json"> blocks, checks required
    fields per schema type, and suggests missing schemas based on URL patterns.
    Does not require authentication -- works on any public URL.

    Returns detected schemas, validation results per schema, and recommendations.
    The valid flag and verdict check only this tool's local required-field
    presence rules, not full Schema.org validity or Google rich-result eligibility.
    Recommended properties are reported separately and do not affect validity.
    Verdicts: healthy (all schemas valid) | missing_schemas (none found) |
              invalid_schemas (found but at least one has missing required fields) |
              challenge_page (known challenge replaces the unavailable page) |
              fetch_error (URL not reachable).
    """
    try:
        html, status, final_url = fetch_html_following_redirects(url)
    except (URLSafetyError, httpx.HTTPError) as e:
        return json.dumps(with_meta(
            {"url": url, "error": str(e), "verdict": "fetch_error", "untrusted_content": None},
            tool="schema_validate",
            params={"url": url},
        ))

    untrusted_content = observe_untrusted_content(html, source_url=final_url)
    challenge = detect_challenge_page(html)
    if challenge:
        return json.dumps(with_meta(
            {
                "url": url,
                "final_url": final_url,
                "http_status": status,
                "challenge": challenge,
                "untrusted_content": untrusted_content,
                "schemas_detected": None,
                "validation_scope": "not_assessed",
                "google_rich_result_eligibility": "not_assessed",
                "schemas": None,
                "recommendations": None,
                "verdict": "challenge_page",
            },
            tool="schema_validate",
            params={"url": url},
        ))

    parser = _JsonLdExtractor()
    parser.feed(html)

    detected: list[dict] = []
    for schema in parser.schemas:
        schema_type = _primary_type(schema.get("@type", "Unknown"))
        required = _REQUIRED_FIELDS.get(schema_type, [])
        missing = [f for f in required if f not in schema]
        missing_recommended = [
            f for f in _RECOMMENDED_FIELDS.get(schema_type, []) if f not in schema
        ]
        deprecated_note = _DEPRECATED_RICH_RESULTS.get(schema_type)
        detected.append({
            "type": schema_type,
            "valid": not missing,
            "missing_required_fields": missing,
            "missing_recommended_fields": missing_recommended,
            "fields_present": [k for k in schema if not k.startswith("@")],
            "deprecated_rich_result": deprecated_note,
        })

    detected_types = {s["type"] for s in detected}
    recommendations = [
        schema_type
        for pattern, schema_type in _PATTERN_RECOMMENDATIONS
        if re.search(pattern, url, re.IGNORECASE) and schema_type not in detected_types
    ]

    if not detected:
        verdict = "missing_schemas"
    elif all(s["valid"] for s in detected):
        verdict = "healthy"
    else:
        verdict = "invalid_schemas"

    return json.dumps(with_meta(
        {
            "url": url,
            "final_url": final_url,
            "schemas_detected": len(detected),
            "untrusted_content": untrusted_content,
            "validation_scope": "local_required_field_presence",
            "google_rich_result_eligibility": "not_assessed",
            "schemas": detected,
            "recommendations": recommendations,
            "verdict": verdict,
        },
        tool="schema_validate",
        params={"url": url},
    ))


# ---------------------------------------------------------------------------
# schema_generate
# Adapted from scripts/schema_generate.py in claude-seo
# (https://github.com/AgriciDaniel/claude-seo, MIT, Copyright (c) 2026 agricidaniel)
# ---------------------------------------------------------------------------


def _strip_nones(payload: object) -> object:
    """Recursively remove None-valued keys from dicts (keeps JSON-LD output tight)."""
    if isinstance(payload, dict):
        return {k: _strip_nones(v) for k, v in payload.items() if v is not None}
    if isinstance(payload, list):
        return [_strip_nones(v) for v in payload]
    return payload


def schema_generate(
    schema_type: str,
    # Reservation
    provider: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    party_size: Optional[int] = None,
    reservation_id: Optional[str] = None,
    reservation_for_name: Optional[str] = None,
    customer_name: Optional[str] = None,
    customer_email: Optional[str] = None,
    reservation_kind: str = "FoodEstablishmentReservation",
    # OrderAction
    merchant: Optional[str] = None,
    order_url: Optional[str] = None,
    order_name: str = "Order online",
    delivery_method: Optional[list[str]] = None,
    # DiscussionForumPosting
    headline: Optional[str] = None,
    author: Optional[str] = None,
    url: Optional[str] = None,
    date_published: Optional[str] = None,
    text: Optional[str] = None,
    date_modified: Optional[str] = None,
    comment_count: Optional[int] = None,
    # ProfilePage
    name: Optional[str] = None,
    profile_url: Optional[str] = None,
    description: Optional[str] = None,
    same_as: Optional[list[str]] = None,
    knows_about: Optional[list[str]] = None,
    works_for: Optional[str] = None,
    image: Optional[str] = None,
    job_title: Optional[str] = None,
) -> str:
    """Generate a Schema.org JSON-LD block for one of four high-leverage types.

    Adapted from scripts/schema_generate.py in claude-seo (agricidaniel, MIT).
    Supports: reservation, order_action, discussion, profile.
    No authentication required. No Google API calls made.

    schema_type: one of "reservation", "order_action", "discussion", "profile".
    Returns the generated JSON-LD block.
    Verdicts: generated | error.
    """
    schema_type_key = schema_type.lower().strip()

    try:
        if schema_type_key == "reservation":
            if not provider or not start_time:
                raise ValueError("reservation requires provider and start_time")
            payload: dict = {
                "@context": "https://schema.org",
                "@type": reservation_kind,
                "reservationStatus": "https://schema.org/ReservationConfirmed",
                "provider": {"@type": "Organization", "name": provider},
                "reservationFor": {
                    "@type": "FoodEstablishment"
                    if reservation_kind == "FoodEstablishmentReservation"
                    else "Place",
                    "name": reservation_for_name or provider,
                },
                "startTime": start_time,
            }
            if end_time:
                payload["endTime"] = end_time
            if party_size is not None:
                payload["partySize"] = int(party_size)
            if reservation_id:
                payload["reservationId"] = reservation_id
            if customer_name or customer_email:
                person: dict = {"@type": "Person"}
                if customer_name:
                    person["name"] = customer_name
                if customer_email:
                    person["email"] = customer_email
                payload["underName"] = person

        elif schema_type_key == "order_action":
            if not merchant or not order_url:
                raise ValueError("order_action requires merchant and order_url")
            payload = {
                "@context": "https://schema.org",
                "@type": "OrderAction",
                "name": order_name,
                "target": {
                    "@type": "EntryPoint",
                    "urlTemplate": order_url,
                    "inLanguage": "en-US",
                    "actionPlatform": [
                        "https://schema.org/DesktopWebPlatform",
                        "https://schema.org/MobileWebPlatform",
                    ],
                },
                "deliveryMethod": delivery_method or [
                    "https://schema.org/OnSitePickup",
                    "https://schema.org/ParcelService",
                ],
                "priceSpecification": {
                    "@type": "PriceSpecification",
                    "eligibleTransactionVolume": {
                        "@type": "PriceSpecification",
                        "minPrice": 0,
                        "priceCurrency": "USD",
                    },
                },
                "merchant": {"@type": "Organization", "name": merchant},
            }

        elif schema_type_key == "discussion":
            if not headline or not author or not url or not date_published:
                raise ValueError(
                    "discussion requires headline, author, url, date_published"
                )
            payload = {
                "@context": "https://schema.org",
                "@type": "DiscussionForumPosting",
                "headline": headline,
                "author": {"@type": "Person", "name": author},
                "datePublished": date_published,
                "url": url,
                "mainEntityOfPage": {"@type": "WebPage", "@id": url},
            }
            if text:
                payload["text"] = text
            if date_modified:
                payload["dateModified"] = date_modified
            if comment_count is not None:
                payload["commentCount"] = int(comment_count)

        elif schema_type_key == "profile":
            if not name or not profile_url:
                raise ValueError("profile requires name and profile_url")
            person_block: dict = {"@type": "Person", "name": name, "url": profile_url}
            if description:
                person_block["description"] = description
            if same_as:
                person_block["sameAs"] = list(same_as)
            if knows_about:
                person_block["knowsAbout"] = list(knows_about)
            if works_for:
                person_block["worksFor"] = {"@type": "Organization", "name": works_for}
            if image:
                person_block["image"] = image
            if job_title:
                person_block["jobTitle"] = job_title
            payload = {
                "@context": "https://schema.org",
                "@type": "ProfilePage",
                "mainEntity": person_block,
                "url": profile_url,
            }

        else:
            raise ValueError(
                f"Unknown schema_type {schema_type!r}. "
                "Supported: reservation, order_action, discussion, profile."
            )

        cleaned = _strip_nones(payload)
        return json.dumps(with_meta(
            {"schema_type": schema_type_key, "json_ld": cleaned, "verdict": "generated"},
            tool="schema_generate",
            params={"schema_type": schema_type},
        ))

    except ValueError as exc:
        return json.dumps(with_meta(
            {"schema_type": schema_type_key, "error": str(exc), "verdict": "error"},
            tool="schema_generate",
            params={"schema_type": schema_type},
        ))


# ---------------------------------------------------------------------------
# ai_visibility_audit
# ---------------------------------------------------------------------------

_AI_CRAWLERS = {
    "GPTBot":           "OpenAI ChatGPT training",
    "ClaudeBot":        "Anthropic Claude training",
    "Claude-User":      "Anthropic Claude user-driven browsing",
    "Claude-SearchBot": "Anthropic Claude search indexing",
    "PerplexityBot":    "Perplexity AI",
    "CCBot":            "Common Crawl (used by multiple AI labs)",
    "Google-Extended":  "Google Gemini / Vertex AI training",
    "cohere-ai":        "Cohere training",
    "Bytespider":       "ByteDance (TikTok parent) crawling",
    "OAI-SearchBot":    "OpenAI search indexing",
}


def ai_visibility_audit(url: str) -> str:
    """Check robots.txt AI crawler access and llms.txt presence for a URL's origin.

    Fetches {origin}/robots.txt and checks each known AI crawler agent.
    Also checks for {origin}/llms.txt (Model Context Protocol discoverability file).
    No authentication required.

    Verdicts: open (all AI crawlers allowed) | partial (some blocked) |
              closed (all blocked or disallow all) | fetch_error.
    """
    try:
        validate_url_strict(url)
    except URLSafetyError as e:
        return json.dumps(with_meta(
            {"url": url, "error": str(e), "verdict": "fetch_error"},
            tool="ai_visibility_audit",
            params={"url": url},
        ))

    parsed = urlparse(url)
    origin = f"{parsed.scheme}://{parsed.netloc}"

    robots_txt_found = False
    robots_text = ""
    try:
        robots_text, _ = safe_fetch_html(f"{origin}/robots.txt")
        robots_txt_found = True
    except (httpx.HTTPError, URLSafetyError):
        robots_txt_found = False

    rp = urllib.robotparser.RobotFileParser()
    if robots_txt_found:
        rp.parse(robots_text.splitlines())

    crawlers: list[dict] = []
    for agent, description in _AI_CRAWLERS.items():
        allowed = rp.can_fetch(agent, url) if robots_txt_found else True
        crawlers.append({"agent": agent, "description": description, "allowed": allowed})

    llms_txt_present = False
    try:
        safe_fetch_html(f"{origin}/llms.txt")
        llms_txt_present = True
    except (httpx.HTTPError, URLSafetyError):
        llms_txt_present = False

    allowed_count = sum(c["allowed"] for c in crawlers)
    total_crawlers = len(crawlers)

    if not robots_txt_found:
        verdict = "open"
    elif allowed_count == total_crawlers:
        verdict = "open"
    elif allowed_count == 0:
        verdict = "closed"
    else:
        verdict = "partial"

    return json.dumps(with_meta(
        {
            "url": url,
            "origin": origin,
            "robots_txt_found": robots_txt_found,
            "llms_txt_present": llms_txt_present,
            "crawlers": crawlers,
            "allowed_count": allowed_count,
            "total_crawlers": total_crawlers,
            "verdict": verdict,
        },
        tool="ai_visibility_audit",
        params={"url": url},
    ))


# ---------------------------------------------------------------------------
# gbp_deprecation_lint
# ---------------------------------------------------------------------------

_GBP_DEPRECATED_PATTERNS = [
    (r"widget\.appointments\.google\.com", "GBP appointment widget embed (deprecated)"),
    (r"reservewithgoogle\.com", "Reserve with Google (deprecated June 2025)"),
    (r"\.business\.site", "business.site link (GBP websites deprecated March 2024)"),
    (r"google\.com/maps/reserve", "Google Maps Reserve (deprecated flow)"),
    (r"gbp[_-]chat[_-]?widget|gmbchatwidget", "GBP chat widget (deprecated)"),
]


def gbp_deprecation_lint(url: str) -> str:
    """Scan a page for deprecated Google Business Profile (GBP) features.

    Checks for GBP chat widget embed scripts, dead .business.site links, and
    Reserve with Google (deprecated) integrations. No authentication required.

    Verdicts: clean | deprecated_found | fetch_error.
    """
    try:
        validate_url_strict(url)
    except URLSafetyError as e:
        return json.dumps(with_meta(
            {"url": url, "error": str(e), "verdict": "fetch_error"},
            tool="gbp_deprecation_lint",
            params={"url": url},
        ))

    try:
        html, _ = safe_fetch_html(url)
    except (httpx.HTTPError, URLSafetyError) as e:
        return json.dumps(with_meta(
            {"url": url, "error": str(e), "verdict": "fetch_error"},
            tool="gbp_deprecation_lint",
            params={"url": url},
        ))

    issues: list[dict] = []
    seen_descriptions: set[str] = set()
    for pattern, description in _GBP_DEPRECATED_PATTERNS:
        if re.search(pattern, html, re.IGNORECASE) and description not in seen_descriptions:
            issues.append({"pattern": pattern, "description": description})
            seen_descriptions.add(description)

    verdict = "deprecated_found" if issues else "clean"

    return json.dumps(with_meta(
        {
            "url": url,
            "issues_count": len(issues),
            "issues": issues,
            "verdict": verdict,
        },
        tool="gbp_deprecation_lint",
        params={"url": url},
    ))


# ---------------------------------------------------------------------------
# pagespeed_audit
# ---------------------------------------------------------------------------


def pagespeed_audit(url: str, strategy: str = "mobile") -> str:
    """Run a PageSpeed Insights audit via Google's PSI API v5.

    Requires GOOGLE_API_KEY environment variable (plain API key, not service account).
    The PageSpeed Insights API must be enabled in the GCP project.

    strategy: "mobile" (default) or "desktop".
    Returns Lighthouse performance score, Core Web Vitals, and top opportunities.
    Verdicts: good (score>=90) | needs_improvement (50-89) | poor (<50) | missing_key | fetch_error.
    """
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        return json.dumps(with_meta(
            {"url": url, "error": "GOOGLE_API_KEY not set", "verdict": "missing_key"},
            tool="pagespeed_audit",
            params={"url": url, "strategy": strategy},
        ))

    try:
        validate_url_strict(url)
    except URLSafetyError as e:
        return json.dumps(with_meta(
            {"url": url, "error": str(e), "verdict": "fetch_error"},
            tool="pagespeed_audit",
            params={"url": url, "strategy": strategy},
        ))

    psi_url = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
    try:
        with httpx.Client(timeout=60) as client:
            resp = client.get(psi_url, params={"url": url, "strategy": strategy, "key": api_key})
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError as e:
        return json.dumps(with_meta(
            {"url": url, "error": str(e), "verdict": "fetch_error"},
            tool="pagespeed_audit",
            params={"url": url, "strategy": strategy},
        ))

    lhr = data.get("lighthouseResult", {})
    categories = lhr.get("categories", {})
    perf_score = categories.get("performance", {}).get("score")
    perf_score_pct = round(perf_score * 100) if perf_score is not None else None

    audits = lhr.get("audits", {})

    def _metric(key: str) -> dict:
        a = audits.get(key, {})
        return {
            "display_value": a.get("displayValue"),
            "score": a.get("score"),
            "numeric_value": a.get("numericValue"),
        }

    cwv = {
        "fcp":         _metric("first-contentful-paint"),
        "lcp":         _metric("largest-contentful-paint"),
        "tbt":         _metric("total-blocking-time"),
        "cls":         _metric("cumulative-layout-shift"),
        "speed_index": _metric("speed-index"),
        "tti":         _metric("interactive"),
    }

    opportunities: list[dict] = []
    for key, audit in audits.items():
        details = audit.get("details", {})
        if details.get("type") == "opportunity" and audit.get("score", 1) < 0.9:
            opportunities.append({
                "id": key,
                "title": audit.get("title"),
                "description": audit.get("description"),
                "score": audit.get("score"),
            })
    opportunities.sort(key=lambda x: x.get("score") or 0)
    top_opportunities = opportunities[:3]

    if perf_score_pct is None:
        verdict = "fetch_error"
    elif perf_score_pct >= 90:
        verdict = "good"
    elif perf_score_pct >= 50:
        verdict = "needs_improvement"
    else:
        verdict = "poor"

    return json.dumps(with_meta(
        {
            "url": url,
            "strategy": strategy,
            "performance_score": perf_score_pct,
            "cwv": cwv,
            "top_opportunities": top_opportunities,
            "verdict": verdict,
        },
        tool="pagespeed_audit",
        params={"url": url, "strategy": strategy},
    ))
