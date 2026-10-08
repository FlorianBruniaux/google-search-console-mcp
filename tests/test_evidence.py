"""Evidence is provenance, not probability, safety or permission to act."""

import ast
import copy
import inspect
import json
import re
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from gsc_mcp.meta import with_meta


def fields(tool, data):
    return with_meta(data, tool, {})["_meta"]["evidence"]["fields"]


def assert_basis(records, pointer, basis, tier):
    assert records[pointer]["basis"] == basis
    assert records[pointer]["confidence_tier"] == tier
    assert records[pointer]["scope"]
    assert "confidence" not in records[pointer]


def test_additive_metadata_preserves_inputs_sources_and_nested_values():
    data = {"verdict": "PASS", "category": "indexed", "score": 0,
            "extra": {"status": "unknown", "score": 23}}
    before = copy.deepcopy(data)
    params = {"url": "https://example.com", "site": "sc-domain:example.com"}
    sources = {"gsc": {"site": "sc-domain:example.com"}}
    result = with_meta(data, "inspect_url", params, sources=sources)
    meta = result.pop("_meta")
    assert result == before == data
    assert meta["params"] == params
    assert meta["sources"] == sources
    assert meta["evidence"]["version"] == 1
    assert set(meta["evidence"]["fields"]) == {"/verdict", "/category"}
    assert_basis(meta["evidence"]["fields"], "/verdict", "measured", "observed")
    assert_basis(meta["evidence"]["fields"], "/category", "rule", "heuristic")


def test_registry_requires_explicit_applicability_for_every_registered_tool():
    from gsc_mcp.evidence import INVENTORY
    from gsc_mcp.registry import TOOLS
    assert set(INVENTORY) == set(TOOLS)
    assert all(entry["applicability"] in {"fields", "error_only", "operational", "data_only"}
               and entry["reason"] for entry in INVENTORY.values())


def test_unreviewed_generic_metadata_does_not_invent_evidence_and_model_descriptors_are_rejected():
    from gsc_mcp.evidence import validate_descriptor
    result = with_meta({"score": 3}, "new_unreviewed_tool", {})
    assert result["_meta"]["evidence"] == {"version": 1, "fields": {}, "inventory_status": "unregistered"}
    with pytest.raises(ValueError, match="model"):
        validate_descriptor({"basis": "model", "confidence_tier": "act", "scope": "prediction"})
    with pytest.raises(ValueError):
        validate_descriptor({"basis": "rule", "confidence_tier": "observed", "scope": "rule"})


def test_future_model_field_is_rejected_at_metadata_boundary(monkeypatch):
    from gsc_mcp.evidence import _PATHS
    monkeypatch.setitem(_PATHS, "content_quality", [("/score", "model", "uncalibrated output")])
    with pytest.raises(ValueError, match="model"):
        fields("content_quality", {"score": .8})


def test_real_inspection_calls_distinguish_provider_states_local_categories_and_missing_data(monkeypatch):
    from gsc_mcp.tools import inspection
    svc = MagicMock()
    samples = [{"verdict": "PASS", "pageFetchState": "SUCCESSFUL"},
               {}, {"pageFetchState": "PAGE_FETCH_STATE_UNSPECIFIED"},
               {"verdict": "FAIL", "pageFetchState": "SOFT_404"}]
    execute = svc.urlInspection.return_value.index.return_value.inspect.return_value.execute
    execute.side_effect = [{"inspectionResult": {"indexStatusResult": row}} for row in samples]
    monkeypatch.setattr(inspection, "get_searchconsole_service", lambda: svc)
    data = json.loads(inspection.batch_url_inspection(["a", "b", "c", "d"], "site"))
    records = data["_meta"]["evidence"]["fields"]
    assert_basis(records, "/results/0/verdict", "measured", "observed")
    assert_basis(records, "/results/0/category", "rule", "heuristic")
    assert_basis(records, "/results/1/verdict", None, "unavailable")
    assert_basis(records, "/results/1/category", None, "unavailable")
    assert_basis(records, "/results/2/page_fetch_state", None, "unavailable")
    assert_basis(records, "/results/2/category", None, "unavailable")
    # A genuine provider fetch failure is observed, unlike a local fetch error.
    assert_basis(records, "/results/3/page_fetch_state", "measured", "observed")
    assert_basis(records, "/results/3/category", "rule", "heuristic")
    execute.side_effect = None
    execute.return_value = {"inspectionResult": {"indexStatusResult": samples[0]}}
    single = json.loads(inspection.inspect_url("a", "site"))
    assert_basis(single["_meta"]["evidence"]["fields"], "/verdict", "measured", "observed")
    issues = json.loads(inspection.check_indexing_issues(["a"], "site"))
    assert_basis(issues["_meta"]["evidence"]["fields"], "/summary", "derived", "calculated")


@pytest.mark.parametrize("provider_field,provider_value,output_field", [
    ("verdict", "VERDICT_UNSPECIFIED", "verdict"),
    ("indexingState", "INDEXING_STATE_UNSPECIFIED", "indexing_state"),
    ("robotsTxtState", "ROBOTS_TXT_STATE_UNSPECIFIED", "robots_txt_state"),
])
def test_real_inspection_unspecified_only_inputs_cannot_support_category(monkeypatch, provider_field, provider_value, output_field):
    from gsc_mcp.tools import inspection
    svc = MagicMock()
    svc.urlInspection.return_value.index.return_value.inspect.return_value.execute.return_value = {
        "inspectionResult": {"indexStatusResult": {provider_field: provider_value}}}
    monkeypatch.setattr(inspection, "get_searchconsole_service", lambda: svc)
    results = [
        (json.loads(inspection.inspect_url("a", "site")), "", None),
        (json.loads(inspection.batch_url_inspection(["a"], "site")), "/results/0", "results"),
        (json.loads(inspection.check_indexing_issues(["a"], "site")), "/issues/0", "issues"),
    ]
    for result, prefix, collection in results:
        row = result[collection][0] if collection else result
        assert row["category"] == "not_indexed"
        assert row[output_field] == provider_value
        records = result["_meta"]["evidence"]["fields"]
        assert_basis(records, f"{prefix}/{output_field}", None, "unavailable")
        assert_basis(records, f"{prefix}/category", None, "unavailable")


def test_real_anomaly_statistics_are_calculated_but_selection_is_a_rule(monkeypatch):
    from gsc_mcp.tools import analytics
    monkeypatch.setattr(analytics, "get_searchconsole_service", lambda: object())
    monkeypatch.setattr(analytics, "_fetch_rows", lambda *args: [
        {"date": f"2026-01-0{i + 1}", "clicks": clicks} for i, clicks in enumerate([1, 1, 1, 9])])
    result = json.loads(analytics.analytics_anomalies("site", threshold=1))
    records = result["_meta"]["evidence"]["fields"]
    assert_basis(records, "/anomalies", "rule", "heuristic")
    assert_basis(records, "/anomalies/0/z_score", "derived", "calculated")
    assert_basis(records, "/anomalies/0/type", "rule", "heuristic")


def test_real_quick_win_score_is_a_benchmark_assumption(monkeypatch):
    from gsc_mcp.tools import seo
    monkeypatch.setattr(seo, "_fetch_metric_rows", lambda *args: object())
    monkeypatch.setattr(seo, "_rows_as_dicts", lambda batch: [{
        "page": "/a", "position": 5, "clicks": 1, "impressions": 1000, "ctr": .001}])
    result = json.loads(seo.quick_wins("site"))
    assert_basis(result["_meta"]["evidence"]["fields"], "/opportunities/0/opportunity_score", "rule", "heuristic")


def test_real_content_quality_separates_repetition_arithmetic_from_quality_rules(monkeypatch):
    from gsc_mcp.tools import content
    monkeypatch.setattr(content, "safe_fetch_html", lambda *args, **kwargs: (
        "<p>alpha beta gamma alpha beta gamma 42 Paris</p>", 200))
    result = json.loads(content.content_quality("https://example.com"))
    assert_basis(result["_meta"]["evidence"]["fields"], "/repetition_score", "derived", "calculated")
    assert_basis(result["_meta"]["evidence"]["fields"], "/overall_quality", "rule", "heuristic")


@pytest.mark.parametrize("tool,data,expected", [
    ("seo_cannibalization", {"conflicts": [{"conflict_score": .5, "total_clicks": 2},
                                           {"conflict_score": .5, "total_clicks": 0}]},
     {"/conflicts/0/conflict_score": "derived", "/conflicts/1/conflict_score": "rule"}),
    ("page_health_score", {"score": 100, "components": {"gsc": {"score": 30, "available": True},
                                                            "crux": {"score": 0, "available": False}}},
     {"/score": "rule", "/components/gsc/score": "rule", "/components/crux/score": None}),
    ("page_health_score", {"score": 0, "components": {"gsc": {"score": 0, "available": False}}},
     {"/score": None, "/components/gsc/score": None}),
    ("ai_visibility_audit", {"verdict": "open", "robots_txt_found": False, "crawlers": [{"allowed": True}]},
     {"/verdict": None, "/crawlers/0/allowed": None}),
    ("schema_validate", {"verdict": "challenge_page", "schemas": None, "recommendations": None,
                         "challenge": {"provider": "siteground", "reasons": ["pattern"]},
                         "google_rich_result_eligibility": "not_assessed"},
     {"/verdict": "rule", "/schemas": None, "/recommendations": None, "/challenge": "rule", "/google_rich_result_eligibility": None}),
    ("schema_validate", {"verdict": "healthy", "schemas": [{"valid": True, "deprecated_rich_result": None}]},
     {"/schemas/0/valid": "rule", "/schemas/0/deprecated_rich_result": "rule"}),
    ("heading_audit", {"verdict": "healthy", "title_h1_overlap": None, "words_per_h2": 0, "descriptive_ratio": 1},
     {"/title_h1_overlap": None, "/words_per_h2": "derived", "/descriptive_ratio": "rule"}),
    ("drift_compare", {"all_findings": [{"rule": "perf_score_dropped", "severity": "WARNING", "triggered": False,
                                        "old_value": None, "new_value": None, "message": "comparison skipped"},
                                       {"rule": "title_removed", "severity": "CRITICAL", "triggered": True,
                                        "old_value": "title", "new_value": None, "message": "removed"}]},
     {"/all_findings/0/triggered": None, "/all_findings/0/severity": None, "/all_findings/1/triggered": "rule"}),
    ("bing_url_info", {"http_status": 0, "is_page": False}, {"/http_status": None, "/is_page": None}),
    ("bing_feeds_list", {"feeds": [{"status": "Success"}, {"status": None}]},
     {"/feeds/0/status": "measured", "/feeds/1/status": None}),
    ("traffic_health_check", {"status": "incomplete_coverage", "ratio": None, "total_gsc_clicks": 0,
                              "source_data": {"gsc": {"availability": "measured"}, "ga4": {"availability": "unknown"}},
                              "comparison": {"comparable": False}},
     {"/ratio": None, "/status": None, "/total_gsc_clicks": "derived", "/comparison/comparable": "rule"}),
    ("indexnow_submit", {"status_code": 202, "status": "received", "verdict": "ok", "key_validation": "pending"},
     {"/status_code": "measured", "/status": "rule", "/verdict": "rule", "/key_validation": "rule"}),
    ("indexnow_submit", {"status_code": None, "status": "error", "verdict": "error", "error_category": "timeout"},
     {"/status_code": None, "/status": None, "/verdict": None}),
])
def test_degraded_outputs_preserve_sentinels_and_meaningful_zeroes(tool, data, expected):
    records = fields(tool, data)
    for pointer, basis in expected.items():
        assert_basis(records, pointer, basis, {"measured": "observed", "derived": "calculated", "rule": "heuristic", None: "unavailable"}[basis])


def test_pointer_escaping_and_whitelisting_do_not_label_arbitrary_content():
    data = {"metrics": {"a~/b": {"p75": 0, "rating": "good", "score": 42}}}
    records = fields("crux_page_vitals", data)
    assert set(records) == {"/metrics/a~0~1b/p75", "/metrics/a~0~1b/rating"}
    assert fields("schema_generate", {"verdict": "generated", "json_ld": {"score": 55, "verdict": "PASS"}}) == {}
    assert fields("submit_url", {"status": "submitted"}) == {}
    assert fields("ga4_funnel", {"error": "INVALID_STEPS"})["/error"]["basis"] is None


def test_http_content_instruction_signals_are_rules_and_never_trust():
    data = {"verdict": "healthy", "untrusted_content": {
        "trust": "untrusted", "assessment": "deterministic_rules_only", "flagged": False,
        "signals": [{"basis": "rule", "method": "deterministic_patterns", "reason": "pattern"}]}}
    records = fields("page_technical_audit", data)
    assert_basis(records, "/untrusted_content/flagged", "rule", "heuristic")
    assert_basis(records, "/untrusted_content/signals/0", "rule", "heuristic")
    assert "/untrusted_content/trust" not in records


def test_real_pagespeed_scores_are_heuristics_and_lab_values_are_observations(monkeypatch):
    from gsc_mcp.tools import technical
    monkeypatch.setenv("GOOGLE_API_KEY", "test")
    monkeypatch.setattr(technical, "validate_url_strict", lambda url: None)
    client = MagicMock()
    client.__enter__.return_value = client
    client.get.return_value.json.return_value = {"lighthouseResult": {
        "categories": {"performance": {"score": .91}}, "audits": {
            "largest-contentful-paint": {"score": .8, "numericValue": 2300},
            "unused-css-rules": {"score": .4, "details": {"type": "opportunity"}}}}}
    monkeypatch.setattr(technical.httpx, "Client", lambda **kwargs: client)
    result = json.loads(technical.pagespeed_audit("https://example.com"))
    records = result["_meta"]["evidence"]["fields"]
    assert result["performance_score"] == 91
    assert_basis(records, "/performance_score", "rule", "heuristic")
    assert_basis(records, "/cwv/lcp/score", "rule", "heuristic")
    assert_basis(records, "/cwv/lcp/numeric_value", "measured", "observed")
    assert_basis(records, "/cwv/tbt/score", None, "unavailable")
    assert_basis(records, "/top_opportunities/0/score", "rule", "heuristic")


def test_real_crux_subparts_keep_measured_p75_separate_from_dominance_and_rating(monkeypatch):
    from gsc_mcp.tools import crux
    monkeypatch.setenv("CRUX_API_KEY", "test")
    client = MagicMock()
    client.__enter__.return_value = client
    client.post.return_value.status_code = 200
    client.post.return_value.json.return_value = {"record": {"metrics": {
        "largest_contentful_paint": {"percentiles": {"p75": 2500}},
        "largest_contentful_paint_image_time_to_first_byte": {"percentiles": {"p75": 1000}},
        "largest_contentful_paint_image_resource_load_delay": {"percentiles": {"p75": 300}}}}}
    monkeypatch.setattr(crux.httpx, "Client", lambda **kwargs: client)
    result = json.loads(crux.crux_lcp_subparts("https://example.com"))
    records = result["_meta"]["evidence"]["fields"]
    assert_basis(records, "/lcp_p75_ms", "measured", "observed")
    assert_basis(records, "/subparts/dominant_phase", "derived", "calculated")
    assert_basis(records, "/lcp_rating", "rule", "heuristic")
    assert_basis(records, "/subparts/render_delay_ms", None, "unavailable")


def test_real_health_composition_marks_complete_partial_and_all_unavailable_scores(monkeypatch):
    from gsc_mcp.tools import cross
    monkeypatch.setattr(cross, "inspect_url", lambda **kwargs: json.dumps({"verdict": "PASS", "indexing_state": "INDEXING_ALLOWED"}))
    monkeypatch.setattr(cross, "ga4_page_performance", lambda **kwargs: json.dumps({"pages": [{"active_users": 1, "engagement_rate": .8}]}))
    monkeypatch.setattr(cross, "crux_page_vitals", lambda **kwargs: json.dumps({"metrics": {
        "largest_contentful_paint": {"rating": "good"}, "interaction_to_next_paint": {"rating": "good"},
        "cumulative_layout_shift": {"rating": "good"}}}))
    monkeypatch.setattr(cross, "schema_validate", lambda **kwargs: json.dumps({"schemas_detected": 1, "schemas": [{"missing_required_fields": []}]}))
    complete = json.loads(cross.page_health_score("site", "https://example.com"))
    assert complete["score"] == 100
    assert_basis(complete["_meta"]["evidence"]["fields"], "/components/schema/score", "rule", "heuristic")
    def unavailable(**kwargs):
        raise RuntimeError("credentials unavailable")
    monkeypatch.setattr(cross, "crux_page_vitals", unavailable)
    partial = json.loads(cross.page_health_score("site", "https://example.com"))
    assert partial["score"] == 100
    assert_basis(partial["_meta"]["evidence"]["fields"], "/components/crux/score", None, "unavailable")
    assert "renormalized" in partial["_meta"]["evidence"]["fields"]["/score"]["scope"]
    for name in ("inspect_url", "ga4_page_performance", "schema_validate"):
        monkeypatch.setattr(cross, name, unavailable)
    absent = json.loads(cross.page_health_score("site", "https://example.com"))
    assert absent["score"] == 0
    assert_basis(absent["_meta"]["evidence"]["fields"], "/score", None, "unavailable")


def test_real_drift_comparison_and_history_keep_skipped_rules_unavailable(monkeypatch, tmp_path):
    from gsc_mcp.tools import drift
    monkeypatch.setattr(drift, "_DB_PATH", tmp_path / "drift.db")
    monkeypatch.setattr(drift, "safe_fetch_html", lambda *args, **kwargs: ("<title>Before</title><h1>Heading</h1>", 200))
    baseline = json.loads(drift.drift_baseline("https://example.com", skip_cwv=True))
    assert baseline["_meta"]["evidence"]["fields"] == {}
    monkeypatch.setattr(drift, "safe_fetch_html", lambda *args, **kwargs: ("<p>After</p>", 200))
    comparison = json.loads(drift.drift_compare("https://example.com", skip_cwv=True))
    records = comparison["_meta"]["evidence"]["fields"]
    for i, finding in enumerate(comparison["all_findings"]):
        if finding["rule"] == "perf_score_dropped":
            assert_basis(records, f"/all_findings/{i}/triggered", None, "unavailable")
        elif finding["rule"] == "h1_changed":
            assert_basis(records, f"/all_findings/{i}/triggered", None, "unavailable")
        elif finding["rule"] == "title_removed":
            assert_basis(records, f"/all_findings/{i}/triggered", "rule", "heuristic")
    assert_basis(records, "/summary/critical", "derived", "calculated")
    history = json.loads(drift.drift_history("https://example.com"))
    assert_basis(history["_meta"]["evidence"]["fields"], "/comparisons/0/critical", "derived", "calculated")


def test_drift_rules_without_comparable_status_or_cwv_pairs_are_unavailable():
    from gsc_mcp.tools import drift
    findings = [drift._rule_08_status_code_error({"status_code": None}, 200),
                drift._rule_11_cwv_regressed({"cwv_json": '{"lcp_p75":1800}'}, {"inp_p75": 120}),
                drift._rule_11_cwv_regressed({"cwv_json": '{"lcp_p75":0}'}, {"lcp_p75": 1800})]
    records = fields("drift_compare", {"all_findings": findings})
    for i in range(len(findings)):
        assert_basis(records, f"/all_findings/{i}/triggered", None, "unavailable")
        assert_basis(records, f"/all_findings/{i}/severity", None, "unavailable")


def test_real_bing_feed_observation_preserves_contract_metadata_and_write_sentinel(monkeypatch):
    from gsc_mcp.tools import bing_webmaster
    client = MagicMock()
    client.read.return_value = [{"Status": "Success", "Url": "https://example.com/sitemap.xml"}]
    monkeypatch.setattr(bing_webmaster, "get_bing_client", lambda: client)
    monkeypatch.setattr(bing_webmaster, "_validate_target", lambda *args: None)
    feed = json.loads(bing_webmaster.bing_feeds_list("https://example.com"))
    assert feed["_meta"]["engine"] == "bing"
    assert_basis(feed["_meta"]["evidence"]["fields"], "/feeds/0/status", "measured", "observed")
    write = json.loads(bing_webmaster.bing_url_submit("https://example.com", "https://example.com/a"))
    assert write["indexed"] is False
    assert write["_meta"]["indexed_semantics"] == "not_verified"
    assert_basis(write["_meta"]["evidence"]["fields"], "/indexed", None, "unavailable")
    assert "/status" not in write["_meta"]["evidence"]["fields"]


# Independent success shapes exercise every reviewed declaration, including
# implicit collection verdicts. Integration tests above verify real producers.
_INSPECTION_SHAPE = {"verdict": "PASS", "robots_txt_state": "ALLOWED", "indexing_state": "INDEXING_ALLOWED",
                     "page_fetch_state": "SUCCESSFUL", "coverage_state": "Submitted and indexed", "category": "indexed"}
_AUDIT_SHAPE = {"verdict": "healthy", "issues": [{"severity": "high"}]}
SUCCESS_SHAPES = {
    "inspect_url": _INSPECTION_SHAPE,
    "batch_url_inspection": {"results": [_INSPECTION_SHAPE]},
    "check_indexing_issues": {"issues": [_INSPECTION_SHAPE], "summary": {"indexed": 1}},
    "analytics_anomalies": {"mean_daily_clicks": 4, "std_daily_clicks": 1, "anomalies": [{"z_score": 3, "type": "spike"}]},
    "quick_wins": {"opportunities": [{"benchmark_ctr": .03, "expected_clicks_at_benchmark": 3, "opportunity_score": 2}]},
    "traffic_drops": {"drops": [{"diagnosis": "ranking_loss", "clicks_delta": -1, "impressions_delta": -2}]},
    "seo_striking_distance": {"queries": []},
    "seo_cannibalization": {"conflicts": [{"conflict_score": .5, "total_clicks": 2}]},
    "seo_lost_queries": {"lost_queries": [{"drop_pct": .8}]},
    "check_alerts": {"alerts": [{"type": "traffic_concentration", "severity": "high", "message": "recommendation"}]},
    "parasite_risk": {"verdict": "high_risk", "site_risk": "high", "results": [{"risk": "high"}]},
    "prune_candidates": {"verdict": "candidates_found", "guard_rail": "review manually", **{key: [{"action": "review"}] for key in ("has_traffic", "impressions_no_clicks", "low_impressions", "zero_impressions")}},
    "traffic_health_check": {"status": "healthy", "ratio": 1, "total_gsc_clicks": 4, "total_ga4_sessions": 4, "comparison": {"comparable": True}, "source_data": {"gsc": {"availability": "measured"}}},
    "page_analysis": {"pages": [{"opportunity_score": 4}]},
    "content_brief": {"current_focus": "query", "question_queries": []},
    "page_health_score": {"score": 100, "components": {"gsc": {"score": 30, "available": True}}},
    "compare_search_engines": {"windows_comparable": True, **{key: value for key, value in (("totals", {"windows_comparable": True, "click_delta": 0, "impression_delta": 1}), ("rows", [{"windows_comparable": True, "click_delta": 0, "impression_delta": 1}]))}},
    "crux_page_vitals": {"metrics": {"largest_contentful_paint": {"p75": 2000, "rating": "good"}}},
    "crux_history": {"history": [{"p75": 2000}]},
    "crux_lcp_subparts": {"lcp_p75_ms": 2000, "lcp_rating": "good", "verdict": "good", "subparts": {"ttfb_ms": 1, "resource_load_delay_ms": 2, "resource_load_duration_ms": 3, "render_delay_ms": 4, "dominant_phase": "render_delay"}},
    "pagespeed_audit": {"performance_score": 90, "verdict": "good", "cwv": {"lcp": {"score": .8, "numeric_value": 2000}}, "top_opportunities": [{"score": .3}]},
    "schema_validate": {"verdict": "healthy", "schemas": [{"valid": True, "missing_required_fields": [], "missing_recommended_fields": [], "deprecated_rich_result": None}], "recommendations": [], "validation_scope": "local_required_field_presence", "google_rich_result_eligibility": "not_assessed", "challenge": {"provider": "siteground"}, "http_status": 200},
    "content_quality": {"verdict": "good", "filler_score": 0, "information_density": .4, "overall_quality": 60, "repetition_score": 0, "flags": []},
    "hreflang_audit": _AUDIT_SHAPE,
    "page_technical_audit": {**_AUDIT_SHAPE, "findings": {"status_code": 200, "redirected": False, "robots_txt_blocks_googlebot": False}},
    "preload_audit": {**_AUDIT_SHAPE, "prerender_deprecated": False, "bfcache_no_store": False},
    "heading_audit": {**_AUDIT_SHAPE, "empty_headings": [], "descriptive_ratio": 1, "title_h1_overlap": .5, "words_per_h2": 100, "title_h1_identical": False, "hierarchy_jumps": []},
    "internal_links_audit": {**_AUDIT_SHAPE, "generic_anchors": [], "empty_anchors": [], "nofollow_internal": [], "footer_only_targets": []},
    "link_equity_map": {**_AUDIT_SHAPE, "underlinked_striking_distance": [], "orphan_candidates": [], "footer_only_targets": [], "hub_pages": []},
    "gbp_deprecation_lint": _AUDIT_SHAPE,
    "ai_visibility_audit": {"verdict": "open", "robots_txt_found": True, "crawlers": [{"allowed": True}]},
    "sitemap_audit": {"verdict": "healthy", "visibility_verdict": "healthy", "urls_with_search_data": 1, "urls_without_search_data": 0, "urls_in_gsc": 1, "urls_missing_from_gsc": 0},
    "drift_compare": {"summary": {"critical": 1}, **{key: [{"rule": "title_removed", "severity": "CRITICAL", "triggered": True, "message": "removed"}] for key in ("triggered_findings", "all_findings")}},
    "drift_history": {"comparisons": [{"critical": 1, "warning": 2, "info": 0}]},
    "bing_feeds_list": {"feeds": [{"status": "Success"}]},
    "bing_feed_details": {"feeds": [{"status": "Success"}]},
    "bing_crawl_issues": {"issues": [{"issue_types": ["code4xx"], "unknown_issue_bits": 0}]},
    "bing_url_info": {"http_status": 200, "is_page": True},
    "ga4_ai_referrals": {"availability": "measured", "rows": [{"classification": "confirmed"}], "ai_session_share": .2, "comparison": {"availability": "unavailable"}},
    "indexnow_submit": {"status_code": 202, "status": "received", "verdict": "ok", "key_validation": "pending"},
}
for _tool in ("schema_validate", "page_technical_audit", "heading_audit", "internal_links_audit"):
    SUCCESS_SHAPES[_tool] = {**SUCCESS_SHAPES[_tool], "untrusted_content": {"flagged": True, "signals": [{"basis": "rule"}]}}


def test_all_applicable_tools_and_declarations_have_exercised_success_or_degraded_shapes():
    from gsc_mcp.evidence import INVENTORY, _PATHS
    applicable = {tool for tool, entry in INVENTORY.items() if entry["applicability"] == "fields"}
    assert applicable <= set(SUCCESS_SHAPES)
    for tool in INVENTORY:
        fixtures = [SUCCESS_SHAPES.get(tool, {}), {"error": "failure", "verdict": "fetch_error", "indexed": False}]
        emitted = {pointer for data in fixtures for pointer in fields(tool, data)}
        for template, _, _ in _PATHS[tool]:
            pattern = "^" + re.escape(template).replace(r"\*", "[^/]+") + "$"
            assert any(re.match(pattern, pointer) for pointer in emitted), (tool, template)
        for data in fixtures:
            records = fields(tool, data)
            for pointer, record in records.items():
                # Every concrete path must resolve in the original payload.
                target = data
                for key in pointer[1:].split("/"):
                    key = key.replace("~1", "/").replace("~0", "~")
                    target = target[int(key)] if isinstance(target, list) else target[key]
                assert record["confidence_tier"] == {"measured": "observed", "derived": "calculated", "rule": "heuristic", None: "unavailable"}[record["basis"]]


# Structural review tripwire, not proof of semantic correctness. Keys in helper
# dictionaries and output assignments are included; generated JSON-LD and
# operational statuses are reviewed exclusions rather than blanket observations.
_REVIEWED_SIGNALS = {
    "analytics.analytics_anomalies": "z_score",
    "bing_webmaster._feed_row": "status",
    "bing_webmaster._mutation_response": "status",
    "bing_webmaster.bing_crawl_issues": "issues",
    "bing_webmaster.bing_feed_remove": "status",
    "content.content_quality": "filler_score overall_quality repetition_score verdict",
    "content.hreflang_audit": "issues severity verdict",
    "content.page_technical_audit": "issues severity verdict",
    "content.preload_audit": "issues severity verdict",
    "content.heading_audit": "issues severity verdict",
    "cross.traffic_health_check": "status",
    "cross.page_analysis": "opportunity_score",
    "cross.content_brief": "current_focus question_queries",
    "cross.page_health_score": "score",
    "crux.crux_page_vitals": "rating verdict",
    "crux.crux_history": "verdict",
    "crux.crux_lcp_subparts": "lcp_rating verdict",
    "drift._finding": "severity triggered",
    "drift.drift_baseline": "status verdict",
    "drift.drift_compare": "triggered verdict",
    "indexing.submit_url": "status",
    "indexing._make_callback": "status",
    "indexing.indexnow_submit": "status verdict",
    "indexing.callback": "status",
    "inspection._parse_inspection": "category verdict",
    "inspection.check_indexing_issues": "issues",
    "links.internal_links_audit": "issues severity verdict",
    "links.link_equity_map": "issues severity verdict",
    "seo._unsupported_bing": "verdict",
    "seo.quick_wins": "opportunities opportunity_score",
    "seo.traffic_drops": "diagnosis drops",
    "seo.seo_striking_distance": "queries",
    "seo.seo_cannibalization": "conflict_score conflicts",
    "seo.seo_lost_queries": "lost_queries",
    "seo.check_alerts": "alerts severity",
    "seo._parasite_check_url": "risk",
    "seo.parasite_risk": "site_risk verdict",
    "seo.prune_candidates": "action verdict",
    "sitemaps.submit_sitemap": "status",
    "sitemaps.sitemaps_delete": "status",
    "sitemaps.sitemap_audit": "verdict visibility_verdict",
    "technical.schema_validate": "valid verdict",
    "technical.schema_generate": "verdict",
    "technical.ai_visibility_audit": "allowed verdict",
    "technical.gbp_deprecation_lint": "issues verdict",
    "technical.pagespeed_audit": "performance_score score verdict",
    "technical._metric": "score",
    "ai_referrals.parse_row": "classification",
    "content_trust.observe_untrusted_content": "assessment flagged",
}


def test_output_signal_changes_require_an_explicit_inventory_review():
    import gsc_mcp
    root = Path(inspect.getfile(gsc_mcp)).parent
    files = [*sorted((root / "tools").glob("*.py")), root / "ai_referrals.py", root / "content_trust.py", root / "page_challenges.py"]
    signals = {"verdict", "visibility_verdict", "status", "rating", "lcp_rating", "score", "overall_quality", "diagnosis", "risk", "site_risk", "severity", "valid", "allowed", "action", "current_focus", "triggered", "category", "opportunities", "conflicts", "drops", "lost_queries", "alerts", "queries", "issues", "question_queries", "assessment", "flagged", "classification"}
    actual = {}
    for file in files:
        tree = ast.parse(file.read_text())
        for fn in (n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))):
            keys = set()
            for node in ast.walk(fn):
                candidates = node.keys if isinstance(node, ast.Dict) else [node.slice] if isinstance(node, ast.Subscript) and isinstance(node.ctx, ast.Store) else []
                for key in candidates:
                    if isinstance(key, ast.Constant) and isinstance(key.value, str) and (key.value in signals or key.value.endswith("_score")):
                        keys.add(key.value)
            if keys:
                actual[f"{file.stem}.{fn.name}"] = keys
    assert actual == {fn: set(keys.split()) for fn, keys in _REVIEWED_SIGNALS.items()}
