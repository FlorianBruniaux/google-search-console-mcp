import json
import pytest
from unittest.mock import patch, call, MagicMock

from tests.conftest import _make_ga4_row, _make_ga4_response, _make_ga4_batch_response
from gsc_mcp.tools.ga4 import (
    ga4_organic_landing_pages,
    ga4_traffic_sources,
    ga4_page_performance,
    ga4_realtime,
    ga4_user_behavior,
    ga4_conversion_funnel,
    ga4_funnel,
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


# ---------------------------------------------------------------------------
# hostname + country dimension filters (Phase 1, v0.5.0)
# ---------------------------------------------------------------------------

def test_build_dimension_filter_none_returns_none():
    from gsc_mcp.tools.ga4 import _build_dimension_filter
    assert _build_dimension_filter() is None
    assert _build_dimension_filter(hostname=None, country=None) is None


def test_build_dimension_filter_hostname_only():
    from gsc_mcp.tools.ga4 import _build_dimension_filter
    f = _build_dimension_filter(hostname="cc.bruniaux.com")
    assert f is not None
    assert f.filter.field_name == "hostName"
    assert f.filter.string_filter.value == "cc.bruniaux.com"


def test_build_dimension_filter_hostname_country_and_group():
    from gsc_mcp.tools.ga4 import _build_dimension_filter
    f = _build_dimension_filter(hostname="cc.bruniaux.com", country="France")
    assert len(f.and_group.expressions) == 2
    field_names = {e.filter.field_name for e in f.and_group.expressions}
    assert field_names == {"hostName", "country"}


def test_build_dimension_filter_base_filter_only():
    from gsc_mcp.tools.ga4 import _build_dimension_filter, _organic_filter
    f = _build_dimension_filter(base_filter=_organic_filter())
    assert f is not None
    assert f.filter.field_name == "sessionMedium"


def test_build_dimension_filter_base_plus_hostname():
    from gsc_mcp.tools.ga4 import _build_dimension_filter, _organic_filter
    f = _build_dimension_filter(hostname="cc.bruniaux.com", base_filter=_organic_filter())
    assert len(f.and_group.expressions) == 2


def test_organic_landing_pages_no_filter_change_without_params(mock_ga4_service):
    """Without hostname/country, dimension_filter is still the organic filter (backward compat)."""
    with patch("gsc_mcp.tools.ga4.get_ga4_service", return_value=mock_ga4_service):
        ga4_organic_landing_pages()
    req = mock_ga4_service.run_report.call_args[0][0]
    assert req.dimension_filter is not None
    assert req.dimension_filter.filter.field_name == "sessionMedium"


def test_organic_landing_pages_hostname_adds_and_group(mock_ga4_service):
    with patch("gsc_mcp.tools.ga4.get_ga4_service", return_value=mock_ga4_service):
        ga4_organic_landing_pages(hostname="cc.bruniaux.com")
    req = mock_ga4_service.run_report.call_args[0][0]
    assert len(req.dimension_filter.and_group.expressions) == 2


def test_page_performance_hostname_filter(mock_ga4_service):
    with patch("gsc_mcp.tools.ga4.get_ga4_service", return_value=mock_ga4_service):
        ga4_page_performance(hostname="cc.bruniaux.com")
    req = mock_ga4_service.run_report.call_args[0][0]
    assert req.dimension_filter is not None
    assert req.dimension_filter.filter.field_name == "hostName"


def test_page_performance_hostname_country_and_group(mock_ga4_service):
    with patch("gsc_mcp.tools.ga4.get_ga4_service", return_value=mock_ga4_service):
        ga4_page_performance(hostname="cc.bruniaux.com", country="France")
    req = mock_ga4_service.run_report.call_args[0][0]
    assert len(req.dimension_filter.and_group.expressions) == 2


def test_page_performance_no_filter_without_params(mock_ga4_service):
    """No hostname/country/page_path → dimension_filter is unset (None)."""
    with patch("gsc_mcp.tools.ga4.get_ga4_service", return_value=mock_ga4_service):
        ga4_page_performance()
    req = mock_ga4_service.run_report.call_args[0][0]
    assert req.dimension_filter == req.__class__().dimension_filter


def test_realtime_hostname_filter(mock_ga4_service):
    with patch("gsc_mcp.tools.ga4.get_ga4_service", return_value=mock_ga4_service):
        ga4_realtime(hostname="cc.bruniaux.com")
    req = mock_ga4_service.run_realtime_report.call_args[0][0]
    assert req.dimension_filter is not None
    assert req.dimension_filter.filter.field_name == "hostName"


def test_realtime_no_hostname_no_filter(mock_ga4_service):
    with patch("gsc_mcp.tools.ga4.get_ga4_service", return_value=mock_ga4_service):
        ga4_realtime()
    req = mock_ga4_service.run_realtime_report.call_args[0][0]
    assert req.dimension_filter == req.__class__().dimension_filter


def test_user_behavior_hostname_filter_applied_to_all_subrequests(mock_ga4_service):
    with patch("gsc_mcp.tools.ga4.get_ga4_service", return_value=mock_ga4_service):
        ga4_user_behavior(hostname="cc.bruniaux.com")
    batch_req = mock_ga4_service.batch_run_reports.call_args[0][0]
    for sub_req in batch_req.requests:
        assert sub_req.dimension_filter is not None
        assert sub_req.dimension_filter.filter.field_name == "hostName"


def test_user_behavior_no_filter_without_params(mock_ga4_service):
    with patch("gsc_mcp.tools.ga4.get_ga4_service", return_value=mock_ga4_service):
        ga4_user_behavior()
    batch_req = mock_ga4_service.batch_run_reports.call_args[0][0]
    for sub_req in batch_req.requests:
        assert sub_req.dimension_filter == sub_req.__class__().dimension_filter


def test_conversion_funnel_hostname_filter_applied(mock_ga4_service):
    with patch("gsc_mcp.tools.ga4.get_ga4_service", return_value=mock_ga4_service):
        ga4_conversion_funnel(hostname="cc.bruniaux.com")
    pages_req = mock_ga4_service.run_report.call_args_list[0][0][0]
    events_req = mock_ga4_service.run_report.call_args_list[1][0][0]
    assert pages_req.dimension_filter.filter.field_name == "hostName"
    assert events_req.dimension_filter.filter.field_name == "hostName"


def test_traffic_sources_hostname_filter(mock_ga4_service):
    with patch("gsc_mcp.tools.ga4.get_ga4_service", return_value=mock_ga4_service):
        ga4_traffic_sources(hostname="cc.bruniaux.com")
    req = mock_ga4_service.run_report.call_args[0][0]
    assert req.dimension_filter.filter.field_name == "hostName"


def test_meta_params_include_hostname_country(mock_ga4_service):
    with patch("gsc_mcp.tools.ga4.get_ga4_service", return_value=mock_ga4_service):
        result = json.loads(ga4_page_performance(hostname="cc.bruniaux.com", country="France"))
    assert result["_meta"]["params"]["hostname"] == "cc.bruniaux.com"
    assert result["_meta"]["params"]["country"] == "France"


# ---------------------------------------------------------------------------
# ga4_funnel
# ---------------------------------------------------------------------------

def _make_alpha_row(step_name: str, users: str):
    """Build a mock funnel table row with dimension_values[0] and metric_values[0]."""
    row = MagicMock()
    row.dimension_values = [MagicMock(value=step_name)]
    row.metric_values = [MagicMock(value=users)]
    return row


def _make_alpha_client(rows: list):
    """Build a mock alpha GA4 client whose run_funnel_report returns rows."""
    client = MagicMock()
    response = MagicMock()
    response.funnel_table.rows = rows
    client.run_funnel_report.return_value = response
    return client


STEPS_2 = [
    {"name": "Visit homepage", "event": "page_view"},
    {"name": "Add to cart", "event": "add_to_cart"},
]


def test_ga4_funnel_two_step_conversion_rate():
    """Step 1 conversion_rate is null; step 2 is calculated from step 1 users."""
    rows = [
        _make_alpha_row("Visit homepage", "1000"),
        _make_alpha_row("Add to cart", "450"),
    ]
    mock_client = _make_alpha_client(rows)

    with patch("gsc_mcp.tools.ga4.get_alpha_ga4_service", return_value=mock_client):
        result = json.loads(ga4_funnel(STEPS_2, "7daysAgo", "today"))

    assert result["steps"][0]["users"] == 1000
    assert result["steps"][0]["conversion_rate"] is None
    assert result["steps"][1]["users"] == 450
    assert result["steps"][1]["conversion_rate"] == pytest.approx(45.0)


def test_ga4_funnel_invalid_steps_no_api_call():
    """Less than 2 steps returns INVALID_STEPS without calling the alpha API."""
    mock_client = MagicMock()

    with patch("gsc_mcp.tools.ga4.get_alpha_ga4_service", return_value=mock_client):
        result = json.loads(ga4_funnel([{"name": "Only step", "event": "page_view"}], "7daysAgo", "today"))

    assert result["error"] == "INVALID_STEPS"
    assert result["reason"] == "minimum 2 steps required"
    mock_client.run_funnel_report.assert_not_called()


def test_ga4_funnel_event_names_passed_to_steps():
    """Event names from input steps appear in the output steps."""
    rows = [
        _make_alpha_row("Visit homepage", "500"),
        _make_alpha_row("Add to cart", "200"),
    ]
    mock_client = _make_alpha_client(rows)

    with patch("gsc_mcp.tools.ga4.get_alpha_ga4_service", return_value=mock_client):
        result = json.loads(ga4_funnel(STEPS_2, "7daysAgo", "today"))

    assert result["steps"][0]["event"] == "page_view"
    assert result["steps"][1]["event"] == "add_to_cart"


def test_ga4_funnel_uses_alpha_client_not_beta():
    """The tool calls get_alpha_ga4_service, not get_ga4_service."""
    rows = [
        _make_alpha_row("Step 1", "100"),
        _make_alpha_row("Step 2", "50"),
    ]
    mock_alpha = _make_alpha_client(rows)

    with patch("gsc_mcp.tools.ga4.get_alpha_ga4_service", return_value=mock_alpha) as patched_alpha, \
         patch("gsc_mcp.tools.ga4.get_ga4_service") as patched_beta:
        ga4_funnel(STEPS_2, "7daysAgo", "today")

    patched_alpha.assert_called_once()
    patched_beta.assert_not_called()


def test_ga4_funnel_meta_block_present():
    """_meta block has the correct tool name and echoes back params."""
    rows = [
        _make_alpha_row("Visit homepage", "1000"),
        _make_alpha_row("Add to cart", "300"),
    ]
    mock_client = _make_alpha_client(rows)

    with patch("gsc_mcp.tools.ga4.get_alpha_ga4_service", return_value=mock_client):
        result = json.loads(ga4_funnel(STEPS_2, "2025-01-01", "2025-01-31", property_id="99999"))

    assert result["_meta"]["tool"] == "ga4_funnel"
    assert result["_meta"]["params"]["start_date"] == "2025-01-01"
    assert result["_meta"]["params"]["end_date"] == "2025-01-31"
    assert result["_meta"]["params"]["property_id"] == "99999"
    assert result["_meta"]["params"]["steps"] == STEPS_2
