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
    "quick_wins": {"opportunities": [{"benchmark_ctr": .03, "expected_clicks_at_benchmark": 3, "opportunity_score": 2}], "skipped_metric_rows": {"ctr_unavailable": 1}},
    "traffic_drops": {
        "drops": [{"diagnosis": "ranking_loss", "diagnosis_status": "candidate", "diagnosis_candidates": ["ranking_loss"],
                   "clicks_delta": -1, "impressions_delta": -2, "position_current": 7, "position_previous": 3,
                   "metrics_previous": {"clicks": 2, "impressions": 10, "ctr": .2, "position": 3},
                   "metrics_current": {"clicks": 1, "impressions": 8, "ctr": .125, "position": 7}}],
        "unavailable_queries": [{"diagnosis": "unknown", "diagnosis_status": "insufficient_evidence", "diagnosis_candidates": [],
                                 "reason": "current_query_not_returned", "metrics_current": None,
                                 "metrics_previous": {"clicks": 588, "impressions": 600, "ctr": .98, "position": 3}}],
    },
    "seo_striking_distance": {"queries": []},
    "seo_cannibalization": {"conflicts": [{"conflict_score": .5, "total_clicks": 2}], "excluded_search_operator_queries": 1},
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
    "editorial_audit": {"verdict": "checked", "assessment": "house_style_review", "findings": [{"rule_id": "stacked_modality", "requires_context_review": True}], "metrics": {"findings_detected": 1}, "findings_truncated": False, "http_status": 200, "challenge": {"provider": "siteground"},
                        "source": {"origin": "caller", "format": "markdown"},
                        "method": {"location_basis": "original_source_span", "coverage": {"parser": "bounded_markdown_subset", "rendered_coordinates": "not_assessed"}},
                        "input_limits": {"max_characters": 100000, "max_blocks": 2000}, "input_truncated": False},
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
for _tool in ("schema_validate", "page_technical_audit", "heading_audit", "internal_links_audit", "editorial_audit"):
    SUCCESS_SHAPES[_tool] = {**SUCCESS_SHAPES[_tool], "untrusted_content": {"flagged": True, "signals": [{"basis": "rule"}]}}


_SOURCE_ANOMALY = {"reason": "clicks_exceed_impressions", "clicks": 3, "impressions": 2, "raw_ratio": 1.5}
_BING_ANOMALOUS_ROW = {"clicks": 3, "impressions": 2, "ctr": None, "position": 5,
                       "avg_click_position": 6, "avg_impression_position": 5,
                       "metric_diagnostics": [_SOURCE_ANOMALY]}
for _tool in ("bing_query_stats", "bing_page_stats", "bing_page_query_stats", "bing_rank_traffic_stats"):
    SUCCESS_SHAPES[_tool] = {"count": 2, "rows": [
        _BING_ANOMALOUS_ROW,
        {"clicks": 0, "impressions": 10, "ctr": None,
         "unavailable_metrics": ["clicks", "ctr"]},
    ]}
SUCCESS_SHAPES["bing_query_stats"].update({
    "aggregation_scope": "query", "row_count": 2, "source_row_count": 2, "local_truncated": False,
    "date_filtering": {"invalid_date_row_count": 0, "out_of_window_row_count": 0},
    "metric_diagnostics": [_SOURCE_ANOMALY],
})
SUCCESS_SHAPES["compare_search_engines"]["rows"][0].update({
    "google": {"present": True, **_BING_ANOMALOUS_ROW, "unavailable_metrics": ["clicks", "ctr"]},
    "bing": {"present": True, **_BING_ANOMALOUS_ROW, "unavailable_metrics": ["clicks", "ctr"]},
})
SUCCESS_SHAPES["compare_search_engines"]["totals"].update({
    "google": {**_BING_ANOMALOUS_ROW, "unavailable_metrics": ["clicks", "ctr"]},
    "bing": {**_BING_ANOMALOUS_ROW, "unavailable_metrics": ["clicks", "ctr"]},
})


_BREAKDOWN_METRICS = {"clicks": 10, "impressions": 100, "ctr": .1, "position": 2}
_BREAKDOWN_COUNTS = {"clicks": 10, "impressions": 100}
SUCCESS_SHAPES["search_change_breakdown"] = {
    "baseline_totals": {"baseline": {"metrics": _BREAKDOWN_METRICS, "availability": "observed", "response_aggregation_type": "byProperty", "fetch_error": None}},
    "baseline_delta": {"clicks": -1}, "baseline_comparison": {"comparable": True, "reason": None},
    "periods": {"baseline": {"coverage_probe_status": "observed", "incompleteness_status": "final_requested", "observed_dates": ["2026-01-01"],
                              "observed_start": "2026-01-01", "observed_end": "2026-01-01", "missing_requested_dates": [], "observed_day_count": 1,
                              "first_incomplete_date": None, "response_aggregation_type": "byProperty", "fetch_error": None}},
    "request_budget": {"requests_made": 6, "max_requests": 20, "exhausted": False},
    "breakdowns": {"query": {"matched": [{"baseline": _BREAKDOWN_METRICS, "comparison": _BREAKDOWN_METRICS, "delta": {"clicks": 0}}],
                             "baseline_only": [{"baseline": _BREAKDOWN_METRICS, "comparison": None, "delta": None}],
                             "comparison_only": [{"baseline": None, "comparison": _BREAKDOWN_METRICS, "delta": None}],
                             "matched_count": 1, "baseline_only_count": 1, "comparison_only_count": 1,
                             "matched_delta": _BREAKDOWN_COUNTS, "observed_sums": {"baseline": _BREAKDOWN_COUNTS},
                             "displayed_counts": {"matched": 1}, "display_truncated": False,
                             "baseline_coverage": {"rows_returned": 1, "pages_fetched": 1, "response_aggregation_type": "byProperty", "response_aggregation_types": ["byProperty"]},
                             "comparison_coverage": {"rows_returned": 1, "pages_fetched": 1, "response_aggregation_type": "byProperty", "response_aggregation_types": ["byProperty"]},
                             "comparison": {"comparable": True, "reason": None},
                             "reconciliation": {"comparable": True, "reason": None, "overcoverage": False, "baseline_residual": _BREAKDOWN_COUNTS,
                                                "comparison_residual": _BREAKDOWN_COUNTS, "total_delta_minus_matched_delta": _BREAKDOWN_COUNTS}}}}

SUCCESS_SHAPES["seo_change_impact"] = {
    "event": {"provenance": "caller_declared"}, "page_mapping": {"provenance": "caller_declared"},
    "windows": {"weekday_aligned": False},
    "maturity_policy": {"lag_days": 3, "latest_eligible_date": "2026-01-20", "provider_finalization_verified": False},
    "comparison": {"status": "observed", "reasons": [],
                   "before": {"clicks": 10, "impressions": 100, "ctr": .1},
                   "after": {"clicks": 12, "impressions": 100, "ctr": .12},
                   "descriptive_delta": {"clicks": 2, "impressions": 0, "ctr_percentage_points": 2}},
    "collection": {"started_at": "2026-01-23T12:00:00+00:00", "completed_at": "2026-01-23T12:00:01+00:00"},
    "attribution": {"causal_effect": None, "status": "not_identified"},
    "search_evidence": copy.deepcopy(SUCCESS_SHAPES["search_change_breakdown"]),
}
# Synthetic provider-shaped labels exercise provenance, not live AI support.
SUCCESS_SHAPES["ai_overviews_impact"] = {
    "source_status": "observed", "count": 1,
    "rows": [{"searchAppearance": "TEST_APPEARANCE", "clicks": 1, "impressions": 10,
              "ctr": .1, "position": 1.0}],
    "ai_exposure": {"status": "unavailable", "verification": "unverified"},
}
SUCCESS_SHAPES["rewrite_fidelity_check"] = {
    "verdict": "compared", "assessment": "mechanical_comparison_only",
    "findings": [{"category": "number", "operation": "changed", "context_review_required": True}],
    "findings_truncated": False, "analysis_truncated": False,
    "counts": {"original_occurrences_checked": 1, "revised_occurrences_checked": 1,
               "findings_detected": 1, "findings_returned": 1},
    "semantic_assessment": {"fidelity": "unassessed", "factual_truth": "unassessed", "scope": "unassessed", "causality": "unassessed"},
}
# Null search_evidence is a distinct actual output branch, rather than a success
# shape with contradictory provider data. The real-call tests exercise both.
DEGRADED_SHAPES = {
    "ai_overviews_impact": {"error": "AI_OVERVIEWS_NOT_AVAILABLE", "http_status": 403,
                            "source_status": "access_denied", "error_meaning": "access_denied",
                            "ai_exposure": {"status": "unavailable", "verification": "unverified"}},
    "seo_change_impact": {"comparison": {"status": "unavailable", "reasons": ["insufficient_post_change_data"],
                                        "before": None, "after": None,
                                        "descriptive_delta": {"clicks": None, "impressions": None, "ctr_percentage_points": None}},
                          "search_evidence": None},
}


_LINK_OBSERVATION = {
    "status_code": 404, "last_observed_status": 404, "attempted": True,
    "started_at": "2026-01-01T00:00:00+00:00", "completed_at": "2026-01-01T00:00:01+00:00", "elapsed_ms": 1000,
    "outcome": "observed", "availability_reason": None,
    "hops": [{"status_code": 404, "observed_at": "2026-01-01T00:00:01+00:00", "elapsed_ms": 1000}],
}
SUCCESS_SHAPES["link_targets_audit"] = {
    "collected_at": "2026-01-01T00:00:01+00:00", "source_body_complete": True,
    "source_observation": {**_LINK_OBSERVATION, "status_code": 200, "body_complete": True},
    "scope_policy": "same_site_www_alias_default_ports", "coverage": "complete", "targets": [
        {**_LINK_OBSERVATION, "findings": ["http_not_found"], "source_links": [{"anchor": "Text", "zone": "body"}]}],
    "total_anchors": 1, "distinct_in_scope_targets": 1, "targets_attempted": 1, "targets_completed": 1, "targets_skipped": 0,
    "excluded_reasons": {"external": 1},
    "budgets": {"max_targets": 30, "max_requests": 60, "requests_started": 2, "dns_refusals": 0, "max_redirects": 5,
                "request_timeout_seconds": 10, "scheduling_deadline_seconds": 60, "source_max_body_bytes": 1048576,
                "target_max_body_bytes": 0, "elapsed_ms": 1000, "deadline_overrun": False},
    "untrusted_content": {"flagged": True, "signals": [{"basis": "rule"}]},
}


def test_link_destination_evidence_separates_received_status_from_unavailable_target():
    records = fields("link_targets_audit", SUCCESS_SHAPES["link_targets_audit"])
    assert_basis(records, "/targets/0/status_code", "measured", "observed")
    assert_basis(records, "/source_observation/hops/0/status_code", "measured", "observed")
    assert_basis(records, "/source_body_complete", "measured", "observed")


    assert_basis(records, "/budgets/requests_started", "measured", "observed")
    assert_basis(records, "/targets_completed", "derived", "calculated")
    assert_basis(records, "/targets/0/findings", "rule", "heuristic")
    assert_basis(records, "/coverage", "rule", "heuristic")
    assert "/targets/0/source_links/0/anchor" not in records
    unavailable = {"coverage": "partial", "targets": [{**_LINK_OBSERVATION, "status_code": None,
                   "outcome": "unavailable", "availability_reason": "timeout", "last_observed_status": 301}]}
    records = fields("link_targets_audit", unavailable)
    assert_basis(records, "/targets/0/status_code", None, "unavailable")
    assert_basis(records, "/targets/0/last_observed_status", "measured", "observed")
    assert_basis(records, "/targets/0/availability_reason", "rule", "heuristic")
    source_unavailable = {"coverage": "unavailable", "source_body_complete": False, "targets_completed": 0,
                          "total_anchors": 0, "distinct_in_scope_targets": 0, "targets_attempted": 0, "targets_skipped": 0}
    records = fields("link_targets_audit", source_unavailable)
    assert_basis(records, "/total_anchors", None, "unavailable")
    assert_basis(records, "/targets_completed", None, "unavailable")
    assert_basis(records, "/source_body_complete", "measured", "observed")


def test_search_breakdown_row_sum_and_residual_scopes_name_their_actual_formulas():
    data = {"breakdowns": {"query": {"observed_sums": {"baseline": {"clicks": 10, "impressions": None}},
             "reconciliation": {"baseline_residual": {"clicks": 5}, "total_delta_minus_matched_delta": {"clicks": 2}}}}}
    records = fields("search_change_breakdown", data)
    assert_basis(records, "/breakdowns/query/observed_sums/baseline/clicks", "derived", "calculated")
    assert records["/breakdowns/query/observed_sums/baseline/clicks"]["scope"] == (
        "Sum over retrieved valid per-period rows; not property totals; null when rows are empty or any required metric is missing")
    assert_basis(records, "/breakdowns/query/observed_sums/baseline/impressions", None, "unavailable")
    assert records["/breakdowns/query/reconciliation/baseline_residual/clicks"]["scope"] == (
        "Reported period aggregate minus retrieved period row sum, only on compatible known aggregation; descriptive residual, not a cause")
    assert records["/breakdowns/query/reconciliation/total_delta_minus_matched_delta/clicks"]["scope"] == (
        "Reported total change minus summed matched-row changes, only on compatible known aggregation; descriptive residual, not a cause")


@pytest.mark.parametrize("missing_followup", [False, True])
def test_real_change_impact_preserves_nested_metric_and_missing_row_provenance(monkeypatch, missing_followup):
    from types import SimpleNamespace
    from gsc_mcp.tools import change_impact, search_breakdown

    def query(siteUrl, body):
        before = body["startDate"] == "2020-01-01"
        dimension = body.get("dimensions", [None])[0]
        key = (body["startDate"] if dimension == "date" else
               "baseline-query" if dimension == "query" and before else
               "comparison-query" if dimension == "query" else
               "https://example.com/article" if dimension == "page" else dimension)
        row = {"keys": [] if key is None else [key], "clicks": 10 if before else 12,
               "impressions": 100, "ctr": .8, "position": 2}
        rows = [] if missing_followup and not before and dimension is None else [row]
        return SimpleNamespace(execute=lambda: {"rows": rows, "responseAggregationType": "byPage"})

    service = SimpleNamespace(searchanalytics=lambda: SimpleNamespace(query=query))
    monkeypatch.setattr(search_breakdown, "get_searchconsole_service", lambda: service)
    event = {"site": "sc-domain:example.com", "url": "https://example.com/article",
             "changed_at": "2020-01-08T12:00:00-08:00", "timezone": "America/Los_Angeles",
             "description": "Caller reports a heading change."}
    result = json.loads(change_impact.seo_change_impact(event, "2020-01-01", "2020-01-01",
                                                      "2020-01-09", "2020-01-09"))
    records = result["_meta"]["evidence"]["fields"]
    nested_records = result["search_evidence"]["_meta"]["evidence"]["fields"]
    assert result["comparison"]["before"]["ctr"] == .1
    assert_basis(records, "/event/provenance", "rule", "heuristic")
    assert_basis(records, "/comparison/before/clicks", "measured", "observed")
    assert_basis(records, "/comparison/before/ctr", "derived", "calculated")
    assert_basis(records, "/attribution/causal_effect", None, "unavailable")
    assert_basis(records, "/maturity_policy/provider_finalization_verified", "rule", "heuristic")
    for pointer, basis, tier in [
        ("/baseline_totals/baseline/metrics/clicks", "measured", "observed"),
        ("/baseline_totals/baseline/metrics/ctr", "derived", "calculated"),
        ("/periods/baseline/observed_dates", "measured", "observed"),
        ("/breakdowns/query/baseline_only/0/baseline/clicks", "measured", "observed"),
        ("/breakdowns/query/baseline_only/0/comparison", None, "unavailable"),
        ("/breakdowns/query/baseline_only/0/delta", None, "unavailable"),
        ("/breakdowns/query/comparison_only/0/baseline", None, "unavailable"),
    ]:
        assert_basis(records, "/search_evidence" + pointer, basis, tier)
        assert records["/search_evidence" + pointer] == nested_records[pointer]
    assert "/search_evidence" not in records
    assert not any("/_meta/" in pointer for pointer in records)
    if missing_followup:
        assert result["comparison"]["status"] == "unavailable"
        assert result["comparison"]["after"]["clicks"] is None
        assert_basis(records, "/comparison/status", None, "unavailable")
        assert_basis(records, "/comparison/after/clicks", None, "unavailable")
        assert_basis(records, "/comparison/descriptive_delta/clicks", None, "unavailable")
        assert_basis(records, "/search_evidence/baseline_totals/comparison/availability", None, "unavailable")
    else:
        assert result["comparison"]["status"] == "observed"
        assert result["comparison"]["descriptive_delta"]["clicks"] == 2
        assert_basis(records, "/comparison/status", "rule", "heuristic")
        assert_basis(records, "/comparison/descriptive_delta/clicks", "derived", "calculated")


def test_real_draft_editorial_evidence_describes_parser_limits_and_caller_provenance():
    from gsc_mcp.tools.editorial import editorial_audit
    result = json.loads(editorial_audit(text="It may potentially help.", language="en", format="markdown"))
    records = result["_meta"]["evidence"]["fields"]
    assert result["source"]["origin"] == "caller"
    assert result["method"]["coverage"]["parser"] == "bounded_markdown_subset"
    assert_basis(records, "/source/origin", "rule", "heuristic")
    assert_basis(records, "/method/coverage", "rule", "heuristic")
    assert_basis(records, "/method/location_basis", "rule", "heuristic")
    assert_basis(records, "/input_limits/max_characters", "rule", "heuristic")
    assert_basis(records, "/metrics/findings_detected", "derived", "calculated")
    assert_basis(records, "/http_status", None, "unavailable")
    assert "/coverage" not in records


@pytest.mark.parametrize("options", [
    {"original": ""}, {"revised": None}, {"original": "x" * 20001},
    {"language": "de"}, {"format": "html"},
])
def test_real_rewrite_invalid_input_never_labels_placeholder_zero_findings_as_assessed(options):
    from gsc_mcp.tools.rewrite import rewrite_fidelity_check
    params = {"original": "The rate is 10%.", "revised": "The rate is 12%."}
    params.update(options)
    result = json.loads(rewrite_fidelity_check(**params))
    assert result["verdict"] == "invalid_input"
    assert result["assessment"] == "not_assessed"
    assert result["findings"] is None
    assert "counts" not in result
    assert set(result["semantic_assessment"].values()) == {"unassessed"}
    records = result["_meta"]["evidence"]["fields"]
    for pointer in ("/verdict", "/assessment", "/findings", "/findings_truncated", "/analysis_truncated", "/error"):
        assert_basis(records, pointer, None, "unavailable")
    for dimension in ("fidelity", "factual_truth", "scope", "causality"):
        assert_basis(records, "/semantic_assessment/" + dimension, None, "unavailable")


def test_real_rewrite_mechanical_counts_do_not_certify_semantics():
    from gsc_mcp.tools.rewrite import rewrite_fidelity_check
    result = json.loads(rewrite_fidelity_check("The rate is 10%.", "The rate is 12%."))
    assert result["assessment"] == "mechanical_comparison_only"
    assert result["counts"]["findings_detected"] == 1
    records = result["_meta"]["evidence"]["fields"]
    assert_basis(records, "/findings/0/category", "rule", "heuristic")
    assert_basis(records, "/findings/0/context_review_required", "rule", "heuristic")
    assert_basis(records, "/counts/findings_detected", "derived", "calculated")
    assert_basis(records, "/semantic_assessment/factual_truth", None, "unavailable")


def test_all_applicable_tools_and_declarations_have_exercised_success_or_degraded_shapes():
    from gsc_mcp.evidence import INVENTORY, _PATHS
    applicable = {tool for tool, entry in INVENTORY.items() if entry["applicability"] == "fields"}
    assert applicable <= set(SUCCESS_SHAPES)
    for tool in INVENTORY:
        fixtures = [SUCCESS_SHAPES.get(tool, {}), DEGRADED_SHAPES.get(tool, {}),
                    {"error": "failure", "verdict": "fetch_error", "indexed": False}]
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
    "analytics.ai_overviews_impact": "status",
    "analytics.analytics_anomalies": "z_score",
    "bing_webmaster._feed_row": "status",
    "bing_webmaster._mutation_response": "status",
    "bing_webmaster.bing_crawl_issues": "issues",
    "bing_webmaster.bing_feed_remove": "status",
    "editorial.editorial_audit": "assessment",
    "editorial.analyze_html": "assessment verdict",
    "editorial_drafts.analyze_draft": "assessment",
    "change_impact.seo_change_impact": "status",
    "rewrite._compare": "category",
    "rewrite.finding": "category",
    "rewrite.rewrite_fidelity_check": "assessment verdict",
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
    "link_targets.link_targets_audit": "coverage",
    "seo._unsupported_bing": "verdict",
    "seo.quick_wins": "opportunities opportunity_score skipped_metric_rows",
    "seo.traffic_drops": "diagnosis drops diagnosis_status diagnosis_candidates metrics_current metrics_previous unavailable_queries",
    "seo.seo_striking_distance": "queries",
    "seo.seo_cannibalization": "conflict_score conflicts excluded_search_operator_queries",
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
    "bing_analytics._position_stats": "aggregation_scope date_filtering local_truncated metric_diagnostics row_count source_row_count",
    "search_compare._aggregate_rows": "metric_diagnostics unavailable_metrics",
    "search_compare._totals": "metric_diagnostics unavailable_metrics",
    "search_compare.compare_search_engines": "row_count",
    "bing.bing_ctr_metrics": "metric_diagnostics",
    "bing.bing_row_ctr_metrics": "unavailable_metrics",
    "bing._aggregate_dates": "metric_diagnostics unavailable_metrics",
    "bing._aggregate_positions": "metric_diagnostics unavailable_metrics",
    # Provider row_count in GA4's existing data-only coverage metadata is a
    # reviewed scan inclusion, not a new field-level quality descriptor.
    "ga4._report_coverage": "row_count",
    # Existing search-breakdown null/count availability handling was reviewed
    # already; its named missing-input list is now included in the tripwire.
    "search_breakdown._metrics": "unavailable_metrics",
}


def test_output_signal_changes_require_an_explicit_inventory_review():
    import gsc_mcp
    root = Path(inspect.getfile(gsc_mcp)).parent
    files = [*sorted((root / "tools").glob("*.py")), root / "ai_referrals.py", root / "content_trust.py", root / "page_challenges.py", root / "editorial.py", root / "providers" / "bing.py"]
    signals = {"verdict", "visibility_verdict", "status", "rating", "lcp_rating", "score", "overall_quality", "diagnosis", "risk", "site_risk", "severity", "valid", "allowed", "action", "current_focus", "triggered", "category", "opportunities", "conflicts", "drops", "lost_queries", "alerts", "queries", "issues", "question_queries", "assessment", "flagged", "classification",
               "diagnosis_status", "diagnosis_candidates", "metrics_current", "metrics_previous", "unavailable_queries",
               "excluded_search_operator_queries", "skipped_metric_rows", "metric_diagnostics", "unavailable_metrics", "aggregation_scope",
               "source_row_count", "row_count", "local_truncated", "date_filtering"}
    actual = {}
    for file in files:
        tree = ast.parse(file.read_text())
        for fn in (n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))):
            keys = set()
            for node in ast.walk(fn):
                candidates = node.keys if isinstance(node, ast.Dict) else [node.slice] if isinstance(node, ast.Subscript) and isinstance(node.ctx, ast.Store) else []
                for key in candidates:
                    if isinstance(key, ast.Constant) and isinstance(key.value, str) and (key.value in signals or key.value.endswith("_score") or (file.stem == "link_targets" and key.value == "coverage")):
                        keys.add(key.value)
            if keys:
                actual[f"{file.stem}.{fn.name}"] = keys
    assert actual == {fn: set(keys.split()) for fn, keys in _REVIEWED_SIGNALS.items()}


def test_editorial_evidence_keeps_rule_warnings_counts_and_unassessed_states_separate():
    checked = {"verdict": "checked", "assessment": "house_style_review", "http_status": 200,
               "findings": [{"rule_id": "stacked_modality", "requires_context_review": True}],
               "metrics": {"findings_detected": 1}, "findings_truncated": False}
    records = fields("editorial_audit", checked)
    assert_basis(records, "/findings/0/rule_id", "rule", "heuristic")
    assert_basis(records, "/findings", "rule", "heuristic")
    assert_basis(records, "/metrics/findings_detected", "derived", "calculated")
    assert_basis(records, "/http_status", "measured", "observed")
    for verdict in ("invalid_input", "fetch_error", "challenge_page", "language_unavailable", "unsupported_language", "empty_content"):
        records = fields("editorial_audit", {"verdict": verdict, "assessment": "not_assessed",
                         "http_status": 200, "findings": None, "metrics": None, "findings_truncated": False})
        assert_basis(records, "/verdict", None, "unavailable")
        assert_basis(records, "/findings", None, "unavailable")
        assert_basis(records, "/findings_truncated", None, "unavailable")
        assert_basis(records, "/http_status", "measured", "observed")
