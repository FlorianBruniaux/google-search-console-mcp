import json
import os

import httpx

from gsc_mcp.meta import with_meta

_CRUX_BASE = "https://chromeuxreport.googleapis.com/v1/records"

_LCP_SUBPART_METRICS = [
    "largest_contentful_paint_image_time_to_first_byte",
    "largest_contentful_paint_image_resource_load_delay",
    "largest_contentful_paint_image_resource_load_duration",
    "largest_contentful_paint_image_element_render_delay",
]

_LCP_SUBPART_KEY_MAP = {
    "largest_contentful_paint_image_time_to_first_byte": "ttfb_ms",
    "largest_contentful_paint_image_resource_load_delay": "resource_load_delay_ms",
    "largest_contentful_paint_image_resource_load_duration": "resource_load_duration_ms",
    "largest_contentful_paint_image_element_render_delay": "render_delay_ms",
}

_LCP_SUBPART_PHASE_MAP = {
    "ttfb_ms": "ttfb",
    "resource_load_delay_ms": "resource_load_delay",
    "resource_load_duration_ms": "resource_load_duration",
    "render_delay_ms": "render_delay",
}

_THRESHOLDS = {
    "largest_contentful_paint":        (2500, 4000),
    "interaction_to_next_paint":       (200, 500),
    "cumulative_layout_shift":         (0.1, 0.25),
    "first_contentful_paint":          (1800, 3000),
    "experimental_time_to_first_byte": (800, 1800),
}


def _crux_api_key() -> str:
    key = os.environ.get("CRUX_API_KEY", "").strip()
    if not key:
        raise RuntimeError(
            "CRUX_API_KEY environment variable is not set. "
            "Get a key at https://console.cloud.google.com/apis/credentials "
            "and enable the Chrome UX Report API."
        )
    return key


def _rate(metric_key: str, p75) -> str:
    if p75 is None:
        return "unknown"
    good, poor = _THRESHOLDS.get(metric_key, (0, 0))
    if p75 <= good:
        return "good"
    if p75 <= poor:
        return "needs_improvement"
    return "poor"


def crux_page_vitals(url: str, form_factor: str = "ALL_FORM_FACTORS") -> str:
    """Fetch current Core Web Vitals (LCP, INP, CLS, FCP, TTFB) for a URL from the CrUX API.

    form_factor: "ALL_FORM_FACTORS" | "PHONE" | "DESKTOP" | "TABLET"
    Returns p75 percentile and a good/needs_improvement/poor rating per metric.
    If the URL has insufficient data (<1000 real users over 28 days), returns verdict=not_enough_data.
    Requires CRUX_API_KEY environment variable (Google API key with Chrome UX Report API enabled).
    """
    payload: dict = {
        "url": url,
        "metrics": [
            "largest_contentful_paint",
            "interaction_to_next_paint",
            "cumulative_layout_shift",
            "first_contentful_paint",
            "experimental_time_to_first_byte",
        ],
    }
    if form_factor != "ALL_FORM_FACTORS":
        payload["formFactor"] = form_factor

    with httpx.Client(timeout=15) as client:
        resp = client.post(
            f"{_CRUX_BASE}:queryRecord",
            params={"key": _crux_api_key()},
            json=payload,
        )

    if resp.status_code == 404:
        return json.dumps(with_meta(
            {
                "url": url,
                "form_factor": form_factor,
                "verdict": "not_enough_data",
                "note": "URL not in CrUX dataset (requires 1000+ real users over 28 days).",
            },
            tool="crux_page_vitals",
            params={"url": url, "form_factor": form_factor},
        ))

    resp.raise_for_status()
    metrics_raw = resp.json().get("record", {}).get("metrics", {})

    metrics = {
        key: {
            "p75": val.get("percentiles", {}).get("p75"),
            "rating": _rate(key, val.get("percentiles", {}).get("p75")),
        }
        for key, val in metrics_raw.items()
    }

    return json.dumps(with_meta(
        {"url": url, "form_factor": form_factor, "metrics": metrics},
        tool="crux_page_vitals",
        params={"url": url, "form_factor": form_factor},
    ))


def crux_history(
    url: str,
    form_factor: str = "ALL_FORM_FACTORS",
    metric: str = "largest_contentful_paint",
) -> str:
    """Fetch 40 weeks of Core Web Vitals history for a URL from the CrUX History API.

    form_factor: "ALL_FORM_FACTORS" | "PHONE" | "DESKTOP" | "TABLET"
    metric: one of largest_contentful_paint | interaction_to_next_paint |
            cumulative_layout_shift | first_contentful_paint | experimental_time_to_first_byte
    Returns p75 per weekly collection period, oldest to newest.
    Requires CRUX_API_KEY environment variable.
    """
    payload: dict = {"url": url, "metrics": [metric]}
    if form_factor != "ALL_FORM_FACTORS":
        payload["formFactor"] = form_factor

    with httpx.Client(timeout=15) as client:
        resp = client.post(
            f"{_CRUX_BASE}:queryHistoryRecord",
            params={"key": _crux_api_key()},
            json=payload,
        )

    if resp.status_code == 404:
        return json.dumps(with_meta(
            {"url": url, "form_factor": form_factor, "metric": metric, "verdict": "not_enough_data"},
            tool="crux_history",
            params={"url": url, "form_factor": form_factor, "metric": metric},
        ))

    resp.raise_for_status()
    record = resp.json().get("record", {})
    periods = record.get("collectionPeriods", [])
    p75s = record.get("metrics", {}).get(metric, {}).get("percentilesTimeseries", {}).get("p75s", [])

    history = [
        {"week_start": p["firstDate"], "week_end": p["lastDate"], "p75": v}
        for p, v in zip(periods, p75s)
    ]

    return json.dumps(with_meta(
        {"url": url, "form_factor": form_factor, "metric": metric, "weeks": len(history), "history": history},
        tool="crux_history",
        params={"url": url, "form_factor": form_factor, "metric": metric},
    ))


def crux_lcp_subparts(url: str, form_factor: str = "PHONE") -> str:
    """Decompose LCP into its four subparts via the CrUX API for actionable performance diagnosis.

    Returns p75 values for TTFB, resource load delay, resource load duration, and element
    render delay, plus the dominant phase (the subpart with the highest p75 ms). Knowing
    which phase dominates turns "LCP is 4.2s" into a specific fix (server, preload, image
    size, or render-blocking resources).

    form_factor: "PHONE" (default) | "DESKTOP" | "TABLET" | "ALL_FORM_FACTORS"
    Requires CRUX_API_KEY environment variable.
    Verdicts: good | needs_improvement | poor | not_enough_data | missing_key | fetch_error.
    Adapted from claude-seo lcp_subparts.py (agricidaniel, MIT).
    """
    api_key = os.environ.get("CRUX_API_KEY", "").strip()
    if not api_key:
        return json.dumps(with_meta(
            {"url": url, "form_factor": form_factor, "verdict": "missing_key"},
            tool="crux_lcp_subparts",
            params={"url": url, "form_factor": form_factor},
        ))

    payload: dict = {
        "url": url,
        "metrics": _LCP_SUBPART_METRICS + ["largest_contentful_paint"],
    }
    if form_factor != "ALL_FORM_FACTORS":
        payload["formFactor"] = form_factor

    with httpx.Client(timeout=15) as client:
        resp = client.post(
            f"{_CRUX_BASE}:queryRecord",
            params={"key": api_key},
            json=payload,
        )

    if resp.status_code == 404:
        return json.dumps(with_meta(
            {
                "url": url,
                "form_factor": form_factor,
                "verdict": "not_enough_data",
                "note": "URL not in CrUX dataset (requires 1000+ real users over 28 days).",
            },
            tool="crux_lcp_subparts",
            params={"url": url, "form_factor": form_factor},
        ))

    resp.raise_for_status()
    metrics_raw = resp.json().get("record", {}).get("metrics", {})

    def _p75(key: str):
        m = metrics_raw.get(key)
        if not m:
            return None
        val = m.get("percentiles", {}).get("p75")
        if val is None:
            return None
        try:
            return float(val)
        except (TypeError, ValueError):
            return None

    lcp_p75 = _p75("largest_contentful_paint")
    lcp_rating = _rate("largest_contentful_paint", lcp_p75)

    subpart_values: dict[str, float | None] = {
        _LCP_SUBPART_KEY_MAP[k]: _p75(k)
        for k in _LCP_SUBPART_METRICS
    }

    # Dominant phase: short key name of the subpart with the highest p75 value
    valid_subparts = {k: v for k, v in subpart_values.items() if v is not None}
    if valid_subparts:
        dominant_key = max(valid_subparts, key=lambda k: valid_subparts[k])  # type: ignore[arg-type]
        dominant_phase = _LCP_SUBPART_PHASE_MAP.get(dominant_key)
    else:
        dominant_phase = None

    subparts = {**subpart_values, "dominant_phase": dominant_phase}

    # Verdict matches LCP rating when data is present
    if lcp_p75 is None:
        verdict = "not_enough_data"
    elif lcp_rating == "good":
        verdict = "good"
    elif lcp_rating == "needs_improvement":
        verdict = "needs_improvement"
    else:
        verdict = "poor"

    return json.dumps(with_meta(
        {
            "url": url,
            "form_factor": form_factor,
            "lcp_p75_ms": lcp_p75,
            "lcp_rating": lcp_rating,
            "subparts": subparts,
            "verdict": verdict,
        },
        tool="crux_lcp_subparts",
        params={"url": url, "form_factor": form_factor},
    ))
