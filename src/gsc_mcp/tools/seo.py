import json
import re
from datetime import date, timedelta
from urllib.parse import urlparse

from gsc_mcp.auth import get_searchconsole_service
from gsc_mcp.meta import with_meta
from gsc_mcp.constants import CTR_BENCHMARKS
from gsc_mcp.tools.analytics import _fetch_rows, _date_range, _MAX_ROWS_PER_PAGE

_WIN_MIN_POSITION = 4.0
_WIN_MAX_POSITION = 15.0
_WIN_MIN_IMPRESSIONS = 10

_STRIKING_MIN_POSITION = 8.0
_STRIKING_MAX_POSITION = 15.0
_CANNIBAL_MIN_CONFLICT = 0.1


def _two_periods(days: int):
    """Return (start_a, end_a, start_b, end_b) for two consecutive equal-length windows ending today."""
    end_b = date.today()
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


def quick_wins(site: str, days: int = 28, min_impressions: int = _WIN_MIN_IMPRESSIONS) -> str:
    """Identify pages ranking between positions 4-15 whose CTR is below the industry benchmark for their rank.

    Sorted by opportunity_score = (benchmark_ctr - actual_ctr) * impressions. High scores mean
    large click gains are possible with CTR optimisation (title/meta improvements).
    """
    start, end = _date_range(days)
    svc = get_searchconsole_service()
    body = {
        "startDate": start,
        "endDate": end,
        "dimensions": ["page"],
        "rowLimit": _MAX_ROWS_PER_PAGE,
    }
    raw = _fetch_rows(svc, site, body)

    opportunities = []
    for r in raw:
        pos = r.get("position", 0.0)
        imp = r.get("impressions", 0)
        if not (_WIN_MIN_POSITION <= pos <= _WIN_MAX_POSITION and imp >= min_impressions):
            continue
        bench = _benchmark_ctr(pos)
        actual_ctr = r.get("ctr", 0.0)
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

    return json.dumps(with_meta(
        {"site": site, "date_range": {"start": start, "end": end}, "opportunities": opportunities},
        tool="quick_wins",
        params={"site": site, "days": days, "min_impressions": min_impressions},
    ))


def traffic_drops(site: str, days: int = 28) -> str:
    """Find queries whose clicks dropped compared to the previous equally-sized period.

    Each result includes a diagnosis: 'ranking_loss' (position degraded by more than 2),
    'ctr_collapse' (CTR fell more than 30%), or 'demand_decline' (impressions also fell).
    Note: uses date.today() without a GSC reporting lag, so the most recent 2-3 days may be incomplete.
    """
    svc = get_searchconsole_service()
    start_a, end_a, start_b, end_b = _two_periods(days)

    def fetch(start, end):
        body = {
            "startDate": start.isoformat(),
            "endDate": end.isoformat(),
            "dimensions": ["query"],
            "rowLimit": _MAX_ROWS_PER_PAGE,
        }
        rows = _fetch_rows(svc, site, body)
        return {r.get("query", ""): r for r in rows}

    prev = fetch(start_a, end_a)
    curr = fetch(start_b, end_b)

    drops = []
    for query, curr_row in curr.items():
        prev_row = prev.get(query)
        if not prev_row:
            continue
        click_delta = curr_row["clicks"] - prev_row["clicks"]
        if click_delta >= 0:
            continue

        if curr_row["position"] > prev_row["position"] + 2:
            diagnosis = "ranking_loss"
        elif curr_row["ctr"] < prev_row["ctr"] * 0.7:
            diagnosis = "ctr_collapse"
        else:
            diagnosis = "demand_decline"

        drops.append({
            "query": query,
            "clicks_delta": click_delta,
            "impressions_delta": curr_row["impressions"] - prev_row["impressions"],
            "position_current": curr_row["position"],
            "position_previous": prev_row["position"],
            "diagnosis": diagnosis,
        })

    drops.sort(key=lambda x: x["clicks_delta"])

    return json.dumps(with_meta(
        {
            "site": site,
            "period_a": {"start": start_a.isoformat(), "end": end_a.isoformat()},
            "period_b": {"start": start_b.isoformat(), "end": end_b.isoformat()},
            "drops": drops,
        },
        tool="traffic_drops",
        params={"site": site, "days": days},
    ))


def seo_striking_distance(site: str, days: int = 28, min_impressions: int = 0) -> str:
    """List queries ranking between positions 8-15, sorted by impressions descending.

    These are the best candidates for ranking improvement: close enough to page 1 that
    targeted content or link optimisation can move them into top positions.
    """
    start, end = _date_range(days)
    svc = get_searchconsole_service()
    body = {
        "startDate": start,
        "endDate": end,
        "dimensions": ["query"],
        "rowLimit": _MAX_ROWS_PER_PAGE,
    }
    raw = _fetch_rows(svc, site, body)

    candidates = []
    for r in raw:
        pos = r.get("position", 0.0)
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

    return json.dumps(with_meta(
        {"site": site, "date_range": {"start": start, "end": end}, "queries": candidates},
        tool="seo_striking_distance",
        params={"site": site, "days": days, "min_impressions": min_impressions},
    ))


def seo_cannibalization(site: str, days: int = 28, min_impressions: int = 50) -> str:
    """Detect queries where multiple pages compete for the same ranking slot.

    Uses the Herfindahl-Hirschman Index (HHI) to measure click concentration across pages.
    conflict_score = 1 - HHI: values near 1 mean clicks are split evenly across pages (high competition).
    Filters to queries with at least min_impressions total impressions to exclude noise.
    """
    start, end = _date_range(days)
    svc = get_searchconsole_service()
    body = {
        "startDate": start,
        "endDate": end,
        "dimensions": ["query", "page"],
        "rowLimit": _MAX_ROWS_PER_PAGE,
    }
    raw = _fetch_rows(svc, site, body)

    groups: dict[str, list[dict]] = {}
    for r in raw:
        query = r.get("query")
        if query is None:
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
        {"site": site, "date_range": {"start": start, "end": end}, "conflicts": conflicts},
        tool="seo_cannibalization",
        params={"site": site, "days": days, "min_impressions": min_impressions},
    ))


def seo_lost_queries(site: str, days: int = 28) -> str:
    """Find queries that had significant clicks previously but now have 80%+ fewer clicks.

    Only queries with at least 5 clicks in the previous period are included to filter noise.
    Note: uses date.today() without a GSC reporting lag, so the most recent 2-3 days of the
    current period may include incomplete data and produce false positives.
    """
    svc = get_searchconsole_service()
    start_a, end_a, start_b, end_b = _two_periods(days)

    def fetch(start, end):
        body = {
            "startDate": start.isoformat(),
            "endDate": end.isoformat(),
            "dimensions": ["query"],
            "rowLimit": _MAX_ROWS_PER_PAGE,
        }
        rows = _fetch_rows(svc, site, body)
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


def check_alerts(site: str, days: int = 28) -> str:
    """Scan for structural SEO risks: traffic concentration and high-impression low-rank pages.

    Flags 'traffic_concentration' (severity: high) when a single query drives more than 50% of
    all clicks (fragility indicator) and 'high_impression_low_rank' (severity: medium) when a
    page gets more than 5000 impressions at position > 10 (content optimisation opportunity).
    """
    start, end = _date_range(days)
    svc = get_searchconsole_service()
    body = {
        "startDate": start,
        "endDate": end,
        "dimensions": ["page", "query"],
        "rowLimit": _MAX_ROWS_PER_PAGE,
    }
    rows = _fetch_rows(svc, site, body)

    alerts = []
    total_clicks = sum(r["clicks"] for r in rows)

    for r in rows:
        share = r["clicks"] / total_clicks if total_clicks else 0
        if share > 0.5:
            alerts.append({
                "type": "traffic_concentration",
                "severity": "high",
                "page": r.get("page"),
                "query": r.get("query"),
                "message": f"Single query drives {share:.0%} of all clicks — single point of failure.",
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
