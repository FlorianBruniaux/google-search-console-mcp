import json
from gsc_mcp.auth import get_gsc_service
from gsc_mcp.meta import with_meta
from gsc_mcp.constants import CTR_BENCHMARKS
from gsc_mcp.tools.analytics import _fetch_rows, _date_range, _MAX_ROWS_PER_PAGE

_WIN_MIN_POSITION = 4.0
_WIN_MAX_POSITION = 15.0
_WIN_MIN_IMPRESSIONS = 10


def _benchmark_ctr(position: float) -> float:
    pos_int = max(1, min(15, round(position)))
    for b in CTR_BENCHMARKS:
        if b["position"] == pos_int:
            return b["ctr"]
    return CTR_BENCHMARKS[-1]["ctr"]


def quick_wins(site: str, days: int = 28, min_impressions: int = _WIN_MIN_IMPRESSIONS) -> str:
    start, end = _date_range(days)
    svc = get_gsc_service()
    body = {
        "startDate": start,
        "endDate": end,
        "dimensions": ["page", "query"],
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
        expected_clicks = round(bench * imp)
        opportunity_score = round((bench - actual_ctr) * imp)
        opportunities.append({
            "page": r.get("page"),
            "query": r.get("query"),
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
    svc = get_gsc_service()

    from datetime import date, timedelta
    end_b = date.today()
    start_b = end_b - timedelta(days=days - 1)
    end_a = start_b - timedelta(days=1)
    start_a = end_a - timedelta(days=days - 1)

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


def check_alerts(site: str, days: int = 28) -> str:
    start, end = _date_range(days)
    svc = get_gsc_service()
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
