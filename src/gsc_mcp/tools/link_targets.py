"""Bounded internal destination status observations, without a recursive crawl."""

from __future__ import annotations

import json
import re
import time
from datetime import datetime, timezone
from urllib.parse import urlsplit

from gsc_mcp.content_trust import observe_untrusted_content
from gsc_mcp.meta import with_meta
from gsc_mcp.tools.links import _LinkParser
from gsc_mcp.url_safety import (
    FetchObservationBudget, URLSafetyError, normalize_observation_url,
    observation_site_key, observe_get_redirects, redact_observation_url, resolve_observation_reference,
)


def link_targets_audit(url: str, max_targets: int = 30, max_requests: int = 60) -> str:
    """Check one page's internal HTTP(S) link targets, retaining every anchor.

    Public pages only; no authentication or Google API calls. Physical GETs
    (including source redirects and failed requests) share the request budget.
    Target bodies are not read; source raw identity bytes are capped at 1 MiB.
    Same-site scope allows one www alias and standard HTTP/HTTPS ports. Custom
    ports must match numerically. Query bytes/order, path case and trailing slash
    remain distinct identities. Relative links use the served URL; HTML base is
    ignored. The 60-second scheduling deadline cannot cancel synchronous DNS.
    HTTP observations do not establish Google indexation or ranking impact.
    """
    for name, value, upper in [("max_targets", max_targets, 100), ("max_requests", max_requests, 200)]:
        if type(value) is not int or not 1 <= value <= upper:
            raise ValueError(f"{name} must be an integer between 1 and {upper}")
    started = time.monotonic()
    budget = FetchObservationBudget(max_requests, started + 60)
    source = observe_get_redirects(url, site_url=url, budget=budget, max_body_bytes=1024 * 1024)
    body = source.pop("body")
    data = {"source_requested_url": redact_observation_url(url), "source_final_url": source["final_url"],
            "source_observation": source, "collected_at": datetime.now(timezone.utc).isoformat(),
            "scope_policy": "same_site_www_alias_default_ports", "coverage": "unavailable",
            "source_body_complete": source["body_complete"], "total_anchors": 0,
            "distinct_in_scope_targets": 0, "targets_attempted": 0, "targets_completed": 0,
            "targets_skipped": 0, "excluded_reasons": {}, "targets": [], "untrusted_content": None,
            "limitations": ["HTML base is ignored; relative hrefs resolve against served source URL",
                            "IPv4 pinning only; IPv6-only hosts have no supported A transport",
                            "Scheduling deadline cannot cancel synchronous DNS or socket work",
                            "Body limits cover application consumption, not exact socket traffic"]}
    if source["outcome"] == "observed" and source["body_complete"] and 200 <= source["status_code"] < 300:
        html = body.decode("utf-8", errors="replace")
        parser = _LinkParser()
        parser.feed(html)
        parser.close()
        final_source = source["final_url"]
        data["untrusted_content"] = observe_untrusted_content(redact_observation_url(html), source_url=final_source)
        data["untrusted_content"]["page_derived_fields"] = ["targets[].source_links", "targets[].hops[].location", "targets[].hops[].next_url"]
        data["total_anchors"] = len(parser.links)
        groups = {}
        excluded = data["excluded_reasons"]
        for link in parser.links:
            raw = link["href"] or ""
            href = raw.strip()
            reason = None
            if not href:
                reason = "empty_href"
            elif href.startswith("#"):
                reason = "fragment_only"
            else:
                try:
                    if re.search(r"[\x00-\x1f\x7f]", raw):
                        raise URLSafetyError("invalid_url")
                    absolute = resolve_observation_reference(final_source, href)
                    if urlsplit(absolute).scheme not in {"http", "https"}:
                        reason = "non_http_scheme"
                    else:
                        identity = normalize_observation_url(absolute)
                        if observation_site_key(identity) != observation_site_key(final_source):
                            reason = "external"
                        else:
                            groups.setdefault(identity, []).append({
                                "source_requested_url": redact_observation_url(url), "source_final_url": final_source,
                                "href": redact_observation_url(raw), "absolute_url": absolute,
                                "anchor": link["anchor"], "zone": link["zone"], "rel": link["rel"]})
                except (ValueError, UnicodeError):
                    reason = "invalid_url"
            if reason:
                excluded[reason] = excluded.get(reason, 0) + 1
        data["distinct_in_scope_targets"] = len(groups)
        for index, (identity, associations) in enumerate(groups.items()):
            if index >= max_targets:
                observation = {"requested_url": identity, "last_requested_url": None, "last_response_url": None,
                               "final_url": None, "attempted": False, "status_code": None,
                               "last_observed_status": None, "hops": [], "outcome": "unavailable",
                               "availability_reason": "skipped_target_budget", "started_at": None,
                               "completed_at": None, "elapsed_ms": None}
            else:
                observation = observe_get_redirects(identity, site_url=final_source, budget=budget)
                observation.pop("body", None)
                observation.pop("body_complete")
            status = observation["status_code"]
            findings = []
            if status in {404, 410}:
                findings.append("http_not_found")
            elif status is not None and status >= 400:
                findings.append("http_error")
            if len(observation["hops"]) > 1:
                findings.append("redirect_chain")
            if observation["availability_reason"] == "redirect_loop":
                findings.append("redirect_loop")
            data["targets"].append({**observation, "source_links": associations, "findings": findings})
        data["targets_attempted"] = sum(t["attempted"] for t in data["targets"])
        data["targets_completed"] = sum(t["outcome"] == "observed" for t in data["targets"])
        data["targets_skipped"] = sum(not t["attempted"] for t in data["targets"])
        data["coverage"] = "complete" if data["targets_completed"] == len(groups) else "partial"
    elapsed = time.monotonic() - started
    data["budgets"] = {"max_targets": max_targets, "max_requests": max_requests,
                       "requests_started": budget.requests_started, "dns_refusals": budget.dns_refusals,
                       "max_redirects": 5, "request_timeout_seconds": 10, "scheduling_deadline_seconds": 60,
                       "source_max_body_bytes": 1024 * 1024, "target_max_body_bytes": 0,
                       "elapsed_ms": round(elapsed * 1000, 3), "deadline_overrun": elapsed > 60}
    return json.dumps(with_meta(data, tool="link_targets_audit", params={
        "url": redact_observation_url(url), "max_targets": max_targets, "max_requests": max_requests}))
