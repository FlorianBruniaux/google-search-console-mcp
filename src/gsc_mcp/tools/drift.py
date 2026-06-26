"""
SEO drift monitoring tools for gsc-mcp.

Adapted from scripts/drift_baseline.py, scripts/drift_compare.py, and
scripts/drift_history.py in claude-seo
(https://github.com/AgriciDaniel/claude-seo, MIT License).
Original drift methodology: Dan Colta (claude-seo CONTRIBUTORS.md).

Three tools:

drift_baseline(url)
    Capture the current SEO state of a page as a "known good" baseline.
    Stores title, meta tags, canonical, headings, JSON-LD, OG tags, and CWV
    in a local SQLite database.

drift_compare(url, *, baseline_id=None)
    Compare the current page state against the stored baseline and report
    which of the 17 SEO drift rules triggered.

drift_history(url, *, limit=10)
    Return recent comparisons for a URL.

Storage: sqlite3 in platformdirs.user_data_dir("gsc-mcp")/drift/baselines.db
No Google API calls in baseline/compare. CWV comparison is optional (requires
CRUX_API_KEY environment variable).
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from difflib import SequenceMatcher
from html.parser import HTMLParser
from pathlib import Path
from typing import Optional
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import httpx
from platformdirs import user_data_dir

from gsc_mcp.meta import with_meta
from gsc_mcp.url_safety import URLSafetyError, safe_fetch_html

# ---------------------------------------------------------------------------
# Storage paths
# ---------------------------------------------------------------------------

_DRIFT_DIR = Path(user_data_dir("gsc-mcp")) / "drift"
_DB_PATH = _DRIFT_DIR / "baselines.db"

_UTM_PARAMS = {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content"}


# ---------------------------------------------------------------------------
# URL normalization
# ---------------------------------------------------------------------------

def _normalize_url(url: str) -> str:
    """Normalize a URL for consistent baseline matching.

    Lowercase scheme and host, strip default ports, sort query params, strip
    UTM params, strip trailing slash (except bare root).
    """
    parsed = urlparse(url)
    scheme = parsed.scheme.lower()
    hostname = (parsed.hostname or "").lower()

    port = parsed.port
    if (scheme == "http" and port == 80) or (scheme == "https" and port == 443):
        port = None

    netloc = hostname if port is None else f"{hostname}:{port}"

    query_params = parse_qs(parsed.query, keep_blank_values=True)
    filtered = {k: v for k, v in sorted(query_params.items()) if k not in _UTM_PARAMS}
    query = urlencode(filtered, doseq=True)

    path = parsed.path.rstrip("/") or "/"
    return urlunparse((scheme, netloc, path, "", query, ""))


def _url_hash(url: str) -> str:
    """SHA-256 of normalized URL, truncated to 16 hex chars."""
    return hashlib.sha256(_normalize_url(url).encode()).hexdigest()[:16]


def _hash_content(content: str) -> str:
    """Full SHA-256 of a string."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

def _init_db() -> sqlite3.Connection:
    _DRIFT_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS baselines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL,
            url_hash TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            title TEXT,
            meta_description TEXT,
            canonical TEXT,
            robots TEXT,
            h1 TEXT,
            h2_json TEXT,
            h3_json TEXT,
            schema_json TEXT,
            og_json TEXT,
            cwv_json TEXT,
            html_hash TEXT,
            schema_hash TEXT,
            status_code INTEGER
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_url_hash ON baselines(url_hash)")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS comparisons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL,
            url_hash TEXT NOT NULL,
            baseline_id INTEGER NOT NULL,
            timestamp TEXT NOT NULL,
            results_json TEXT NOT NULL,
            critical_count INTEGER DEFAULT 0,
            warning_count INTEGER DEFAULT 0,
            info_count INTEGER DEFAULT 0,
            FOREIGN KEY (baseline_id) REFERENCES baselines(id)
        )
    """)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_comp_url_hash ON comparisons(url_hash)"
    )
    conn.commit()
    return conn


# ---------------------------------------------------------------------------
# HTML page parser (stdlib html.parser only)
# ---------------------------------------------------------------------------

class _DriftPageParser(HTMLParser):
    """Extract drift-relevant fields from a page's HTML."""

    def __init__(self) -> None:
        super().__init__()
        self._in_title = False
        self._in_heading: Optional[str] = None
        self._in_ld = False
        self._title_chunks: list[str] = []
        self._heading_chunks: list[str] = []
        self._ld_chunks: list[str] = []

        self.title: Optional[str] = None
        self.meta_description: Optional[str] = None
        self.meta_robots: Optional[str] = None
        self.canonical: Optional[str] = None
        self.h1: list[str] = []
        self.h2: list[str] = []
        self.h3: list[str] = []
        self.schema: list[dict] = []
        self.open_graph: dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs) -> None:
        attr = dict(attrs)
        tag_lower = tag.lower()

        if tag_lower == "title":
            self._in_title = True
            self._title_chunks = []

        elif tag_lower in ("h1", "h2", "h3"):
            self._in_heading = tag_lower
            self._heading_chunks = []

        elif tag_lower == "script" and attr.get("type") == "application/ld+json":
            self._in_ld = True
            self._ld_chunks = []

        elif tag_lower == "meta":
            name = (attr.get("name") or "").lower()
            prop = (attr.get("property") or "").lower()
            content = attr.get("content", "")

            if name == "description":
                self.meta_description = content
            elif name == "robots":
                self.meta_robots = content
            elif prop.startswith("og:"):
                og_key = prop[3:]  # strip "og:" prefix
                self.open_graph[og_key] = content

        elif tag_lower == "link":
            rel = (attr.get("rel") or "").lower()
            href = attr.get("href", "")
            if rel == "canonical" and href:
                self.canonical = href

    def handle_endtag(self, tag: str) -> None:
        tag_lower = tag.lower()

        if tag_lower == "title" and self._in_title:
            self._in_title = False
            self.title = "".join(self._title_chunks).strip() or None

        elif tag_lower in ("h1", "h2", "h3") and self._in_heading == tag_lower:
            text = "".join(self._heading_chunks).strip()
            if text:
                if tag_lower == "h1":
                    self.h1.append(text)
                elif tag_lower == "h2":
                    self.h2.append(text)
                else:
                    self.h3.append(text)
            self._in_heading = None

        elif tag_lower == "script" and self._in_ld:
            self._in_ld = False
            raw = "".join(self._ld_chunks).strip()
            if raw:
                try:
                    data = json.loads(raw)
                    if isinstance(data, list):
                        self.schema.extend(data)
                    else:
                        self.schema.append(data)
                except json.JSONDecodeError:
                    pass

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self._title_chunks.append(data)
        elif self._in_heading:
            self._heading_chunks.append(data)
        elif self._in_ld:
            self._ld_chunks.append(data)

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "meta_description": self.meta_description,
            "meta_robots": self.meta_robots,
            "canonical": self.canonical,
            "h1": self.h1,
            "h2": self.h2,
            "h3": self.h3,
            "schema": self.schema,
            "open_graph": self.open_graph,
        }


def _parse_html(html: str) -> dict:
    parser = _DriftPageParser()
    parser.feed(html)
    return parser.to_dict()


# ---------------------------------------------------------------------------
# CWV fetching (optional, requires CRUX_API_KEY)
# ---------------------------------------------------------------------------

def _fetch_cwv(url: str) -> Optional[dict]:
    """Fetch CrUX field data for url. Returns dict or None if unavailable."""
    try:
        from gsc_mcp.tools.crux import crux_page_vitals
        raw = crux_page_vitals(url=url)
        data = json.loads(raw)
        if data.get("verdict") == "not_enough_data" or data.get("error"):
            return None
        return {
            "lcp_p75": data.get("lcp_p75"),
            "inp_p75": data.get("inp_p75"),
            "cls_p75": data.get("cls_p75"),
            "fcp_p75": data.get("fcp_p75"),
            "ttfb_p75": data.get("ttfb_p75"),
        }
    except Exception:
        return None


# ---------------------------------------------------------------------------
# 17 comparison rules
# ---------------------------------------------------------------------------

def _finding(rule: str, severity: str, triggered: bool, old_value, new_value, message: str) -> dict:
    return {
        "rule": rule,
        "severity": severity,
        "triggered": triggered,
        "old_value": old_value,
        "new_value": new_value,
        "message": message,
    }


def _rule_01_schema_removed(baseline: dict, current: dict) -> dict:
    old = json.loads(baseline.get("schema_json") or "[]")
    new = current.get("schema", [])
    triggered = len(old) > 0 and len(new) == 0
    return _finding(
        "schema_removed", "CRITICAL", triggered,
        f"{len(old)} schema block(s)", "0 schema blocks",
        "All JSON-LD removed. Rich results will be lost. Restore immediately."
        if triggered else "Schema presence unchanged.",
    )


def _rule_02_canonical_changed(baseline: dict, current: dict) -> dict:
    old = baseline.get("canonical")
    new = current.get("canonical")
    triggered = old is not None and new is not None and old != new
    return _finding(
        "canonical_changed", "CRITICAL", triggered, old, new,
        f"Canonical changed from {old!r} to {new!r}. Verify this is intentional."
        if triggered else "Canonical URL unchanged.",
    )


def _rule_03_canonical_removed(baseline: dict, current: dict) -> dict:
    old = baseline.get("canonical")
    new = current.get("canonical")
    triggered = old is not None and (new is None or new == "")
    return _finding(
        "canonical_removed", "CRITICAL", triggered, old, None,
        "Canonical tag removed. Google will guess the canonical, often incorrectly."
        if triggered else "Canonical tag presence unchanged.",
    )


def _rule_04_noindex_added(baseline: dict, current: dict) -> dict:
    old_robots = (baseline.get("robots") or "").lower()
    new_robots = (current.get("meta_robots") or "").lower()
    triggered = "noindex" not in old_robots and "noindex" in new_robots
    return _finding(
        "noindex_added", "CRITICAL", triggered,
        baseline.get("robots"), current.get("meta_robots"),
        "noindex directive added. Page will be dropped from search results within days."
        if triggered else "Robots directives unchanged.",
    )


def _rule_05_h1_removed(baseline: dict, current: dict) -> dict:
    old_h1 = baseline.get("h1")
    new_h1_list = current.get("h1", [])
    triggered = old_h1 is not None and old_h1 != "" and len(new_h1_list) == 0
    return _finding(
        "h1_removed", "CRITICAL", triggered, old_h1, None,
        "H1 removed. Primary topic signal for search engines is gone."
        if triggered else "H1 presence unchanged.",
    )


def _rule_06_h1_changed_significantly(baseline: dict, current: dict) -> dict:
    old_h1 = baseline.get("h1") or ""
    new_h1_list = current.get("h1", [])
    new_h1 = new_h1_list[0] if new_h1_list else ""
    if not old_h1 or not new_h1:
        return _finding("h1_changed", "CRITICAL", False, old_h1, new_h1, "H1 comparison skipped (one side empty).")
    ratio = SequenceMatcher(None, old_h1, new_h1).ratio()
    triggered = ratio < 0.5
    return _finding(
        "h1_changed", "CRITICAL", triggered, old_h1, new_h1,
        f"H1 changed significantly (similarity {ratio:.0%}). Verify keyword targeting."
        if triggered else f"H1 text similar enough (similarity {ratio:.0%}).",
    )


def _rule_07_title_removed(baseline: dict, current: dict) -> dict:
    old = baseline.get("title")
    new = current.get("title")
    triggered = old is not None and old != "" and (new is None or new == "")
    return _finding(
        "title_removed", "CRITICAL", triggered, old, None,
        "Title tag removed. Google will auto-generate one, often poorly."
        if triggered else "Title tag presence unchanged.",
    )


def _rule_08_status_code_error(baseline: dict, current_status: Optional[int]) -> dict:
    old = baseline.get("status_code")
    new = current_status
    old_ok = old is not None and 200 <= old < 400
    new_error = new is not None and new >= 400
    triggered = old_ok and new_error
    return _finding(
        "status_code_error", "CRITICAL", triggered, old, new,
        f"Page now returns HTTP {new} (was {old}). Rankings will drop within days."
        if triggered else f"Status code: {old} -> {new}.",
    )


def _rule_09_title_changed(baseline: dict, current: dict) -> dict:
    old = (baseline.get("title") or "").strip()
    new = (current.get("title") or "").strip()
    triggered = old != "" and new != "" and old != new
    return _finding(
        "title_changed", "WARNING", triggered, old, new,
        "Title text changed. Monitor CTR in Search Console over 2 weeks."
        if triggered else "Title text unchanged.",
    )


def _rule_10_meta_description_changed(baseline: dict, current: dict) -> dict:
    old = (baseline.get("meta_description") or "").strip()
    new = (current.get("meta_description") or "").strip()
    triggered = old != "" and new != "" and old != new
    return _finding(
        "meta_description_changed", "WARNING", triggered,
        old[:120] + ("..." if len(old) > 120 else ""),
        new[:120] + ("..." if len(new) > 120 else ""),
        "Meta description changed. Verify it includes target keywords and CTA."
        if triggered else "Meta description unchanged.",
    )


def _rule_11_cwv_regressed(baseline: dict, current_cwv: Optional[dict]) -> dict:
    old_cwv = json.loads(baseline.get("cwv_json") or "null")
    if not old_cwv or not current_cwv:
        return _finding("cwv_regressed", "WARNING", False, None, None, "CWV comparison skipped (data unavailable).")
    regressions = []
    for metric in ("lcp_p75", "inp_p75", "cls_p75"):
        old_val = old_cwv.get(metric)
        new_val = current_cwv.get(metric)
        if old_val is not None and new_val is not None and old_val > 0:
            pct = (new_val - old_val) / old_val
            if pct > 0.20:
                regressions.append(f"{metric}: {old_val} -> {new_val} (+{pct:.0%})")
    triggered = len(regressions) > 0
    return _finding(
        "cwv_regressed", "WARNING", triggered, old_cwv, current_cwv,
        f"CWV regressions: {'; '.join(regressions)}"
        if triggered else "No significant CWV regressions.",
    )


def _rule_12_perf_score_dropped(baseline: dict, current_cwv: Optional[dict]) -> dict:
    # CrUX field data does not include a Lighthouse performance score.
    # Rule retained for structural completeness; always returns not triggered.
    return _finding(
        "perf_score_dropped", "WARNING", False, None, None,
        "Performance score comparison skipped (CrUX field data does not include Lighthouse score).",
    )


def _rule_13_og_tags_removed(baseline: dict, current: dict) -> dict:
    old_og = json.loads(baseline.get("og_json") or "{}")
    new_og = current.get("open_graph", {})
    triggered = len(old_og) > 0 and len(new_og) == 0
    return _finding(
        "og_tags_removed", "WARNING", triggered,
        list(old_og.keys()), [],
        "All OG tags removed. Social sharing will show generic previews."
        if triggered else "OG tags presence unchanged.",
    )


def _rule_14_schema_modified(baseline: dict, current: dict) -> dict:
    old_hash = baseline.get("schema_hash")
    new_schema = current.get("schema", [])
    new_schema_str = json.dumps(new_schema, sort_keys=True)
    new_hash = _hash_content(new_schema_str) if new_schema else None
    triggered = old_hash is not None and new_hash is not None and old_hash != new_hash
    return _finding(
        "schema_modified", "WARNING", triggered,
        old_hash[:12] + "..." if old_hash else None,
        new_hash[:12] + "..." if new_hash else None,
        "JSON-LD content modified. Validate with schema_validate."
        if triggered else "Schema content hash unchanged.",
    )


def _rule_15_schema_added(baseline: dict, current: dict) -> dict:
    old = json.loads(baseline.get("schema_json") or "[]")
    new = current.get("schema", [])
    triggered = len(old) == 0 and len(new) > 0
    return _finding(
        "schema_added", "INFO", triggered,
        "0 schema blocks", f"{len(new)} schema block(s)",
        "New structured data added. Validate with schema_validate."
        if triggered else "No new schema added.",
    )


def _rule_16_h2_structure_changed(baseline: dict, current: dict) -> dict:
    old_h2 = json.loads(baseline.get("h2_json") or "[]")
    new_h2 = current.get("h2", [])
    triggered = old_h2 != new_h2
    return _finding(
        "h2_structure_changed", "INFO", triggered,
        f"{len(old_h2)} H2s", f"{len(new_h2)} H2s",
        f"H2 structure changed ({len(old_h2)} -> {len(new_h2)} headings)."
        if triggered else "H2 structure unchanged.",
    )


def _rule_17_content_hash_changed(baseline: dict, current_html_hash: Optional[str]) -> dict:
    old_hash = baseline.get("html_hash")
    triggered = old_hash is not None and current_html_hash is not None and old_hash != current_html_hash
    return _finding(
        "content_hash_changed", "INFO", triggered,
        old_hash[:12] + "..." if old_hash else None,
        current_html_hash[:12] + "..." if current_html_hash else None,
        "Page content changed (HTML body hash differs from baseline)."
        if triggered else "Page content hash unchanged.",
    )


def _run_rules(baseline: dict, parsed: dict, current_status: Optional[int], current_cwv: Optional[dict]) -> list[dict]:
    return [
        _rule_01_schema_removed(baseline, parsed),
        _rule_02_canonical_changed(baseline, parsed),
        _rule_03_canonical_removed(baseline, parsed),
        _rule_04_noindex_added(baseline, parsed),
        _rule_05_h1_removed(baseline, parsed),
        _rule_06_h1_changed_significantly(baseline, parsed),
        _rule_07_title_removed(baseline, parsed),
        _rule_08_status_code_error(baseline, current_status),
        _rule_09_title_changed(baseline, parsed),
        _rule_10_meta_description_changed(baseline, parsed),
        _rule_11_cwv_regressed(baseline, current_cwv),
        _rule_12_perf_score_dropped(baseline, current_cwv),
        _rule_13_og_tags_removed(baseline, parsed),
        _rule_14_schema_modified(baseline, parsed),
        _rule_15_schema_added(baseline, parsed),
        _rule_16_h2_structure_changed(baseline, parsed),
        _rule_17_content_hash_changed(baseline, baseline.get("html_hash")),  # placeholder, overridden in compare
    ]


# ---------------------------------------------------------------------------
# Tool: drift_baseline
# ---------------------------------------------------------------------------

def drift_baseline(url: str, skip_cwv: bool = False) -> str:
    """Capture an SEO baseline snapshot for a URL.

    Fetches the page, extracts critical SEO signals (title, meta tags, canonical,
    headings, JSON-LD, OpenGraph), and stores them in a local SQLite database as
    a "known good" reference. Call drift_compare later to detect regressions.

    Adapted from scripts/drift_baseline.py in claude-seo (Dan Colta methodology, MIT).
    No Google API calls. CWV capture requires CRUX_API_KEY (skipped otherwise).
    """
    if not url:
        return json.dumps(with_meta(
            {"url": url, "error": "URL is required", "verdict": "error"},
            tool="drift_baseline", params={"url": url},
        ))

    try:
        html, status_code = safe_fetch_html(url, timeout=20)
    except URLSafetyError as exc:
        return json.dumps(with_meta(
            {"url": url, "error": str(exc), "verdict": "ssrf_blocked"},
            tool="drift_baseline", params={"url": url},
        ))
    except httpx.HTTPError as exc:
        return json.dumps(with_meta(
            {"url": url, "error": str(exc), "verdict": "fetch_error"},
            tool="drift_baseline", params={"url": url},
        ))

    parsed = _parse_html(html)
    cwv = None if skip_cwv else _fetch_cwv(url)

    html_hash = _hash_content(html)
    schema_str = json.dumps(parsed["schema"], sort_keys=True)
    schema_hash = _hash_content(schema_str) if parsed["schema"] else None

    now = datetime.now(timezone.utc).isoformat()
    norm_url = _normalize_url(url)
    uhash = _url_hash(url)

    h1_text = parsed["h1"][0] if parsed["h1"] else None

    conn = _init_db()
    try:
        cursor = conn.execute(
            """
            INSERT INTO baselines (
                url, url_hash, timestamp, title, meta_description, canonical,
                robots, h1, h2_json, h3_json, schema_json, og_json, cwv_json,
                html_hash, schema_hash, status_code
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                norm_url, uhash, now,
                parsed["title"], parsed["meta_description"], parsed["canonical"],
                parsed["meta_robots"], h1_text,
                json.dumps(parsed["h2"]), json.dumps(parsed["h3"]),
                json.dumps(parsed["schema"]), json.dumps(parsed["open_graph"]),
                json.dumps(cwv) if cwv else None,
                html_hash, schema_hash, status_code,
            ),
        )
        conn.commit()
        baseline_id = cursor.lastrowid
    finally:
        conn.close()

    return json.dumps(with_meta(
        {
            "status": "ok",
            "baseline_id": baseline_id,
            "url": norm_url,
            "timestamp": now,
            "title": parsed["title"],
            "canonical": parsed["canonical"],
            "h1": h1_text,
            "h2_count": len(parsed["h2"]),
            "h3_count": len(parsed["h3"]),
            "schema_count": len(parsed["schema"]),
            "og_tag_count": len(parsed["open_graph"]),
            "cwv_captured": cwv is not None,
            "status_code": status_code,
        },
        tool="drift_baseline", params={"url": url},
    ))


# ---------------------------------------------------------------------------
# Tool: drift_compare
# ---------------------------------------------------------------------------

def drift_compare(url: str, baseline_id: Optional[int] = None, skip_cwv: bool = False) -> str:
    """Compare current page state to a stored baseline and report SEO drift.

    Applies 17 comparison rules (8 CRITICAL, 6 WARNING, 3 INFO) and returns
    triggered findings with severity, old/new values, and recommended actions.
    Call drift_baseline first if no baseline exists for this URL.

    Adapted from scripts/drift_compare.py in claude-seo (Dan Colta methodology, MIT).
    No Google API calls. CWV comparison requires CRUX_API_KEY (skipped otherwise).
    """
    if not url:
        return json.dumps(with_meta(
            {"url": url, "error": "URL is required", "verdict": "error"},
            tool="drift_compare", params={"url": url},
        ))

    uhash = _url_hash(url)
    norm_url = _normalize_url(url)

    conn = _init_db()
    try:
        if baseline_id is not None:
            row = conn.execute(
                "SELECT * FROM baselines WHERE id = ? AND url_hash = ?",
                (baseline_id, uhash),
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT * FROM baselines WHERE url_hash = ? ORDER BY id DESC LIMIT 1",
                (uhash,),
            ).fetchone()
    except sqlite3.Error as exc:
        conn.close()
        return json.dumps(with_meta(
            {"url": norm_url, "error": f"Database error: {exc}", "verdict": "error"},
            tool="drift_compare", params={"url": url},
        ))

    if not row:
        conn.close()
        msg = f"No baseline for {norm_url}. Run drift_baseline first."
        return json.dumps(with_meta(
            {"url": norm_url, "error": msg, "verdict": "no_baseline"},
            tool="drift_compare", params={"url": url},
        ))

    cols = [d[0] for d in conn.execute("SELECT * FROM baselines LIMIT 0").description]
    baseline = dict(zip(cols, row))

    try:
        html, status_code = safe_fetch_html(url, timeout=20)
    except (URLSafetyError, httpx.HTTPError) as exc:
        conn.close()
        return json.dumps(with_meta(
            {"url": norm_url, "error": str(exc), "verdict": "fetch_error"},
            tool="drift_compare", params={"url": url},
        ))

    parsed = _parse_html(html)
    current_cwv = None if skip_cwv else _fetch_cwv(url)
    current_html_hash = _hash_content(html)

    findings = [
        _rule_01_schema_removed(baseline, parsed),
        _rule_02_canonical_changed(baseline, parsed),
        _rule_03_canonical_removed(baseline, parsed),
        _rule_04_noindex_added(baseline, parsed),
        _rule_05_h1_removed(baseline, parsed),
        _rule_06_h1_changed_significantly(baseline, parsed),
        _rule_07_title_removed(baseline, parsed),
        _rule_08_status_code_error(baseline, status_code),
        _rule_09_title_changed(baseline, parsed),
        _rule_10_meta_description_changed(baseline, parsed),
        _rule_11_cwv_regressed(baseline, current_cwv),
        _rule_12_perf_score_dropped(baseline, current_cwv),
        _rule_13_og_tags_removed(baseline, parsed),
        _rule_14_schema_modified(baseline, parsed),
        _rule_15_schema_added(baseline, parsed),
        _rule_16_h2_structure_changed(baseline, parsed),
        _rule_17_content_hash_changed(baseline, current_html_hash),
    ]

    triggered = [f for f in findings if f["triggered"]]
    critical_count = sum(1 for f in triggered if f["severity"] == "CRITICAL")
    warning_count = sum(1 for f in triggered if f["severity"] == "WARNING")
    info_count = sum(1 for f in triggered if f["severity"] == "INFO")

    now = datetime.now(timezone.utc).isoformat()

    result = {
        "url": norm_url,
        "baseline_id": baseline["id"],
        "baseline_timestamp": baseline["timestamp"],
        "comparison_timestamp": now,
        "summary": {
            "total_rules": len(findings),
            "triggered": len(triggered),
            "critical": critical_count,
            "warning": warning_count,
            "info": info_count,
        },
        "triggered_findings": triggered,
        "all_findings": findings,
        "current_status_code": status_code,
        "cwv_compared": current_cwv is not None,
    }

    try:
        conn.execute(
            """
            INSERT INTO comparisons (
                url, url_hash, baseline_id, timestamp, results_json,
                critical_count, warning_count, info_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                norm_url, uhash, baseline["id"], now, json.dumps(result),
                critical_count, warning_count, info_count,
            ),
        )
        conn.commit()
    except sqlite3.Error as exc:
        result["db_warning"] = f"Could not save comparison: {exc}"
    finally:
        conn.close()

    return json.dumps(with_meta(result, tool="drift_compare", params={"url": url}))


# ---------------------------------------------------------------------------
# Tool: drift_history
# ---------------------------------------------------------------------------

def drift_history(url: str, limit: int = 10) -> str:
    """Return recent drift comparisons for a URL.

    Shows comparison timestamps, triggered finding counts by severity, and
    baseline IDs. Use drift_compare to run a fresh comparison.
    """
    if not url:
        return json.dumps(with_meta(
            {"url": url, "error": "URL is required", "comparisons": []},
            tool="drift_history", params={"url": url},
        ))

    uhash = _url_hash(url)
    norm_url = _normalize_url(url)

    conn = _init_db()
    try:
        rows = conn.execute(
            """
            SELECT id, baseline_id, timestamp, critical_count, warning_count, info_count
            FROM comparisons
            WHERE url_hash = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (uhash, max(1, int(limit))),
        ).fetchall()
    except sqlite3.Error as exc:
        conn.close()
        return json.dumps(with_meta(
            {"url": norm_url, "error": str(exc), "comparisons": []},
            tool="drift_history", params={"url": url},
        ))
    finally:
        conn.close()

    comparisons = [
        {
            "comparison_id": row[0],
            "baseline_id": row[1],
            "timestamp": row[2],
            "critical": row[3],
            "warning": row[4],
            "info": row[5],
        }
        for row in rows
    ]

    return json.dumps(with_meta(
        {
            "url": norm_url,
            "count": len(comparisons),
            "comparisons": comparisons,
        },
        tool="drift_history", params={"url": url},
    ))
