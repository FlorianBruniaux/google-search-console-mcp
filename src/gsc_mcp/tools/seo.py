import json
import re
from datetime import date, timedelta
from urllib.parse import urlparse

from gsc_mcp.auth import get_searchconsole_service
from gsc_mcp.meta import with_meta
from gsc_mcp.constants import CTR_BENCHMARKS
from gsc_mcp.providers import get_search_provider
from gsc_mcp.providers.base import SearchMetricBatch
from gsc_mcp.tools.analytics import _fetch_rows, _date_range

_WIN_MIN_POSITION = 4.0
_WIN_MAX_POSITION = 15.0
_WIN_MIN_IMPRESSIONS = 10

_STRIKING_MIN_POSITION = 8.0
_STRIKING_MAX_POSITION = 15.0
_CANNIBAL_MIN_CONFLICT = 0.1
_SEARCH_OPERATOR_QUERY = re.compile(
    r"(?:^|\s)-?(?:site|intitle|inurl|filetype):\S+", re.IGNORECASE
)


def _validate_engine(engine: str) -> None:
    if engine not in ("google", "bing"):
        raise ValueError("engine must be one of: google, bing")


def _unsupported_bing(tool: str, reason: str, params: dict) -> str:
    return json.dumps(
        with_meta(
            {
                "engine": "bing",
                "verdict": "unsupported",
                "reason": reason,
            },
            tool=tool,
            params={**params, "engine": "bing"},
        )
    )


def _fetch_metric_rows(
    engine: str,
    site: str,
    start: str,
    end: str,
    dimensions: tuple[str, ...],
) -> SearchMetricBatch:
    return get_search_provider(engine).fetch(
        site=site,
        start_date=start,
        end_date=end,
        dimensions=dimensions,
    )


def _rows_as_dicts(batch: SearchMetricBatch) -> list[dict]:
    return [
        {
            "date": row.date,
            "query": row.query,
            "page": row.page,
            "clicks": row.clicks,
            "impressions": row.impressions,
            "ctr": row.ctr,
            "position": row.position,
        }
        for row in batch.rows
    ]


def _two_periods(days: int, lag: int = 0):
    """Return two adjacent equal-length windows ending lag days before today."""
    end_b = date.today() - timedelta(days=lag)
    start_b = end_b - timedelta(days=days - 1)
    end_a = start_b - timedelta(days=1)
    start_a = end_a - timedelta(days=days - 1)
    return start_a, end_a, start_b, end_b


def _benchmark_ctr(position: float) -> float:
    pos_int = max(1, min(15, round(position)))
    for b in CTR_BENCHMARKS:
        if b["position"] == pos_int:
            return b["ctr"]
    return CTR_BENCHMARKS[-1]["ctr"]


def quick_wins(
    site: str,
    days: int = 28,
    min_impressions: int = _WIN_MIN_IMPRESSIONS,
    engine: str = "google",
) -> str:
    """Identify pages ranking between positions 4-15 whose CTR is below the industry benchmark for their rank.

    Sorted by opportunity_score = (benchmark_ctr - actual_ctr) * impressions. High scores mean
    large click gains are possible with CTR optimisation (title/meta improvements).
    Unavailable CTRs are skipped; Bing reports the count in skipped_metric_rows.
    """
    _validate_engine(engine)
    start, end = _date_range(days)
    raw = _rows_as_dicts(
        _fetch_metric_rows(engine, site, start, end, ("page",))
    )

    opportunities = []
    unavailable_ctr_count = 0
    for r in raw:
        pos = r.get("position", 0.0)
        if pos is None:
            continue
        imp = r.get("impressions", 0)
        if not (_WIN_MIN_POSITION <= pos <= _WIN_MAX_POSITION and imp >= min_impressions):
            continue
        bench = _benchmark_ctr(pos)
        actual_ctr = r.get("ctr")
        if actual_ctr is None:
            unavailable_ctr_count += 1
            continue
        if actual_ctr >= bench:
            continue
        expected_clicks = round(bench * imp)
        opportunity_score = round((bench - actual_ctr) * imp)
        opportunities.append({
            "page": r.get("page"),
            "position": pos,
            "clicks": r.get("clicks", 0),
            "impressions": imp,
            "ctr": actual_ctr,
            "benchmark_ctr": bench,
            "expected_clicks_at_benchmark": expected_clicks,
            "opportunity_score": opportunity_score,
        })

    opportunities.sort(key=lambda x: x["opportunity_score"], reverse=True)

    data = {
        "site": site,
        "date_range": {"start": start, "end": end},
        "opportunities": opportunities,
    }
    params = {"site": site, "days": days, "min_impressions": min_impressions}
    if engine == "bing":
        data["engine"] = "bing"
        data["skipped_metric_rows"] = {"ctr_unavailable": unavailable_ctr_count}
        params["engine"] = "bing"

    return json.dumps(with_meta(
        data,
        tool="quick_wins",
        params=params,
    ))


def traffic_drops(site: str, days: int = 28, engine: str = "google") -> str:
    """Find queries whose clicks dropped compared to the previous equally-sized period.

    Windows exclude the most recent 3 days for the GSC reporting lag. Diagnoses are
    metric-rule candidates, not established causes: 'ranking_loss' (position worsened
    by more than 2), 'ctr_collapse' (CTR fell more than 30%), or 'demand_decline'
    (impressions fell). Multiple candidates can match; 'unknown' means insufficient
    evidence. A query missing from current rows is unavailable, not observed zero.
    """
    _validate_engine(engine)
    if engine == "bing":
        return _unsupported_bing(
            "traffic_drops",
            "bing_exact_period_comparison_unavailable",
            {"site": site, "days": days},
        )

    start_a, end_a, start_b, end_b = _two_periods(days, lag=3)

    def fetch(start, end):
        rows = _rows_as_dicts(
            _fetch_metric_rows(
                engine,
                site,
                start.isoformat(),
                end.isoformat(),
                ("query",),
            )
        )
        return {r.get("query", ""): r for r in rows}

    prev = fetch(start_a, end_a)
    curr = fetch(start_b, end_b)

    def metrics(row):
        if row is None:
            return None
        has_impressions = row["impressions"] > 0
        return {
            "clicks": row["clicks"],
            "impressions": row["impressions"],
            "ctr": row["ctr"] if has_impressions else None,
            "position": row["position"] if has_impressions else None,
        }

    unavailable = [
        {
            "query": query,
            "diagnosis": "unknown",
            "diagnosis_status": "insufficient_evidence",
            "diagnosis_candidates": [],
            "reason": "current_query_not_returned",
            "metrics_previous": metrics(prev_row),
            "metrics_current": None,
        }
        for query, prev_row in prev.items()
        if query not in curr
    ]
    drops = []
    for query, curr_row in curr.items():
        prev_row = prev.get(query)
        if not prev_row:
            continue
        click_delta = curr_row["clicks"] - prev_row["clicks"]
        if click_delta >= 0:
            continue

        previous_metrics = metrics(prev_row)
        current_metrics = metrics(curr_row)
        candidates = []
        # No impressions means there is no CTR or ranking evidence to compare.
        if prev_row["impressions"] > 0 and curr_row["impressions"] > 0:
            previous_position = previous_metrics["position"]
            current_position = current_metrics["position"]
            if (previous_position is not None and current_position is not None
                    and current_position > previous_position + 2):
                candidates.append("ranking_loss")
            if curr_row["ctr"] < prev_row["ctr"] * 0.7:
                candidates.append("ctr_collapse")
            if curr_row["impressions"] < prev_row["impressions"]:
                candidates.append("demand_decline")

        drops.append({
            "query": query,
            "clicks_delta": click_delta,
            "impressions_delta": curr_row["impressions"] - prev_row["impressions"],
            "position_current": current_metrics["position"],
            "position_previous": previous_metrics["position"],
            "diagnosis": candidates[0] if candidates else "unknown",
            "diagnosis_status": "candidate" if candidates else "insufficient_evidence",
            "diagnosis_candidates": candidates,
            "metrics_previous": previous_metrics,
            "metrics_current": current_metrics,
        })

    drops.sort(key=lambda x: x["clicks_delta"])

    return json.dumps(with_meta(
        {
            "site": site,
            "period_a": {"start": start_a.isoformat(), "end": end_a.isoformat()},
            "period_b": {"start": start_b.isoformat(), "end": end_b.isoformat()},
            "drops": drops,
            "unavailable_queries": unavailable,
            "diagnosis_note": "Metric-rule candidates do not establish causes. Missing query rows do not establish zero traffic.",
        },
        tool="traffic_drops",
        params={"site": site, "days": days},
    ))


def seo_striking_distance(
    site: str,
    days: int = 28,
    min_impressions: int = 0,
    engine: str = "google",
) -> str:
    """List queries ranking between positions 8-15, sorted by impressions descending.

    These are the best candidates for ranking improvement: close enough to page 1 that
    targeted content or link optimisation can move them into top positions.
    """
    _validate_engine(engine)
    start, end = _date_range(days)
    raw = _rows_as_dicts(
        _fetch_metric_rows(engine, site, start, end, ("query",))
    )

    candidates = []
    for r in raw:
        pos = r.get("position", 0.0)
        if pos is None:
            continue
        imp = r.get("impressions", 0)
        if not (_STRIKING_MIN_POSITION <= pos <= _STRIKING_MAX_POSITION and imp >= min_impressions):
            continue
        candidates.append({
            "query": r.get("query"),
            "position": pos,
            "clicks": r.get("clicks", 0),
            "impressions": imp,
            "ctr": r.get("ctr", 0.0),
        })

    candidates.sort(key=lambda x: x["impressions"], reverse=True)

    data = {
        "site": site,
        "date_range": {"start": start, "end": end},
        "queries": candidates,
    }
    params = {"site": site, "days": days, "min_impressions": min_impressions}
    if engine == "bing":
        data["engine"] = "bing"
        params["engine"] = "bing"

    return json.dumps(with_meta(
        data,
        tool="seo_striking_distance",
        params=params,
    ))


def seo_cannibalization(
    site: str,
    days: int = 28,
    min_impressions: int = 50,
    engine: str = "google",
    include_search_operators: bool = False,
) -> str:
    """Detect queries where multiple pages compete for the same ranking slot.

    Uses the Herfindahl-Hirschman Index (HHI) to measure click concentration across pages.
    conflict_score = 1 - HHI: values near 1 mean clicks are split evenly across pages (high competition).
    Filters to queries with at least min_impressions total impressions to exclude noise.
    Excludes queries containing site:, intitle:, inurl: or filetype: tokens by default,
    counting distinct excluded queries in excluded_search_operator_queries. Pass
    include_search_operators=True to include them. These signals are candidates for
    review; shared queries and split clicks alone do not prove harmful competition.
    """
    _validate_engine(engine)
    if engine == "bing":
        return _unsupported_bing(
            "seo_cannibalization",
            "bing_bulk_page_query_dimension_unavailable",
            {
                "site": site,
                "days": days,
                "min_impressions": min_impressions,
                "include_search_operators": include_search_operators,
            },
        )

    start, end = _date_range(days)
    raw = _rows_as_dicts(
        _fetch_metric_rows(engine, site, start, end, ("query", "page"))
    )

    groups: dict[str, list[dict]] = {}
    excluded_queries = set()
    for r in raw:
        query = r.get("query")
        if query is None:
            continue
        if not include_search_operators and _SEARCH_OPERATOR_QUERY.search(query):
            excluded_queries.add(query)
            continue
        groups.setdefault(query, []).append(r)

    conflicts = []
    for query, page_rows in groups.items():
        if len(page_rows) < 2:
            continue

        total_clicks = sum(p.get("clicks", 0) for p in page_rows)
        total_impressions = sum(p.get("impressions", 0) for p in page_rows)
        if total_impressions < min_impressions:
            continue

        n = len(page_rows)
        if total_clicks > 0:
            hhi = sum((p.get("clicks", 0) / total_clicks) ** 2 for p in page_rows)
        else:
            hhi = 1.0 / n  # uniform share fallback when no clicks to weight by

        conflict_score = 1.0 - hhi
        if conflict_score <= _CANNIBAL_MIN_CONFLICT:
            continue

        pages = sorted(
            [
                {
                    "page": p.get("page"),
                    "clicks": p.get("clicks", 0),
                    "impressions": p.get("impressions", 0),
                    "position": p.get("position", 0.0),
                }
                for p in page_rows
            ],
            key=lambda x: x["clicks"],
            reverse=True,
        )

        conflicts.append({
            "query": query,
            "conflict_score": round(conflict_score, 4),
            "total_clicks": total_clicks,
            "total_impressions": total_impressions,
            "pages": pages,
        })

    conflicts.sort(key=lambda x: x["conflict_score"], reverse=True)

    return json.dumps(with_meta(
        {
            "site": site,
            "date_range": {"start": start, "end": end},
            "conflicts": conflicts,
            "excluded_search_operator_queries": len(excluded_queries),
        },
        tool="seo_cannibalization",
        params={
            "site": site,
            "days": days,
            "min_impressions": min_impressions,
            "include_search_operators": include_search_operators,
        },
    ))


def seo_lost_queries(site: str, days: int = 28, engine: str = "google") -> str:
    """Find queries that had significant clicks previously but now have 80%+ fewer clicks.

    Only queries with at least 5 clicks in the previous period are included to filter noise.
    Note: uses date.today() without a GSC reporting lag, so the most recent 2-3 days of the
    current period may include incomplete data and produce false positives.
    """
    _validate_engine(engine)
    if engine == "bing":
        return _unsupported_bing(
            "seo_lost_queries",
            "bing_exact_period_comparison_unavailable",
            {"site": site, "days": days},
        )

    start_a, end_a, start_b, end_b = _two_periods(days)

    def fetch(start, end):
        rows = _rows_as_dicts(
            _fetch_metric_rows(
                engine,
                site,
                start.isoformat(),
                end.isoformat(),
                ("query",),
            )
        )
        return {r.get("query", ""): r for r in rows}

    prev = fetch(start_a, end_a)
    curr = fetch(start_b, end_b)

    lost = []
    for query, prev_row in prev.items():
        prev_clicks = prev_row["clicks"]
        if prev_clicks < 5:
            continue  # guard: avoids division by zero and low-signal noise
        curr_row = curr.get(query)
        curr_clicks = curr_row["clicks"] if curr_row else 0
        drop_pct = (prev_clicks - curr_clicks) / prev_clicks
        if drop_pct < 0.80:
            continue
        lost.append({
            "query": query,
            "clicks_previous": prev_clicks,
            "clicks_current": curr_clicks,
            "drop_pct": round(drop_pct, 4),
        })

    lost.sort(key=lambda x: (x["drop_pct"], x["clicks_previous"]), reverse=True)

    return json.dumps(with_meta(
        {
            "site": site,
            "period_a": {"start": start_a.isoformat(), "end": end_a.isoformat()},
            "period_b": {"start": start_b.isoformat(), "end": end_b.isoformat()},
            "lost_queries": lost,
        },
        tool="seo_lost_queries",
        params={"site": site, "days": days},
    ))


def check_alerts(site: str, days: int = 28, engine: str = "google") -> str:
    """Scan for structural SEO risks: traffic concentration and high-impression low-rank pages.

    Flags 'traffic_concentration' (severity: high) when a single query drives more than 50% of
    all clicks (fragility indicator) and 'high_impression_low_rank' (severity: medium) when a
    page gets more than 5000 impressions at position > 10 (content optimisation opportunity).
    """
    _validate_engine(engine)
    if engine == "bing":
        return _unsupported_bing(
            "check_alerts",
            "bing_bulk_page_query_dimension_unavailable",
            {"site": site, "days": days},
        )

    start, end = _date_range(days)
    svc = get_searchconsole_service()
    rows = _fetch_rows(
        svc,
        site,
        {
            "startDate": start,
            "endDate": end,
            "dimensions": ["page", "query"],
        },
    )

    alerts = []
    property_rows = _fetch_rows(svc, site, {"startDate": start, "endDate": end})
    total_clicks = sum(r["clicks"] for r in property_rows)

    for r in rows:
        share = r["clicks"] / total_clicks if total_clicks else 0
        if share > 0.5:
            alerts.append({
                "type": "traffic_concentration",
                "severity": "high",
                "page": r.get("page"),
                "query": r.get("query"),
                "message": f"This page/query pair drives {share:.0%} of property clicks.",
            })
        elif r["position"] > 10 and r["impressions"] > 5000:
            alerts.append({
                "type": "high_impression_low_rank",
                "severity": "medium",
                "page": r.get("page"),
                "query": r.get("query"),
                "message": f"{r['impressions']} impressions at position {r['position']:.1f} — ranking opportunity.",
            })

    return json.dumps(with_meta(
        {"site": site, "date_range": {"start": start, "end": end}, "alerts": alerts},
        tool="check_alerts",
        params={"site": site, "days": days},
    ))


# ---------------------------------------------------------------------------
# parasite_risk
# ---------------------------------------------------------------------------

# Direct parasite SEO indicators in URL paths (high risk).
# These path segments map directly to Google's 2024-11-19 site-reputation policy.
_PARASITE_HIGH_PATH_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"/sponsored/", "sponsored"),
    (r"/partner/", "partner"),
    (r"/partners/", "partners"),
    (r"/affiliate/", "affiliate"),
    (r"/brand-studio/", "brand-studio"),
    (r"/paid-content/", "paid-content"),
    (r"/native-advertising/", "native-advertising"),
    (r"\b(?:best|top)\b.+\b(?:deals?|products?|picks?|reviews?)\b", "commercial-section"),
)

# Known editorial domain parasite patterns (medium risk).
# Forbes Advisor, CNN Underscored, WSJ Select/Commerce received manual actions Nov 2024.
_PARASITE_MEDIUM_PATH_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"/advisor/", "advisor"),
    (r"/underscored/", "underscored"),
    (r"/select/", "select"),
    (r"/commerce/", "commerce"),
)

# Affiliate query parameter signals (low risk on their own).
_PARASITE_LOW_QUERY_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"(?:^|&)(?:ref|aff|partner)=", "affiliate-param"),
)


def _parasite_check_url(url: str) -> dict:
    """Classify a single URL by parasite SEO risk based on path and query patterns."""
    parsed = urlparse(url)
    path = parsed.path.lower()
    query = (parsed.query or "").lower()

    matched: list[str] = []

    for pattern, name in _PARASITE_HIGH_PATH_PATTERNS:
        if re.search(pattern, path, re.IGNORECASE):
            matched.append(name)

    for pattern, name in _PARASITE_MEDIUM_PATH_PATTERNS:
        if re.search(pattern, path, re.IGNORECASE):
            matched.append(name)

    for pattern, name in _PARASITE_LOW_QUERY_PATTERNS:
        if re.search(pattern, query, re.IGNORECASE):
            matched.append(name)

    # Risk level: highest-tier match wins
    high_names = {name for _, name in _PARASITE_HIGH_PATH_PATTERNS}
    medium_names = {name for _, name in _PARASITE_MEDIUM_PATH_PATTERNS}

    if any(m in high_names for m in matched):
        risk = "high"
    elif any(m in medium_names for m in matched):
        risk = "medium"
    elif matched:
        risk = "low"
    else:
        risk = "none"

    return {"url": url, "risk": risk, "patterns": matched}


def parasite_risk(site: str, urls: list[str]) -> str:
    """Scan URL paths for parasite SEO patterns matching Google's 2024-11-19 site-reputation policy.

    Pure URL analysis, no HTTP fetches. Detects sponsored/affiliate/partner path segments,
    commercial product sections (/best-deals/, /top-picks/), known editorial domain patterns
    (Forbes Advisor /advisor/, CNN Underscored /underscored/, /select/, /commerce/),
    and affiliate query parameters (?ref=, ?aff=, ?partner=).

    site_risk is the maximum risk level across all URLs.
    Verdicts: clean | at_risk | high_risk.
    No Google API calls. No authentication required.
    Adapted from claude-seo parasite_risk.py (agricidaniel, MIT).
    """
    results = [_parasite_check_url(u) for u in urls]

    risk_order = {"high": 3, "medium": 2, "low": 1, "none": 0}
    max_risk = max((r["risk"] for r in results), key=lambda r: risk_order[r], default="none")

    high_risk_count = sum(1 for r in results if r["risk"] == "high")

    if max_risk == "high":
        verdict = "high_risk"
    elif max_risk in ("medium", "low"):
        verdict = "at_risk"
    else:
        verdict = "clean"

    return json.dumps(with_meta(
        {
            "site": site,
            "urls_analysed": len(urls),
            "high_risk_count": high_risk_count,
            "results": results,
            "site_risk": max_risk,
            "verdict": verdict,
        },
        tool="parasite_risk",
        params={"site": site, "url_count": len(urls)},
    ))


# ---------------------------------------------------------------------------
# prune_candidates
# ---------------------------------------------------------------------------

# A page earning clicks is never a pruning candidate, whatever its word count or
# how templated it looks. Off-the-shelf SEO tools routinely advise deleting whole
# sets of working local pages because they read thinner than a nearby article;
# this tool classifies on measured traffic and refuses to make that call.
_PRUNE_IMPRESSION_FLOOR = 10


def prune_candidates(
    site: str,
    days: int = 180,
    max_pages: int = 500,
    engine: str = "google",
) -> str:
    """Classify pages by measured traffic before any pruning decision is taken.

    Buckets every page Search Console reports over `days`:
    - has_traffic: at least one click. Never a candidate. Full stop.
    - impressions_no_clicks: seen in results, never clicked. Review, do not delete.
    - low_impressions: under 10 impressions. Weak signal, needs a human look.
    - zero_impressions: no impressions at all. The only defensible candidates.

    The tool deliberately returns no "delete these" list. It returns evidence, and
    the buckets carry the recommended action. A page absent from this report was
    absent from Search Console too, which is a crawling question, not a pruning one.

    Pair with content_quality and internal_links_audit before acting: a page with
    no impressions and no internal link may be starved rather than worthless.
    """
    _validate_engine(engine)
    start, end = _date_range(days)
    raw = _rows_as_dicts(
        _fetch_metric_rows(engine, site, start, end, ("page",))
    )

    buckets: dict[str, list[dict]] = {
        "has_traffic": [],
        "impressions_no_clicks": [],
        "low_impressions": [],
        "zero_impressions": [],
    }

    # Search providers normalize rows before this classification step.
    for row in raw[:max_pages]:
        page = row.get("page")
        if not page:
            continue
        clicks = row.get("clicks", 0)
        impressions = row.get("impressions", 0)
        position = row.get("position", 0)
        entry = {
            "url": page,
            "clicks": clicks,
            "impressions": impressions,
            "position": round(position, 1) if position is not None else None,
        }
        if clicks > 0:
            entry["action"] = (
                f"keep, measured Bing clicks: {clicks}"
                if engine == "bing"
                else "keep, this page brings traffic"
            )
            buckets["has_traffic"].append(entry)
        elif impressions >= _PRUNE_IMPRESSION_FLOOR:
            entry["action"] = (
                "review intent and title, measured Bing impressions: "
                f"{impressions}; clicks: 0"
                if engine == "bing"
                else "review intent and title, Google shows it but nobody clicks"
            )
            buckets["impressions_no_clicks"].append(entry)
        elif impressions > 0:
            entry["action"] = (
                f"weak signal: {impressions} measured Bing impression(s); "
                "review internal links separately"
                if engine == "bing"
                else "weak signal, check internal links before judging"
            )
            buckets["low_impressions"].append(entry)
        else:
            entry["action"] = (
                "no measured Bing impressions in this window; verify crawl and "
                "indexing separately before any action"
                if engine == "bing"
                else "defensible pruning candidate, confirm indexing first"
            )
            buckets["zero_impressions"].append(entry)

    for name in buckets:
        buckets[name].sort(key=lambda e: (e["clicks"], e["impressions"]), reverse=True)

    counts = {name: len(rows) for name, rows in buckets.items()}
    protected = counts["has_traffic"] + counts["impressions_no_clicks"]

    guard_rail = (
        (
            f"{protected} page(s) have measured Bing clicks or impressions and "
            "are excluded from pruning by construction. Content length and "
            "template similarity are not grounds for deletion when measured "
            "search data disagrees."
        )
        if engine == "bing"
        else (
                f"{protected} page(s) earn clicks or impressions and are excluded from "
                "pruning by construction. Content length and template similarity are not "
                "grounds for deletion when the traffic data disagrees."
        )
    )
    data = {
        "site": site,
        "days": days,
        "pages_analysed": sum(counts.values()),
        "counts": counts,
        "protected_from_pruning": protected,
        "has_traffic": buckets["has_traffic"][:50],
        "impressions_no_clicks": buckets["impressions_no_clicks"][:50],
        "low_impressions": buckets["low_impressions"][:50],
        "zero_impressions": buckets["zero_impressions"][:50],
        "guard_rail": guard_rail,
        "verdict": "candidates_found" if counts["zero_impressions"] else "nothing_to_prune",
    }
    params = {"site": site, "days": days}
    if engine == "bing":
        data["engine"] = "bing"
        params["engine"] = "bing"

    return json.dumps(with_meta(
        data,
        tool="prune_candidates",
        params=params,
    ))
