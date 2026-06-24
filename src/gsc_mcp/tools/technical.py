import ipaddress
import json
import re
import socket
from html.parser import HTMLParser

import httpx

from gsc_mcp.meta import with_meta

_REQUIRED_FIELDS = {
    "LocalBusiness":       ["name", "@type"],
    "Organization":        ["name", "@type"],
    "FAQPage":             ["mainEntity"],
    "Article":             ["headline", "author", "datePublished"],
    "BlogPosting":         ["headline", "author", "datePublished"],
    "WebSite":             ["name", "url"],
    "BreadcrumbList":      ["itemListElement"],
    "Product":             ["name", "offers"],
    "SoftwareApplication": ["name", "applicationCategory", "operatingSystem"],
}

def _reject_ssrf(url: str) -> None:
    """Raise ValueError if url resolves to a private, loopback, or link-local IP."""
    host = httpx.URL(url).host
    if not host:
        raise ValueError(f"Cannot parse hostname from {url!r}")
    try:
        results = socket.getaddrinfo(host, None)
    except socket.gaierror as exc:
        raise ValueError(f"Cannot resolve {host!r}: {exc}") from exc
    for *_, sockaddr in results:
        ip = ipaddress.ip_address(sockaddr[0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            raise ValueError(f"Blocked: {host!r} resolves to restricted IP {ip}")


_PATTERN_RECOMMENDATIONS = [
    (r"/faq",      "FAQPage"),
    (r"/blog/",    "BlogPosting"),
    (r"/contact",  "ContactPage"),
    (r"/product",  "Product"),
    (r"/glossary", "DefinedTermSet"),
]


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
                    if isinstance(data, list):
                        self.schemas.extend(data)
                    else:
                        self.schemas.append(data)
                except json.JSONDecodeError:
                    pass

    def handle_data(self, data):
        if self._in_ld:
            self._chunks.append(data)


def schema_validate(url: str) -> str:
    """Fetch a URL and validate its JSON-LD structured data schemas.

    Detects all <script type="application/ld+json"> blocks, checks required
    fields per schema type, and suggests missing schemas based on URL patterns.
    Does not require authentication — works on any public URL.

    Returns detected schemas, validation results per schema, and recommendations.
    Verdicts: healthy (all schemas valid) | missing_schemas (none found) |
              invalid_schemas (found but at least one has missing required fields) |
              fetch_error (URL not reachable).
    """
    try:
        _reject_ssrf(url)
    except ValueError as e:
        return json.dumps(with_meta(
            {"url": url, "error": str(e), "verdict": "fetch_error"},
            tool="schema_validate",
            params={"url": url},
        ))
    try:
        with httpx.Client(timeout=15, follow_redirects=False) as client:
            resp = client.get(url, headers={"User-Agent": "gsc-mcp-schema-validator/1.0"})
            resp.raise_for_status()
            html = resp.text
    except httpx.HTTPError as e:
        return json.dumps(with_meta(
            {"url": url, "error": str(e), "verdict": "fetch_error"},
            tool="schema_validate",
            params={"url": url},
        ))

    parser = _JsonLdExtractor()
    parser.feed(html)

    detected: list[dict] = []
    for schema in parser.schemas:
        schema_type = schema.get("@type", "Unknown")
        required = _REQUIRED_FIELDS.get(schema_type, [])
        missing = [f for f in required if f not in schema]
        detected.append({
            "type": schema_type,
            "valid": not missing,
            "missing_required_fields": missing,
            "fields_present": [k for k in schema if not k.startswith("@")],
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
            "schemas_detected": len(detected),
            "schemas": detected,
            "recommendations": recommendations,
            "verdict": verdict,
        },
        tool="schema_validate",
        params={"url": url},
    ))
