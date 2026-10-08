import json
from unittest.mock import patch

import pytest
from google.analytics.data_v1beta.types import RunReportResponse, ResponseMetaData, Row, DimensionValue, MetricValue

from gsc_mcp.tools.ga4 import ga4_organic_landing_pages


@pytest.mark.parametrize("row_count, expected", [(1, True), (12, False)])
def test_landing_report_does_not_claim_truncated_rows_are_complete(row_count, expected):
    response = RunReportResponse(
        row_count=row_count,
        rows=[Row(dimension_values=[DimensionValue(value="/")], metric_values=[MetricValue(value=v) for v in ["0", "0", "0", "0", "0", "0"]])],
        metadata=ResponseMetaData(time_zone="Europe/Paris", subject_to_thresholding=True),
    )
    with patch("gsc_mcp.tools.ga4.get_ga4_service") as get_client:
        get_client.return_value.run_report.return_value = response
        result = json.loads(ga4_organic_landing_pages(property_id="123"))
    assert result["pages"][0]["sessions"] == 0
    assert result["coverage"] == {
        "row_count": row_count, "returned_rows": 1, "complete": expected,
        "data_loss_from_other_row": False, "sampling": False, "subject_to_thresholding": True,
        "empty_reason": None, "metric_restrictions": [],
    }
    assert result["time_zone"] == "Europe/Paris"


def test_landing_report_missing_coverage_stays_unknown():
    from types import SimpleNamespace
    with patch("gsc_mcp.tools.ga4.get_ga4_service") as get_client:
        get_client.return_value.run_report.return_value = SimpleNamespace(rows=[])
        result = json.loads(ga4_organic_landing_pages(property_id="123"))
    assert result["coverage"]["complete"] is None
    assert result["coverage"]["row_count"] is None
    assert result["coverage"]["sampling"] is None
    assert result["coverage"]["subject_to_thresholding"] is None
    assert result["time_zone"] is None
    assert result["coverage"]["metric_restrictions"] is None


def test_landing_report_discloses_empty_reason_and_restricted_metrics():
    response = RunReportResponse(metadata=ResponseMetaData(
        empty_reason="NO_DATA", schema_restriction_response={"active_metric_restrictions": [
            {"metric_name": "totalRevenue", "restricted_metric_types": [1]},
        ]},
    ))
    with patch("gsc_mcp.tools.ga4.get_ga4_service") as get_client:
        get_client.return_value.run_report.return_value = response
        result = json.loads(ga4_organic_landing_pages(property_id="123"))
    assert result["coverage"]["empty_reason"] == "NO_DATA"
    assert result["coverage"]["metric_restrictions"] == [{"metric_name": "totalRevenue", "restricted_metric_types": [1]}]
