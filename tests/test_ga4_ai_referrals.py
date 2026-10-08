"""Recorded assistant source attribution is bounded and never citation evidence."""

import json
from unittest.mock import MagicMock

import pytest
from google.analytics.data_v1beta.types import (
    CheckCompatibilityResponse, Compatibility, DimensionCompatibility, DimensionMetadata,
    MetricCompatibility, MetricMetadata, ResponseMetaData, Row, RunReportResponse, SamplingMetadata,
)
from google.api_core.exceptions import ResourceExhausted

from gsc_mcp.tools import ga4


DIMENSIONS = ["sessionSource", "sessionMedium", "landingPagePlusQueryString"]
METRICS = ["sessions", "engagedSessions", "keyEvents"]


def compatibility(value=Compatibility.COMPATIBLE):
    return CheckCompatibilityResponse(
        dimension_compatibilities=[DimensionCompatibility(dimension_metadata=DimensionMetadata(api_name=name), compatibility=value) for name in DIMENSIONS],
        metric_compatibilities=[MetricCompatibility(metric_metadata=MetricMetadata(api_name=name), compatibility=value) for name in METRICS],
    )


def row(source, sessions=10, engaged=5, events=1, page="/", medium="referral"):
    return Row(dimension_values=[{"value": source}, {"value": medium}, {"value": page}],
               metric_values=[{"value": str(value)} for value in (sessions, engaged, events)])


def response(rows, count=None, **metadata):
    return RunReportResponse(rows=rows, row_count=len(rows) if count is None else count,
                             metadata=ResponseMetaData(time_zone="Europe/Paris", **metadata))


@pytest.fixture
def client(monkeypatch):
    service = MagicMock()
    service.check_compatibility.return_value = compatibility()
    service.run_report.return_value = response([row("chatgpt.com")])
    monkeypatch.setenv("GA4_PROPERTY_ID", "123456789")
    monkeypatch.setattr(ga4, "get_ga4_service", lambda: service)
    return service


def run(**kwargs):
    return json.loads(ga4.ga4_ai_referrals("2026-09-01", "2026-09-28", **kwargs))


def test_exact_source_rules_keep_candidates_and_spoof_names_out_of_confirmed_totals(client):
    client.run_report.return_value = response([
        row("chatgpt.com", 3, 2, 1, "/article"), row("perplexity.ai", 2),
        row("google", 5), row("chatgpt.com.evil.test", 7), row("mychatgpt.com", 11),
        row("cool-ai-gpt-llm.test", 13), row("claude.ai", 17),
    ])
    result = run()
    assert result["confirmed_totals"] == {"sessions": 3, "engaged_sessions": 2, "key_events": 1.0, "conversions": 1.0}
    assert result["candidate_totals"]["sessions"] == 19
    assert result["total_sessions"] == 58
    assert result["ai_session_share"] == pytest.approx(3 / 58)
    assert [r["source"] for r in result["rows"] if r["classification"] == "confirmed"] == ["chatgpt.com"]
    assert result["assistants"][0]["landing_pages"][0]["landing_page"] == "/article"


def test_check_and_report_use_identical_property_dimensions_metrics_and_hostname(client):
    result = run(property_id="properties/987654321", hostname="blog.example.com")
    check = client.check_compatibility.call_args.args[0]
    report = client.run_report.call_args.args[0]
    assert check.property == report.property == "properties/987654321"
    assert [d.name for d in check.dimensions] == [d.name for d in report.dimensions] == DIMENSIONS
    assert [m.name for m in check.metrics] == [m.name for m in report.metrics] == METRICS
    assert check.dimension_filter == report.dimension_filter
    assert report.dimension_filter.filter.field_name == "hostName"
    assert report.dimension_filter.filter.string_filter.value == "blog.example.com"
    assert report.limit == 10000
    assert (report.date_ranges[0].start_date, report.date_ranges[0].end_date) == ("2026-09-01", "2026-09-28")
    assert result["_meta"]["sources"] == {"ga4": {"property": "properties/987654321"}}
    assert result["source_data"]["ga4"]["requested_window"] == {"start": "2026-09-01", "end": "2026-09-28"}
    assert result["source_data"]["ga4"]["filters"] == {"hostname": "blog.example.com"}
    assert result["time_zone"] == "Europe/Paris"


@pytest.mark.parametrize("rows,availability,total,confirmed,share_reason", [
    ([], "empty", None, None, "empty_source"),
    ([row("chatgpt.com", 0, 0, 0)], "measured", 0, 0, "zero_denominator"),
    ([row("google", 10)], "measured", 10, 0, None),
])
def test_empty_explicit_zero_and_no_confirmed_sources_are_distinct(client, rows, availability, total, confirmed, share_reason):
    client.run_report.return_value = response(rows)
    result = run()
    assert result["availability"] == availability
    assert result["total_sessions"] == total
    assert (result["confirmed_totals"]["sessions"] if result["confirmed_totals"] else None) == confirmed
    assert result["share_reason"] == share_reason
    assert result["ai_session_share"] == (0 if share_reason is None else None)


@pytest.mark.parametrize("metadata", [
    {"data_loss_from_other_row": True}, {"subject_to_thresholding": True},
    {"sampling_metadatas": [SamplingMetadata(samples_read_count=2, sampling_space_size=10)]},
    {"schema_restriction_response": {"active_metric_restrictions": [{"metric_name": "keyEvents", "restricted_metric_types": [1]}]}},
])
def test_restricted_report_keeps_observed_counts_but_not_denominator_or_share(client, metadata):
    client.run_report.return_value = response([row("chatgpt.com", 3)], **metadata)
    result = run()
    assert result["confirmed_totals"]["sessions"] == 3
    assert result["total_sessions"] is None
    assert result["ai_session_share"] is None
    assert result["share_reason"] == "incomplete_coverage"


def test_truncation_prevents_share_even_when_numerator_rows_exist(client):
    client.run_report.return_value = response([row("chatgpt.com", 3)], count=10001)
    result = run()
    assert result["coverage"]["complete"] is False
    assert result["confirmed_totals"]["sessions"] == 3
    assert result["total_sessions"] is None
    assert result["ai_session_share"] is None


@pytest.mark.parametrize("checked", [compatibility(Compatibility.INCOMPATIBLE), CheckCompatibilityResponse()])
def test_unverified_or_incompatible_dimensions_stop_before_report(client, checked):
    client.check_compatibility.return_value = checked
    result = run()
    assert result["availability"] == "unavailable"
    assert result["reason"] == "incompatible_or_unknown_api_fields"
    assert result["ai_session_share"] is None
    client.run_report.assert_not_called()


@pytest.mark.parametrize("method", ["check_compatibility", "run_report"])
def test_upstream_failure_returns_unavailable_without_invented_zero(client, method):
    getattr(client, method).side_effect = OSError("upstream error with private diagnostics")
    result = run()
    assert result["availability"] == "unavailable"
    assert result["reason"] == "upstream_error"
    assert result["confirmed_totals"] is None
    assert result["total_sessions"] is None
    assert "private diagnostics" not in json.dumps(result)


def test_missing_configuration_is_distinct_from_upstream_failure(client, monkeypatch):
    monkeypatch.delenv("GA4_PROPERTY_ID")
    result = run()
    assert result["availability"] == "unavailable"
    assert result["reason"] == "configuration_error"
    assert result["_meta"]["sources"] == {"ga4": {"property": None}}


@pytest.mark.parametrize("dates", [("28daysAgo", "today"), ("2026-09-28", "2026-09-01"), ("2026-02-30", "2026-09-01")])
def test_bad_dates_are_rejected_before_auth(client, monkeypatch, dates):
    monkeypatch.setattr(ga4, "get_ga4_property_id", lambda **kw: pytest.fail("invalid dates reached auth"))
    with pytest.raises(ValueError):
        ga4.ga4_ai_referrals(*dates)


@pytest.mark.parametrize("method", ["check_compatibility", "run_report"])
def test_transient_requests_retry_before_error_is_reported(client, monkeypatch, method):
    monkeypatch.setattr("gsc_mcp.retry.time.sleep", lambda delay: None)
    getattr(client, method).side_effect = [ResourceExhausted("quota temporarily exhausted"), compatibility() if method == "check_compatibility" else response([row("chatgpt.com")])]
    result = run()
    assert result["availability"] == "measured"
    assert getattr(client, method).call_count == 2


def test_unrequested_comparison_is_explicitly_unavailable_and_rules_are_sourced(client):
    result = run()
    assert result["comparison"] == {"availability": "unavailable", "reason": "not_requested"}
    assert result["matching_rules"]["verified_on"] == "2026-10-08"
    assert result["matching_rules"]["confirmed"]["chatgpt.com"]["documentation"] == "https://help.openai.com/en/articles/12627856-publishers-and-developers-faq"
    assert result["metric_mapping"]["conversions"] == "keyEvents"
    assert result["limitations"]


def test_tool_is_registered_and_advertised():
    from gsc_mcp.registry import TOOLS
    from gsc_mcp.tools.properties import get_capabilities
    assert "ga4_ai_referrals" in TOOLS
    assert "ga4_ai_referrals" in json.loads(get_capabilities())["tools"]


@pytest.mark.parametrize("source,wanted", [
    (" ChatGPT.com ", "confirmed"), ("www.chatgpt.com", "unmatched"),
    ("https://chatgpt.com", "unmatched"), ("perplexity.ai.evil.test", "unmatched"),
    ("gemini.google.com", "candidate"), ("copilot.microsoft.com", "candidate"),
])
def test_normalization_does_not_expand_the_exact_allowlist(client, source, wanted):
    client.run_report.return_value = response([row(source)])
    result = run()
    assert result["rows"][0]["classification"] == wanted
    assert result["confirmed_totals"]["sessions"] == (10 if wanted == "confirmed" else 0)


@pytest.mark.parametrize("measurement", ["invalid", "-1", "NaN"])
def test_malformed_numeric_metrics_remain_unknown(client, measurement):
    client.run_report.return_value = response([row("chatgpt.com", events=measurement)])
    result = run()
    assert result["availability"] == "unknown"
    assert result["confirmed_totals"] is None
    assert result["ai_session_share"] is None


def test_effective_property_is_not_reresolved_after_client_setup(client, monkeypatch):
    def configured_client():
        monkeypatch.setenv("GA4_PROPERTY_ID", "777777777")
        return client
    monkeypatch.setattr(ga4, "get_ga4_service", configured_client)
    result = run()
    assert client.check_compatibility.call_args.args[0].property == "properties/123456789"
    assert client.run_report.call_args.args[0].property == "properties/123456789"
    assert result["_meta"]["sources"]["ga4"]["property"] == "properties/123456789"
