"""Dated exact GA4 source rules; product domains alone are not referral evidence."""

import math
from datetime import date


MATCHING_RULES = {
    "verified_on": "2026-10-08",
    "matching": "Exact source after whitespace trimming and lowercasing; no substring or subdomain matches.",
    "confirmed": {
        "chatgpt.com": {
            "assistant": "ChatGPT",
            "reason": "OpenAI documents utm_source=chatgpt.com on ChatGPT search referral URLs.",
            "documentation": "https://help.openai.com/en/articles/12627856-publishers-and-developers-faq",
        },
    },
    "candidates": {
        "perplexity.ai": "Perplexity", "claude.ai": "Claude", "gemini.google.com": "Gemini",
        "copilot.microsoft.com": "Copilot",
    },
    "candidate_reason": "Product-domain candidates; their GA4 source patterns are unverified and excluded from confirmed totals.",
}


def validate_window(start: str, end: str) -> None:
    """Concrete inclusive ISO dates are required before credentials are accessed."""
    try:
        valid = (date.fromisoformat(start).isoformat() == start
                 and date.fromisoformat(end).isoformat() == end and start <= end)
    except (TypeError, ValueError):
        valid = False
    if not valid:
        raise ValueError("start_date and end_date must be ordered YYYY-MM-DD dates")


def parse_row(row) -> dict:
    """Reject absent/malformed measurements instead of coercing them to zero."""
    if len(row.dimension_values) != 3 or len(row.metric_values) != 3:
        raise ValueError("Unexpected GA4 row shape")
    source, medium, landing = [value.value for value in row.dimension_values]
    sessions, engaged = [int(value.value) for value in row.metric_values[:2]]
    events = float(row.metric_values[2].value)
    if sessions < 0 or engaged < 0 or events < 0 or not math.isfinite(events):
        raise ValueError("Invalid GA4 measurement")
    normalized = source.strip().lower()
    rule = MATCHING_RULES["confirmed"].get(normalized)
    candidate = MATCHING_RULES["candidates"].get(normalized)
    return {
        "source": source, "medium": medium, "landing_page": landing,
        "sessions": sessions, "engaged_sessions": engaged, "key_events": events, "conversions": events,
        "classification": "confirmed" if rule else "candidate" if candidate else "unmatched",
        "assistant": rule["assistant"] if rule else candidate,
        "match_reason": rule["reason"] if rule else MATCHING_RULES["candidate_reason"] if candidate else "No exact allowlist rule matched.",
    }


def totals(rows: list[dict]) -> dict:
    return {metric: sum(row[metric] for row in rows)
            for metric in ("sessions", "engaged_sessions", "key_events", "conversions")}


def assistant_breakdown(rows: list[dict]) -> list[dict]:
    """Group only confirmed observations and retain per-landing-page breakdowns."""
    groups = {}
    for row in rows:
        group = groups.setdefault(row["assistant"], {**totals([]), "landing_pages": {}})
        landing = group["landing_pages"].setdefault(row["landing_page"], totals([]))
        for metric in ("sessions", "engaged_sessions", "key_events", "conversions"):
            group[metric] += row[metric]
            landing[metric] += row[metric]
    return [
        {"assistant": assistant, **{metric: group[metric] for metric in ("sessions", "engaged_sessions", "key_events", "conversions")},
         "landing_pages": [{"landing_page": page, **values} for page, values in sorted(group["landing_pages"].items())]}
        for assistant, group in sorted(groups.items())
    ]
