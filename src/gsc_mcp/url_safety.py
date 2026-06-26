"""
SSRF/DNS-rebinding protection module for gsc-mcp.

Adapted from scripts/url_safety.py in claude-seo
(https://github.com/AgriciDaniel/claude-seo, MIT License, Copyright (c) 2026 agricidaniel).

Public API
==========

validate_url(url) -> bool
    Boolean check without DNS resolution. Rejects non-http(s) schemes, missing
    hostnames, hard-blocked hostnames (localhost, cloud metadata endpoints), and
    IP literals in private/loopback/reserved ranges.

validate_url_strict(url) -> tuple[str, str]
    Resolves hostname via socket.getaddrinfo, validates every A record, returns
    (normalized_url, pinned_ipv4). Raises URLSafetyError if any resolved IP is
    non-public. Use before opening any network connection to prevent DNS rebinding.

safe_httpx_get(url, *, timeout=15, **kwargs) -> httpx.Response
    httpx.Client.get() wrapped in DNS-pinning. Validates before connect.

safe_httpx_client(url, *, timeout=15) -> context manager yielding httpx.Client
    Same protection for callers that need a client instance for multiple requests.

safe_fetch_html(url, *, timeout=15) -> tuple[str, int]
    Convenience: fetch a URL and return (html_text, status_code). Raises
    URLSafetyError on SSRF block, httpx.HTTPError on network/HTTP errors.

is_safe_ip(ip_str) -> bool
    True iff the address is a public unicast IPv4/IPv6 address.

URLSafetyError
    ValueError subclass raised on SSRF safety failures.
"""

from __future__ import annotations

import ipaddress
import re
import socket
import threading
from contextlib import contextmanager
from typing import Iterator
from urllib.parse import urlparse

import httpx


__all__ = [
    "URLSafetyError",
    "is_safe_ip",
    "normalize_hostname",
    "validate_url",
    "validate_url_strict",
    "safe_httpx_get",
    "safe_httpx_client",
    "safe_fetch_html",
]


# Regex matching IPv4 obfuscation forms glibc/inet_aton accepts:
# dotted-quad, dotted with leading zeros, hex, octal, integer forms.
_IPV4_OBFUSCATED_RE = re.compile(
    r"^(?:0x[0-9a-f]+|[0-9]+)(?:\.(?:0x[0-9a-f]+|[0-9]+)){0,3}$",
    re.IGNORECASE,
)

# Hard-blocked hostnames refused before DNS resolution. Multi-cloud metadata
# endpoints listed explicitly for defence-in-depth.
_BLOCKED_HOSTNAMES: frozenset[str] = frozenset(
    {
        "localhost",
        "ip6-localhost",
        "ip6-loopback",
        "metadata.google.internal",
        "metadata.goog",
        "metadata",
        "metadata.azure.com",
        "metadata.ec2.internal",
        "metadata.oraclecloud.com",
        # Numeric forms also caught by IP literal check below.
        "127.0.0.1",
        "0.0.0.0",
        "::1",
        "169.254.169.254",  # AWS/Azure/GCP/Oracle/Alibaba metadata IPv4
        "fd00:ec2::254",    # AWS IMDS IPv6
    }
)


class URLSafetyError(ValueError):
    """Raised when a URL fails SSRF safety checks."""


def _raw_authority(url: str) -> str:
    """Return the undecoded authority substring between scheme and path."""
    match = re.match(r"^[A-Za-z][A-Za-z0-9+.-]*://([^/?#]*)", url)
    return match.group(1) if match else ""


def _reject_authority_confusion(url: str, parsed) -> None:
    """Reject URL forms where parsers can disagree on the effective host."""
    authority = _raw_authority(url)
    authority_lower = authority.lower()
    url_lower = url.lower()
    if "\\" in authority or "%5c" in authority_lower:
        raise URLSafetyError("URL authority contains a backslash")
    if "%" in authority:
        raise URLSafetyError("URL authority contains percent-encoding")
    if parsed.username is not None or parsed.password is not None or "@" in authority:
        raise URLSafetyError("URL userinfo is not allowed")
    if "#@" in url or "%23@" in url_lower:
        raise URLSafetyError("URL fragment/userinfo confusion refused")


def is_safe_ip(ip_str: str) -> bool:
    """Return True iff ip_str is a public unicast IPv4 or IPv6 address."""
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return False
    return not (
        ip.is_private
        or ip.is_loopback
        or ip.is_reserved
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_unspecified
    )


def normalize_hostname(hostname: str) -> str:
    """Canonicalize hostname to block IPv4 obfuscation and FQDN trailing-dot bypasses.

    1. Lowercased.
    2. Trailing dot stripped (FQDN form, e.g. metadata.google.internal.).
    3. Obfuscated IPv4 forms (decimal, hex, octal, leading zeros) canonicalized
       via socket.inet_aton so they hit the same IP-range checks as dotted-quad.
    """
    if not hostname:
        raise URLSafetyError("Empty hostname")
    h = hostname.lower().strip()
    if h.endswith(".") and not h.endswith(".."):
        h = h[:-1]
    if _IPV4_OBFUSCATED_RE.match(h):
        try:
            packed = socket.inet_aton(h)
        except OSError as exc:
            raise URLSafetyError(
                f"Malformed IPv4 obfuscation refused: {hostname!r} ({exc})"
            ) from exc
        h = socket.inet_ntoa(packed)
    return h


def validate_url(url: str) -> bool:
    """Boolean SSRF check without DNS resolution.

    Returns False for non-http(s) schemes, missing hostnames, hard-blocked
    hostnames, obfuscated private IP literals. Returns True for all other
    well-formed http(s) URLs with public-looking hostnames.
    Use validate_url_strict before opening a socket.
    """
    try:
        parsed = urlparse(url)
        _reject_authority_confusion(url, parsed)
        if parsed.scheme not in ("http", "https"):
            return False
        if not parsed.hostname:
            return False
        hostname = normalize_hostname(parsed.hostname)
    except URLSafetyError:
        return False
    if hostname in _BLOCKED_HOSTNAMES:
        return False
    try:
        ipaddress.ip_address(hostname)
    except ValueError:
        return True  # DNS name, not an IP literal.
    return is_safe_ip(hostname)


def validate_url_strict(url: str) -> tuple[str, str]:
    """Resolve hostname and validate all A records. Returns (url, pinned_ipv4).

    Every returned A record must be a public IP. A hostname with a single
    private record alongside public records is refused to prevent race-condition
    DNS rebinding attacks.
    """
    parsed = urlparse(url)
    _reject_authority_confusion(url, parsed)
    if parsed.scheme not in ("http", "https"):
        raise URLSafetyError(f"Invalid URL scheme: {parsed.scheme!r}")
    if not parsed.hostname:
        raise URLSafetyError("URL has no hostname")

    hostname = normalize_hostname(parsed.hostname)
    if hostname in _BLOCKED_HOSTNAMES:
        raise URLSafetyError(f"Blocked hostname: {hostname}")

    try:
        literal = ipaddress.ip_address(hostname)
    except ValueError:
        literal = None

    if literal is not None:
        if not is_safe_ip(hostname):
            raise URLSafetyError(f"Blocked IP literal: {hostname}")
        return url, str(literal)

    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        addrinfo = socket.getaddrinfo(
            hostname,
            port,
            family=socket.AF_INET,
            type=socket.SOCK_STREAM,
        )
    except (socket.gaierror, UnicodeError) as exc:
        raise URLSafetyError(f"DNS resolution failed for {hostname}: {exc}") from exc

    resolved_ips = sorted({info[4][0] for info in addrinfo})
    if not resolved_ips:
        raise URLSafetyError(f"No A records for {hostname}")

    for ip_str in resolved_ips:
        if not is_safe_ip(ip_str):
            raise URLSafetyError(
                f"DNS rebinding refused: {hostname} resolves to "
                f"non-public IP {ip_str}"
            )

    return url, resolved_ips[0]


# A single non-blocking lock guards the global getaddrinfo monkey-patch.
# Two concurrent pinned fetches raise rather than corrupt the global resolver.
_dns_patch_lock = threading.Lock()


@contextmanager
def _pin_dns(hostname: str, pinned_ip: str, port: int) -> Iterator[None]:
    """Override socket.getaddrinfo so hostname resolves only to pinned_ip.

    Also validates every other hostname resolved during the pinned scope against
    is_safe_ip to catch redirect-target DNS rebinding (a redirect from the
    target host to a private hostname would otherwise bypass validation).
    """
    if not _dns_patch_lock.acquire(blocking=False):
        raise URLSafetyError(
            "DNS-pinned fetch already in progress on another thread; "
            "url_safety is not thread-safe by design."
        )

    original_getaddrinfo = socket.getaddrinfo
    target = hostname.lower()

    def patched(host, requested_port, *args, **kwargs):
        if host and host.lower() == target:
            family = kwargs.get("family", args[0] if args else 0)
            if family in (0, socket.AF_UNSPEC, socket.AF_INET):
                return [(
                    socket.AF_INET,
                    socket.SOCK_STREAM,
                    socket.IPPROTO_TCP,
                    "",
                    (pinned_ip, requested_port or port),
                )]
            raise socket.gaierror(
                socket.EAI_FAIL,
                f"url_safety: address family {family} refused for pinned IPv4 host {host}",
            )
        result = original_getaddrinfo(host, requested_port, *args, **kwargs)
        for info in result:
            sockaddr = info[4]
            if not sockaddr:
                continue
            ip_str = sockaddr[0]
            if not is_safe_ip(ip_str):
                raise socket.gaierror(
                    socket.EAI_FAIL,
                    f"url_safety: refused to resolve {host!r} to non-public IP {ip_str}",
                )
        return result

    socket.getaddrinfo = patched  # type: ignore[assignment]
    try:
        yield
    finally:
        socket.getaddrinfo = original_getaddrinfo  # type: ignore[assignment]
        _dns_patch_lock.release()


def safe_httpx_get(url: str, *, timeout: int = 15, **kwargs) -> httpx.Response:
    """httpx GET with DNS-rebinding protection.

    The hostname is pinned to the pre-validated IP for the duration of the call.
    Standard httpx semantics otherwise.
    """
    norm_url, pinned_ip = validate_url_strict(url)
    parsed = urlparse(norm_url)
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    assert parsed.hostname is not None  # validate_url_strict guarantees this
    with _pin_dns(parsed.hostname, pinned_ip, port):
        with httpx.Client(timeout=timeout) as client:
            return client.get(norm_url, **kwargs)


@contextmanager
def safe_httpx_client(url: str, *, timeout: int = 15) -> Iterator[httpx.Client]:
    """Yield an httpx.Client whose connections to url's hostname are DNS-pinned."""
    norm_url, pinned_ip = validate_url_strict(url)
    parsed = urlparse(norm_url)
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    assert parsed.hostname is not None
    with httpx.Client(timeout=timeout) as client:
        with _pin_dns(parsed.hostname, pinned_ip, port):
            yield client


def safe_fetch_html(url: str, *, timeout: int = 15) -> tuple[str, int]:
    """Fetch url safely and return (html_text, status_code).

    No redirects followed (follow_redirects=False). Raises URLSafetyError on
    SSRF block, httpx.HTTPError on HTTP errors.
    """
    resp = safe_httpx_get(
        url,
        timeout=timeout,
        follow_redirects=False,
        headers={"User-Agent": "gsc-mcp/1.0"},
    )
    resp.raise_for_status()
    return resp.text, resp.status_code


def _cli() -> None:
    """Minimal CLI for manual SSRF policy checks."""
    import argparse
    import json
    import sys

    parser = argparse.ArgumentParser(description="Validate a URL against gsc-mcp SSRF policy.")
    parser.add_argument("url", help="URL to validate")
    parser.add_argument("--strict", action="store_true", help="Run DNS resolution.")
    parser.add_argument("--json", action="store_true", help="Emit JSON output.")
    args = parser.parse_args()

    result: dict = {
        "url": args.url,
        "mode": "strict" if args.strict else "parse",
        "ok": None,
        "pinned_ip": None,
        "error": None,
    }

    try:
        if args.strict:
            _, ip = validate_url_strict(args.url)
            result["ok"] = "true"
            result["pinned_ip"] = ip
        else:
            result["ok"] = "true" if validate_url(args.url) else "false"
    except URLSafetyError as exc:
        result["ok"] = "false"
        result["error"] = str(exc)

    if args.json:
        print(json.dumps(result, indent=2))
        if result["ok"] != "true":
            sys.exit(2)
    else:
        if result["ok"] == "true":
            extra = f" -> {result['pinned_ip']}" if result["pinned_ip"] else ""
            print(f"OK: {args.url}{extra}")
        else:
            print(f"BLOCKED: {args.url} ({result['error'] or 'parse-time reject'})")
            sys.exit(2)


if __name__ == "__main__":
    _cli()
