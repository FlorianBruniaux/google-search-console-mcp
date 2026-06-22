import json
import pytest
from unittest.mock import patch, call

from tests.conftest import _make_ga4_row, _make_ga4_response, _make_ga4_batch_response
from gsc_mcp.tools.ga4 import (
    ga4_organic_landing_pages,
    ga4_traffic_sources,
    ga4_page_performance,
    ga4_realtime,
    ga4_user_behavior,
    ga4_conversion_funnel,
)

PROP = "123456789"
PROP_FULL = f"properties/{PROP}"


@pytest.fixture(autouse=True)
def _set_ga4_property(monkeypatch):
    monkeypatch.setenv("GA4_PROPERTY_ID", PROP)


# ---------------------------------------------------------------------------
# get_ga4_property_id helpers
# ---------------------------------------------------------------------------

def test_get_ga4_property_id_no_env_var(monkeypatch):
    monkeypatch.delenv("GA4_PROPERTY_ID", raising=False)
    from gsc_mcp.auth import get_ga4_property_id
    with pytest.raises(RuntimeError, match="GA4_PROPERTY_ID"):
        get_ga4_property_id()


def test_get_ga4_property_id_plain_number(monkeypatch):
    monkeypatch.setenv("GA4_PROPERTY_ID", "123456789")
    from gsc_mcp.auth import get_ga4_property_id
    result = get_ga4_property_id()
    assert result == "properties/123456789"


def test_get_ga4_property_id_already_prefixed(monkeypatch):
    monkeypatch.setenv("GA4_PROPERTY_ID", "properties/123")
    from gsc_mcp.auth import get_ga4_property_id
    result = get_ga4_property_id()
    assert result == "properties/123"
    assert result.count("properties/") == 1


def test_get_ga4_property_id_override_takes_precedence(monkeypatch):
    monkeypatch.setenv("GA4_PROPERTY_ID", "111111111")
    from gsc_mcp.auth import get_ga4_property_id
    result = get_ga4_property_id(override="443684366")
    assert result == "properties/443684366"


def test_get_ga4_property_id_override_no_env_needed(monkeypatch):
    monkeypatch.delenv("GA4_PROPERTY_ID", raising=False)
    from gsc_mcp.auth import get_ga4_property_id
    result = get_ga4_property_id(override="443684366")
    assert result == "properties/443684366"


# ---------------------------------------------------------------------------
# ga4_organic_landing_pages
# ---------------------------------------------------------------------------

def test_organic_landing_pages_empty(mock_ga4_service):
    with patch("gsc_mcp.tools.ga4.get_ga4_service", return_value=mock_ga4_service):
        result = json.loads(ga4_organic_landing_pages())
    assert result["pages"] == []
    assert result["count"] == 0
    assert result["_meta"]["tool"] == "ga4_organic_landing_pages"
    assert "site" not in result["_meta"]["params"]


def test_organic_landing_pages_two_rows(mock_ga4_service):
    rows = [
        _make_ga4_row(
            ["/page-a"],
            ["100", "80", "0.20", "45.5", "5", "0.0"],
        ),
        _make_ga4_row(
            ["/page-b"],
            ["50", "30", "0.40", "30.0", "2", "19.99"],
        ),
    ]
    mock_ga4_service.run_report.return_value = _make_ga4_response(rows)

    with patch("gsc_mcp.tools.ga4.get_ga4_service", return_value=mock_ga4_service):
        result = json.loads(ga4_organic_landing_pages())

    assert result["count"] == 2
    assert result["pages"][0]["landing_page"] == "/page-a"
    assert result["pages"][0]["sessions"] == 100
    assert result["pages"][0]["bounce_rate"] == pytest.approx(0.20)
    assert result["pages"][1]["total_revenue"] == pytest.approx(19.99)


def test_organic_landing_pages_meta_params(mock_ga4_service):
    with patch("gsc_mcp.tools.ga4.get_ga4_service", return_value=mock_ga4_service):
        result = json.loads(ga4_organic_landing_pages(start_date="7daysAgo", limit=10))
    assert result["_meta"]["params"]["start_date"] == "7daysAgo"
    assert result["_meta"]["params"]["limit"] == 10


# ---------------------------------------------------------------------------
# ga4_traffic_sources
# ---------------------------------------------------------------------------

def test_traffic_sources_empty(mock_ga4_service):
    with patch("gsc_mcp.tools.ga4.get_ga4_service", return_value=mock_ga4_service):
        result = json.loads(ga4_traffic_sources())
    assert result["sources"] == []
    assert result["_meta"]["tool"] == "ga4_traffic_sources"
    assert "site" not in result["_meta"]["params"]


def test_traffic_sources_one_row(mock_ga4_service):
    rows = [_make_ga4_row(["Organic Search", "google", "organic"], ["200", "150", "10", "0.0"])]
    mock_ga4_service.run_report.return_value = _make_ga4_response(rows)

    with patch("gsc_mcp.tools.ga4.get_ga4_service", return_value=mock_ga4_service):
        result = json.loads(ga4_traffic_sources())

    assert result["count"] == 1
    src = result["sources"][0]
    assert src["channel_group"] == "Organic Search"
    assert src["source"] == "google"
    assert src["medium"] == "organic"
    assert src["sessions"] == 200
    assert src["conversions"] == pytest.approx(10.0)


# ---------------------------------------------------------------------------
# ga4_page_performance
# ---------------------------------------------------------------------------

def test_page_performance_empty(mock_ga4_service):
    with patch("gsc_mcp.tools.ga4.get_ga4_service", return_value=mock_ga4_service):
        result = json.loads(ga4_page_performance())
    assert result["pages"] == []
    assert result["_meta"]["tool"] == "ga4_page_performance"


def test_page_performance_no_filter_by_default(mock_ga4_service):
    with patch("gsc_mcp.tools.ga4.get_ga4_service", return_value=mock_ga4_service):
        ga4_page_performance()
    called_request = mock_ga4_service.run_report.call_args[0][0]
    assert called_request.dimension_filter == called_request.__class__().dimension_filter


def test_page_performance_with_page_path_filter(mock_ga4_service):
    with patch("gsc_mcp.tools.ga4.get_ga4_service", return_value=mock_ga4_service):
        ga4_page_performance(page_path="/blog")
    called_request = mock_ga4_service.run_report.call_args[0][0]
    assert called_request.dimension_filter is not None
    assert called_request.dimension_filter != called_request.__class__().dimension_filter


def test_page_performance_rows(mock_ga4_service):
    rows = [
        _make_ga4_row(["/about"], ["300", "200", "60.0", "0.70", "0.30", "5", "0.0"]),
    ]
    mock_ga4_service.run_report.return_value = _make_ga4_response(rows)

    with patch("gsc_mcp.tools.ga4.get_ga4_service", return_value=mock_ga4_service):
        result = json.loads(ga4_page_performance())

    p = result["pages"][0]
    assert p["page_path"] == "/about"
    assert p["page_views"] == 300
    assert p["engagement_rate"] == pytest.approx(0.70)


# ---------------------------------------------------------------------------
# ga4_realtime
# ---------------------------------------------------------------------------

def test_realtime_empty(mock_ga4_service):
    with patch("gsc_mcp.tools.ga4.get_ga4_service", return_value=mock_ga4_service):
        result = json.loads(ga4_realtime())
    assert result["active"] == []
    assert result["_meta"]["tool"] == "ga4_realtime"
    assert "site" not in result["_meta"]["params"]


def test_realtime_uses_run_realtime_report_not_run_report(mock_ga4_service):
    with patch("gsc_mcp.tools.ga4.get_ga4_service", return_value=mock_ga4_service):
        ga4_realtime()
    mock_ga4_service.run_realtime_report.assert_called_once()
    mock_ga4_service.run_report.assert_not_called()


def test_realtime_one_row(mock_ga4_service):
    rows = [_make_ga4_row(["/home", "France", "mobile"], ["12"])]
    mock_ga4_service.run_realtime_report.return_value = _make_ga4_response(rows)

    with patch("gsc_mcp.tools.ga4.get_ga4_service", return_value=mock_ga4_service):
        result = json.loads(ga4_realtime())

    assert result["count"] == 1
    a = result["active"][0]
    assert a["screen_name"] == "/home"
    assert a["country"] == "France"
    assert a["device_category"] == "mobile"
    assert a["active_users"] == 12


# ---------------------------------------------------------------------------
# ga4_user_behavior
# ---------------------------------------------------------------------------

def test_user_behavior_calls_batch_once(mock_ga4_service):
    with patch("gsc_mcp.tools.ga4.get_ga4_service", return_value=mock_ga4_service):
        ga4_user_behavior()
    mock_ga4_service.batch_run_reports.assert_called_once()
    mock_ga4_service.run_report.assert_not_called()


def test_user_behavior_empty_reports(mock_ga4_service):
    empty_reports = [_make_ga4_response([]), _make_ga4_response([]), _make_ga4_response([])]
    mock_ga4_service.batch_run_reports.return_value = _make_ga4_batch_response(empty_reports)

    with patch("gsc_mcp.tools.ga4.get_ga4_service", return_value=mock_ga4_service):
        result = json.loads(ga4_user_behavior())

    assert result["by_device"] == []
    assert result["by_country"] == []
    assert result["by_user_type"] == []
    assert result["_meta"]["tool"] == "ga4_user_behavior"
    assert "site" not in result["_meta"]["params"]


def test_user_behavior_splits_reports_correctly(mock_ga4_service):
    device_rows = [_make_ga4_row(["mobile"], ["1000", "0.65"])]
    country_rows = [_make_ga4_row(["France"], ["500", "0.70"])]
    user_type_rows = [_make_ga4_row(["new"], ["300", "0.55"])]

    mock_ga4_service.batch_run_reports.return_value = _make_ga4_batch_response([
        _make_ga4_response(device_rows),
        _make_ga4_response(country_rows),
        _make_ga4_response(user_type_rows),
    ])

    with patch("gsc_mcp.tools.ga4.get_ga4_service", return_value=mock_ga4_service):
        result = json.loads(ga4_user_behavior())

    assert result["by_device"][0]["dimension"] == "mobile"
    assert result["by_device"][0]["sessions"] == 1000
    assert result["by_country"][0]["dimension"] == "France"
    assert result["by_user_type"][0]["dimension"] == "new"


# ---------------------------------------------------------------------------
# ga4_conversion_funnel
# ---------------------------------------------------------------------------

def test_conversion_funnel_empty(mock_ga4_service):
    with patch("gsc_mcp.tools.ga4.get_ga4_service", return_value=mock_ga4_service):
        result = json.loads(ga4_conversion_funnel())
    assert result["converting_pages"] == []
    assert result["events"] == []
    assert result["_meta"]["tool"] == "ga4_conversion_funnel"
    assert "site" not in result["_meta"]["params"]


def test_conversion_funnel_filters_zero_conversions(mock_ga4_service):
    pages_rows = [
        _make_ga4_row(["/checkout"], ["5.0"]),
        _make_ga4_row(["/home"], ["0.0"]),
        _make_ga4_row(["/contact"], ["2.0"]),
    ]
    events_rows = [_make_ga4_row(["purchase"], ["50"])]

    def side_effect(request):
        dim = request.dimensions[0].name if request.dimensions else ""
        if dim == "pagePath":
            return _make_ga4_response(pages_rows)
        return _make_ga4_response(events_rows)

    mock_ga4_service.run_report.side_effect = side_effect

    with patch("gsc_mcp.tools.ga4.get_ga4_service", return_value=mock_ga4_service):
        result = json.loads(ga4_conversion_funnel())

    assert len(result["converting_pages"]) == 2
    paths = [p["page_path"] for p in result["converting_pages"]]
    assert "/checkout" in paths
    assert "/contact" in paths
    assert "/home" not in paths


def test_conversion_funnel_event_filter_applied(mock_ga4_service):
    with patch("gsc_mcp.tools.ga4.get_ga4_service", return_value=mock_ga4_service):
        ga4_conversion_funnel(event_name="purchase")

    assert mock_ga4_service.run_report.call_count == 2
    events_request = mock_ga4_service.run_report.call_args_list[1][0][0]
    assert events_request.dimension_filter is not None


def test_conversion_funnel_no_event_filter_when_none(mock_ga4_service):
    with patch("gsc_mcp.tools.ga4.get_ga4_service", return_value=mock_ga4_service):
        ga4_conversion_funnel(event_name=None)

    events_request = mock_ga4_service.run_report.call_args_list[1][0][0]
    assert events_request.dimension_filter == events_request.__class__().dimension_filter


def test_conversion_funnel_meta_params(mock_ga4_service):
    with patch("gsc_mcp.tools.ga4.get_ga4_service", return_value=mock_ga4_service):
        result = json.loads(ga4_conversion_funnel(event_name="purchase"))
    assert result["_meta"]["params"]["event_name"] == "purchase"
    assert "site" not in result["_meta"]["params"]


# ---------------------------------------------------------------------------
# Extra coverage: meta params and row parsing
# ---------------------------------------------------------------------------

def test_realtime_row_parsing(mock_ga4_service):
    rows = [
        _make_ga4_row(["/checkout", "Germany", "desktop"], ["7"]),
        _make_ga4_row(["/home", "USA", "mobile"], ["3"]),
    ]
    mock_ga4_service.run_realtime_report.return_value = _make_ga4_response(rows)

    with patch("gsc_mcp.tools.ga4.get_ga4_service", return_value=mock_ga4_service):
        result = json.loads(ga4_realtime())

    assert result["count"] == 2
    assert result["active"][0]["active_users"] == 7
    assert result["active"][1]["country"] == "USA"


def test_page_performance_meta_params(mock_ga4_service):
    with patch("gsc_mcp.tools.ga4.get_ga4_service", return_value=mock_ga4_service):
        result = json.loads(ga4_page_performance(page_path="/blog"))
    assert result["_meta"]["params"]["page_path"] == "/blog"
    assert result["_meta"]["tool"] == "ga4_page_performance"
