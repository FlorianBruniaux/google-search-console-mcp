"""Mocked API fixtures verify local contracts, never live AI appearance support."""

import json
from unittest.mock import patch

import httplib2
import pytest
from googleapiclient.errors import HttpError

from gsc_mcp.tools.analytics import ai_overviews_impact

SITE = "https://example.com/"


def test_generic_appearance_rows_preserve_metrics_order_and_do_not_claim_ai_exposure(mock_gsc_service):
    # Synthetic provider-shaped fixture: these labels are not an AI mapping.
    mock_gsc_service.searchanalytics.return_value.query.return_value.execute.return_value = {
        "rows": [
            {"keys": ["TEST_APPEARANCE_A"], "clicks": 9, "impressions": 100,
             "ctr": .09, "position": 4.2},
            {"keys": ["TEST_APPEARANCE_B"], "clicks": 2, "impressions": 300,
             "ctr": .0067, "position": 1.5},
        ]}
    with patch("gsc_mcp.tools.analytics.get_searchconsole_service", return_value=mock_gsc_service):
        result = json.loads(ai_overviews_impact(SITE, days=14, limit=1))
    assert result["rows"] == [{"searchAppearance": "TEST_APPEARANCE_B", "clicks": 2,
                               "impressions": 300, "ctr": .0067, "position": 1.5}]
    assert result["count"] == 1
    assert result["source_status"] == "observed"
    assert result["source_scope"] == "web_search_appearance"
    assert result["ai_exposure"] == {"status": "unavailable", "verification": "unverified"}
    assert result["evidence_limits"]
    body = mock_gsc_service.searchanalytics.return_value.query.call_args.kwargs["body"]
    assert body["dimensions"] == ["searchAppearance"]
    assert body["type"] == "web"
    assert "dimensionFilterGroups" not in body
    assert result["_meta"]["params"] == {"site": SITE, "days": 14, "limit": 1}
    records = result["_meta"]["evidence"]["fields"]
    assert records["/ai_exposure/status"]["confidence_tier"] == "unavailable"
    assert records["/rows/0/impressions"]["basis"] == "measured"
    assert records["/count"]["basis"] == "derived"


def test_empty_success_is_empty_generic_data_with_ai_exposure_unknown(mock_gsc_service):
    mock_gsc_service.searchanalytics.return_value.query.return_value.execute.return_value = {}
    with patch("gsc_mcp.tools.analytics.get_searchconsole_service", return_value=mock_gsc_service):
        result = json.loads(ai_overviews_impact(SITE))
    assert result["rows"] == []
    assert result["count"] == 0
    assert result["source_status"] == "empty"
    assert result["ai_exposure"] == {"status": "unavailable", "verification": "unverified"}
    assert "error" not in result


@pytest.mark.parametrize("status,expected", [
    (400, "invalid_or_unsupported_request"),
    (403, "access_denied"),
])
def test_request_errors_do_not_infer_property_ai_capability(mock_gsc_service, status, expected):
    response = httplib2.Response({"status": str(status)})
    mock_gsc_service.searchanalytics.return_value.query.return_value.execute.side_effect = HttpError(
        response, b'{"error":{"message":"Synthetic request failure"}}')
    with patch("gsc_mcp.tools.analytics.get_searchconsole_service", return_value=mock_gsc_service):
        result = json.loads(ai_overviews_impact(SITE))
    assert result["error"] == "AI_OVERVIEWS_NOT_AVAILABLE"  # Legacy compatibility only.
    assert result["reason"]
    assert result["http_status"] == status
    assert result["source_status"] == expected
    assert result["error_meaning"] == expected
    assert result["ai_exposure"] == {"status": "unavailable", "verification": "unverified"}
    assert result["_meta"]["evidence"]["fields"]["/ai_exposure/status"]["basis"] is None


def test_ai_named_synthetic_label_is_retained_without_provider_identification(mock_gsc_service):
    # Deliberately invented AI-looking label; existence in a mock proves no capability.
    mock_gsc_service.searchanalytics.return_value.query.return_value.execute.return_value = {
        "rows": [{"keys": ["AI_OVERVIEW"], "clicks": 1, "impressions": 10,
                  "ctr": .1, "position": 1.0}]}
    with patch("gsc_mcp.tools.analytics.get_searchconsole_service", return_value=mock_gsc_service):
        result = json.loads(ai_overviews_impact(SITE))
    assert result["rows"][0]["searchAppearance"] == "AI_OVERVIEW"
    assert result["ai_exposure"]["status"] == "unavailable"
    assert result["ai_exposure"]["verification"] == "unverified"


def test_ai_exposure_evidence_separates_generic_counts_from_unavailable_ai_measurement():
    from gsc_mcp.meta import with_meta
    data = {"source_status": "observed", "count": 1,
            "rows": [{"searchAppearance": "TEST_APPEARANCE", "clicks": 1, "impressions": 10,
                      "ctr": .1, "position": 1.0}],
            "ai_exposure": {"status": "unavailable", "verification": "unverified"}}
    records = with_meta(data, "ai_overviews_impact", {})["_meta"]["evidence"]["fields"]
    assert records["/source_status"]["basis"] == "rule"
    assert records["/count"]["confidence_tier"] == "calculated"
    assert records["/ai_exposure/status"]["basis"] is None
    assert records["/ai_exposure/verification"]["basis"] is None
    assert records["/rows/0/searchAppearance"]["basis"] == "measured"


def test_parser_default_metrics_do_not_become_measured_ai_or_generic_traffic(mock_gsc_service):
    mock_gsc_service.searchanalytics.return_value.query.return_value.execute.return_value = {
        "rows": [{"keys": ["TEST_APPEARANCE"]}]}
    with patch("gsc_mcp.tools.analytics.get_searchconsole_service", return_value=mock_gsc_service):
        result = json.loads(ai_overviews_impact(SITE))
    assert result["rows"][0]["impressions"] is None
    assert result["source_status"] == "partial"
    records = result["_meta"]["evidence"]["fields"]
    for key in ("clicks", "impressions", "ctr", "position"):
        assert records[f"/rows/0/{key}"]["basis"] is None


def test_explicit_zero_and_masked_null_have_distinct_provider_origin(mock_gsc_service):
    mock_gsc_service.searchanalytics.return_value.query.return_value.execute.return_value = {
        'rows': [{'keys': ['TEST'], 'clicks': 0, 'impressions': 0, 'ctr': None, 'position': 0}]}
    with patch('gsc_mcp.tools.analytics.get_searchconsole_service', return_value=mock_gsc_service):
        result = json.loads(ai_overviews_impact(SITE))
    row = result['rows'][0]
    assert row['clicks'] == 0 and row['impressions'] == 0 and row['ctr'] is None
    assert row['unavailable_metrics'] == {'ctr': 'null_provider_value'}
    fields = result['_meta']['evidence']['fields']
    assert fields['/rows/0/clicks']['basis'] == 'measured'
    assert fields['/rows/0/ctr']['basis'] is None
    assert result['_meta']['sources']['google']['site'] == SITE
    assert result['coverage']['observed_window'] is None
    assert result['date_range']['start'] <= result['date_range']['end']


def test_missing_dimension_and_invalid_metrics_are_partial_not_ai_absence(mock_gsc_service):
    mock_gsc_service.searchanalytics.return_value.query.return_value.execute.return_value = {
        'rows': [{'clicks': 1, 'impressions': None, 'ctr': 'masked', 'position': float('nan')}]}
    with patch('gsc_mcp.tools.analytics.get_searchconsole_service', return_value=mock_gsc_service):
        result = json.loads(ai_overviews_impact(SITE))
    assert result['source_status'] == 'partial'
    assert result['rows'][0]['searchAppearance'] is None
    assert result['rows'][0]['position'] is None
    assert result['ai_exposure']['status'] == 'unavailable'


@pytest.mark.parametrize('arguments', [{'days': 0}, {'days': True}, {'limit': 0}, {'limit': -1}])
def test_invalid_bounds_fail_before_access(arguments):
    with patch('gsc_mcp.tools.analytics.get_searchconsole_service') as service:
        with pytest.raises(ValueError):
            ai_overviews_impact(SITE, **arguments)
        service.assert_not_called()


@pytest.mark.parametrize('response', [None, {'rows': None}, {'rows': 'unavailable'}])
def test_malformed_container_preserves_failure_and_unknown_exposure(mock_gsc_service, response):
    mock_gsc_service.searchanalytics.return_value.query.return_value.execute.return_value = response
    with patch('gsc_mcp.tools.analytics.get_searchconsole_service', return_value=mock_gsc_service):
        result = json.loads(ai_overviews_impact(SITE))
    assert result['source_status'] == 'malformed_response'
    assert result['error'] == 'INVALID_SEARCH_APPEARANCE_RESPONSE'
    assert result['ai_exposure']['status'] == 'unavailable'
    assert result['_meta']['sources']['google']['site'] == SITE
