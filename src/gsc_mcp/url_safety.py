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

validate_same_origin(site, candidate) -> None
    Requires site to be an HTTPS origin and candidate to use the exact same
    scheme, normalized hostname, and effective port. Performs no DNS lookup.

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
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterator
from urllib.parse import urljoin, urlparse, urlsplit, urlunsplit

import httpx


__all__ = [
    "URLSafetyError",
    "is_safe_ip",
    "normalize_hostname",
    "validate_url",
    "validate_url_strict",
    "validate_same_origin",
    "safe_httpx_get",
    "safe_httpx_client",
    "safe_fetch_html",
    "fetch_html_following_redirects",
    "FetchObservationBudget",
    "observe_get_redirects",
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
    return ip.is_global and not (
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


def _effective_port(parsed) -> int:
    try:
        explicit_port = parsed.port
    except ValueError as exc:
        raise URLSafetyError("URL has an invalid port") from exc
    if explicit_port is not None:
        return explicit_port
    return 443 if parsed.scheme == "https" else 80


def validate_same_origin(site: str, candidate: str) -> None:
    """Require candidate to share site's exact HTTPS origin without DNS lookup."""
    try:
        site_parsed = urlparse(site)
        candidate_parsed = urlparse(candidate)
    except ValueError as exc:
        raise URLSafetyError("Malformed URL") from exc
    _reject_authority_confusion(site, site_parsed)
    _reject_authority_confusion(candidate, candidate_parsed)

    if site_parsed.scheme != "https" or not site_parsed.hostname:
        raise URLSafetyError("Site must be an HTTPS origin")
    if (
        site_parsed.path not in ("", "/")
        or "?" in site
        or "#" in site
    ):
        raise URLSafetyError("Site must not contain a path, query, or fragment")
    if candidate_parsed.scheme not in ("http", "https") or not candidate_parsed.hostname:
        raise URLSafetyError("Candidate must be an HTTP(S) URL")

    site_origin = (
        site_parsed.scheme,
        normalize_hostname(site_parsed.hostname),
        _effective_port(site_parsed),
    )
    candidate_origin = (
        candidate_parsed.scheme,
        normalize_hostname(candidate_parsed.hostname),
        _effective_port(candidate_parsed),
    )
    if candidate_origin != site_origin:
        raise URLSafetyError("Candidate URL is outside the declared site origin")


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


# Same-site canonicalization redirects (http -> https, bare domain <-> www,
# trailing slash) are common and not worth reporting as a fetch failure. Each
# hop below re-enters safe_fetch_html, so it gets the same DNS-pinned SSRF
# check as a direct request; nothing here trusts httpx's own follow_redirects.
# A redirect to any other site is refused: the caller is auditing one site,
# and following it would attribute another site's page to the original URL.
_MAX_REDIRECT_HOPS = 5
_REDIRECT_STATUSES = frozenset({301, 302, 303, 307, 308})


def _site_key(url: str) -> tuple[str, int | None]:
    """(hostname without a leading 'www.', explicit port) used to compare redirect hops.

    The explicit port is kept as-is (not the effective one) so that an
    http -> https hop on the same host still counts as the same site.
    Malformed targets raise URLSafetyError so callers return fetch_error.
    """
    try:
        parsed = urlparse(url)
        port = parsed.port
    except ValueError as exc:
        raise URLSafetyError(f"Redirect target has an invalid port or authority: {url}") from exc
    host = (parsed.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    return host, port


def fetch_html_following_redirects(
    url: str, max_redirects: int = _MAX_REDIRECT_HOPS, *, timeout: int = 15
) -> tuple[str, int, str]:
    """Fetch url, following same-site redirects one safety-checked hop at a time.

    Returns (html_text, status_code, final_url).

    safe_fetch_html itself never follows a redirect (follow_redirects=False,
    by SSRF design: httpx's built-in following would connect to the redirect
    target without re-running DNS-pinning on it). This wraps it in a bounded
    loop instead: each hop is a fresh safe_fetch_html call, which re-validates
    and re-pins the new host exactly as it would for a direct request. A
    redirect to a private or metadata address is refused at that hop like any
    other unsafe URL, rather than silently followed.

    Only 301/302/303/307/308 are followed, and only when the target is the
    same site (same host ignoring a leading "www.", same explicit port; the
    scheme may change). Anything else raises URLSafetyError.
    """
    current = url
    for _ in range(max_redirects + 1):
        try:
            html, status = safe_fetch_html(current, timeout=timeout)
            return html, status, current
        except httpx.HTTPStatusError as exc:
            location = exc.response.headers.get("location")
            if exc.response.status_code not in _REDIRECT_STATUSES or not location:
                raise
            try:
                target = urljoin(current, location)
            except ValueError as parse_error:
                raise URLSafetyError(
                    f"Redirect target has an invalid port or authority: {location}"
                ) from parse_error
            if _site_key(target) != _site_key(current):
                raise URLSafetyError(
                    f"Cross-site redirect refused: {current} -> {target}"
                ) from exc
            current = target
    raise URLSafetyError(f"Too many redirects (> {max_redirects}) starting at {url}")


@dataclass
class FetchObservationBudget:
    """Shared sequential request cap and cooperative scheduling deadline.

    DNS and individual socket phases are synchronous: the deadline prevents
    scheduling further work, but cannot cancel an in-flight resolver call.
    """

    max_requests: int
    deadline_monotonic: float
    requests_started: int = 0
    dns_refusals: int = 0


def redact_observation_url(value: str) -> str:
    """Remove rejected URL userinfo from page-derived output, including malformed URLs."""
    return re.sub(r"(//)[^/?#]*@", r"\1[redacted]@", value)


def resolve_observation_reference(base_url: str, reference: str) -> str:
    """Resolve href/Location while retaining an explicitly empty query.

    urllib's urljoin loses the query delimiter or inherits base query bytes for
    references such as '?' and '/a?'. Preserve that raw reference distinction
    before normalization, including fragments and protocol-relative URLs.
    Empty/fragment-only references also inherit a defined-empty base query.
    """
    resolved = urljoin(base_url, reference)
    before_fragment = reference.split("#", 1)[0]
    base_before_fragment = base_url.split("#", 1)[0]
    explicit_empty_query = "?" in before_fragment and before_fragment.split("?", 1)[1] == ""
    inherited_empty_query = (before_fragment == "" and "?" in base_before_fragment
                             and base_before_fragment.split("?", 1)[1] == "")
    if explicit_empty_query or inherited_empty_query:
        path, marker, fragment = resolved.partition("#")
        resolved = path.split("?", 1)[0] + "?"
        if marker:
            resolved += "#" + fragment
    return resolved


def normalize_observation_url(url: str) -> str:
    """Validate raw syntax before constructing a query-preserving fetch identity.

    No DNS lookup here. IPv6 is explicitly unsupported by the IPv4 pinning
    transport. Path case, escapes, slash and query ordering stay untouched.
    """
    if not isinstance(url, str) or re.search(r"[\x00-\x20\x7f]", url):
        raise URLSafetyError("invalid_url")
    try:
        parsed = urlsplit(url)
        _reject_authority_confusion(url, parsed)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise URLSafetyError("invalid_url")
        host = normalize_hostname(parsed.hostname).encode("idna").decode("ascii")
        port = _effective_port(parsed)
        if not 1 <= port <= 65535:
            raise URLSafetyError("invalid_url")
        try:
            literal = ipaddress.ip_address(host)
        except ValueError:
            literal = None
        if literal is not None and literal.version != 4:
            raise URLSafetyError("unsupported_address_family")
        if host in _BLOCKED_HOSTNAMES or (literal is not None and not is_safe_ip(host)):
            raise URLSafetyError("unsafe_url")
        authority = host if port == (443 if parsed.scheme == "https" else 80) else f"{host}:{port}"
        normalized = urlunsplit((parsed.scheme, authority, parsed.path or "/", parsed.query, ""))
        if "?" in url.split("#", 1)[0] and not parsed.query:
            normalized += "?"
        return normalized
    except (ValueError, UnicodeError) as exc:
        if isinstance(exc, URLSafetyError) and str(exc) in {"invalid_url", "unsafe_url", "unsupported_address_family"}:
            raise
        raise URLSafetyError("invalid_url") from exc


def observation_site_key(url: str) -> tuple[str, int | None]:
    """Eligibility: one www alias, standard web ports, otherwise exact numeric port."""
    parsed = urlsplit(normalize_observation_url(url))
    host = parsed.hostname
    assert host is not None
    if host.startswith("www."):
        host = host[4:]
    port = _effective_port(parsed)
    return host, None if port == (443 if parsed.scheme == "https" else 80) else port


def _observation_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def observe_get_redirects(
    url: str, *, site_url: str, budget: FetchObservationBudget,
    max_redirects: int = 5, timeout: float = 10.0, max_body_bytes: int = 0,
) -> dict:
    """Observe terminal status and each received hop without eager body reads.

    Source callers may request bounded raw identity bytes; target callers use
    zero and never consume response bodies. Bounds describe application body
    consumption, not exact socket traffic. The deadline is cooperative, not a
    hard wall-clock guarantee. Existing eager fetcher semantics are unchanged.
    """
    started = time.monotonic()
    result = {"requested_url": redact_observation_url(url), "last_requested_url": None,
              "last_response_url": None, "final_url": None, "attempted": False,
              "status_code": None, "last_observed_status": None, "hops": [],
              "outcome": "unavailable", "availability_reason": None,
              "started_at": _observation_timestamp(), "completed_at": None,
              "elapsed_ms": 0.0, "body_complete": False}
    if max_body_bytes:
        result["body"] = b""
    current, seen, followed = url, set(), 0
    try:
        original_site = observation_site_key(site_url)
        while True:
            current = normalize_observation_url(current)
            if observation_site_key(current) != original_site:
                result["availability_reason"] = "out_of_scope_redirect"
                break
            if current in seen:
                result["availability_reason"] = "redirect_loop"
                break
            if budget.requests_started >= budget.max_requests:
                result["availability_reason"] = "skipped_request_budget"
                break
            if time.monotonic() >= budget.deadline_monotonic:
                result["availability_reason"] = "skipped_deadline"
                break
            try:
                normalized, pinned_ip = validate_url_strict(current)
            except URLSafetyError as exc:
                budget.dns_refusals += 1
                result["availability_reason"] = "dns_failure" if "DNS resolution failed" in str(exc) else "dns_refused"
                break
            if ipaddress.ip_address(pinned_ip).version != 4:
                result["availability_reason"] = "unsupported_address_family"
                break
            remaining = budget.deadline_monotonic - time.monotonic()
            if remaining <= 0:
                result["availability_reason"] = "skipped_deadline"
                break
            parsed = urlsplit(normalized)
            hop_started = time.monotonic()
            with _pin_dns(parsed.hostname, pinned_ip, _effective_port(parsed)):
                with httpx.Client(timeout=min(timeout, remaining), trust_env=False,
                                  follow_redirects=False,
                                  headers={"User-Agent": "gsc-mcp/1.0", "Accept-Encoding": "identity"}) as client:
                    budget.requests_started += 1
                    result["attempted"] = True
                    result["last_requested_url"] = current
                    seen.add(current)
                    with client.stream("GET", current) as response:
                        status = response.status_code
                        location = response.headers.get("location")
                        hop = {"requested_url": current, "status_code": status,
                               "location": redact_observation_url(location) if location else location,
                               "next_url": None, "observed_at": _observation_timestamp(),
                               "elapsed_ms": round((time.monotonic() - hop_started) * 1000, 3)}
                        result["hops"].append(hop)
                        result["last_response_url"] = current
                        result["last_observed_status"] = status
                        if status in _REDIRECT_STATUSES:
                            if not location:
                                result["availability_reason"] = "redirect_missing_location"
                                break
                            # Validate before urljoin, which can erase raw control characters.
                            if re.search(r"[\x00-\x20\x7f]", location):
                                raise URLSafetyError("invalid_url")
                            try:
                                next_url = resolve_observation_reference(current, location)
                            except ValueError as exc:
                                raise URLSafetyError("invalid_url") from exc
                            hop["next_url"] = redact_observation_url(next_url)
                            # Record the received hop before rejecting its destination.
                            next_url = normalize_observation_url(next_url)
                            if observation_site_key(next_url) != original_site:
                                result["availability_reason"] = "out_of_scope_redirect"
                                break
                            if next_url in seen:
                                result["availability_reason"] = "redirect_loop"
                                break
                            if followed >= max_redirects:
                                result["availability_reason"] = "redirect_hop_budget"
                                break
                            followed += 1
                            current = next_url
                            continue
                        result["final_url"] = current
                        result["status_code"] = status
                        if max_body_bytes and 200 <= status < 300:
                            if response.headers.get("content-encoding", "identity").lower() not in {"", "identity"}:
                                result["availability_reason"] = "unsupported_content_encoding"
                                break
                            length = response.headers.get("content-length", "")
                            if length.isdigit() and int(length) > max_body_bytes:
                                result["availability_reason"] = "source_body_limit"
                                break
                            body = bytearray()
                            chunks = iter(response.iter_raw(chunk_size=min(8192, max_body_bytes + 1)))
                            while True:
                                if time.monotonic() >= budget.deadline_monotonic:
                                    result["availability_reason"] = "skipped_deadline"
                                    break
                                try:
                                    chunk = next(chunks)
                                except StopIteration:
                                    break
                                room = max_body_bytes - len(body)
                                body.extend(chunk[:room])
                                if len(chunk) > room:
                                    result["availability_reason"] = "source_body_limit"
                                    break
                            result["body"] = bytes(body)
                            if result["availability_reason"] is not None:
                                break
                            result["body_complete"] = True
                        result["outcome"] = "observed"
                        break
    except URLSafetyError as exc:
        reason = str(exc)
        result["availability_reason"] = reason if reason in {"invalid_url", "unsafe_url", "unsupported_address_family"} else "dns_pin_unavailable"
    except httpx.TimeoutException:
        result["availability_reason"] = "timeout"
    except httpx.HTTPError:
        result["availability_reason"] = "network_error"
    finally:
        result["completed_at"] = _observation_timestamp()
        result["elapsed_ms"] = round((time.monotonic() - started) * 1000, 3)
    return result


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
