import json
import os
from unittest.mock import MagicMock, patch

import pytest

from gsc_mcp.tools.crux import crux_page_vitals, crux_history, _rate


@pytest.fixture(autouse=True)
def set_crux_key(monkeypatch):
    monkeypatch.setenv("CRUX_API_KEY", "test-api-key")


def _mock_vitals_response(lcp_p75=1800, inp_p75=120, cls_p75=0.05):
    return {
        "record": {
            "metrics": {
                "largest_contentful_paint": {"percentiles": {"p75": lcp_p75}},
                "interaction_to_next_paint": {"percentiles": {"p75": inp_p75}},
                "cumulative_layout_shift": {"percentiles": {"p75": cls_p75}},
                "first_contentful_paint": {"percentiles": {"p75": 900}},
                "experimental_time_to_first_byte": {"percentiles": {"p75": 600}},
            }
        }
    }


def _mock_history_response(metric="largest_contentful_paint", n=3):
    periods = [
        {"firstDate": f"2026-0{i+1}-01", "lastDate": f"2026-0{i+1}-07"}
        for i in range(n)
    ]
    p75s = [1800 + i * 100 for i in range(n)]
    return {
        "record": {
            "collectionPeriods": periods,
            "metrics": {
                metric: {
                    "percentilesTimeseries": {"p75s": p75s}
                }
            }
        }
    }


def _make_mock_client(status_code=200, json_body=None):
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.json.return_value = json_body or {}
    mock_resp.raise_for_status = MagicMock()
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.post.return_value = mock_resp
    return mock_client


# ---------------------------------------------------------------------------
# _rate helper
# ---------------------------------------------------------------------------

def test_rate_lcp_good():
    assert _rate("largest_contentful_paint", 1800) == "good"


def test_rate_lcp_needs_improvement():
    assert _rate("largest_contentful_paint", 3000) == "needs_improvement"


def test_rate_lcp_poor():
    assert _rate("largest_contentful_paint", 5000) == "poor"


def test_rate_cls_good():
    assert _rate("cumulative_layout_shift", 0.05) == "good"


def test_rate_none_returns_unknown():
    assert _rate("largest_contentful_paint", None) == "unknown"


# ---------------------------------------------------------------------------
# crux_page_vitals
# ---------------------------------------------------------------------------

def test_crux_page_vitals_good_lcp():
    """LCP p75=1800ms rates as good (threshold 2500ms)."""
    with patch("httpx.Client", return_value=_make_mock_client(200, _mock_vitals_response(lcp_p75=1800))):
        result = json.loads(crux_page_vitals("https://example.com/"))
    assert result["metrics"]["largest_contentful_paint"]["rating"] == "good"
    assert result["metrics"]["largest_contentful_paint"]["p75"] == 1800


def test_crux_page_vitals_poor_lcp():
    with patch("httpx.Client", return_value=_make_mock_client(200, _mock_vitals_response(lcp_p75=5000))):
        result = json.loads(crux_page_vitals("https://slow-site.example/"))
    assert result["metrics"]["largest_contentful_paint"]["rating"] == "poor"


def test_crux_page_vitals_not_found():
    """404 from CrUX returns verdict=not_enough_data."""
    with patch("httpx.Client", return_value=_make_mock_client(404)):
        result = json.loads(crux_page_vitals("https://tiny-site.example/obscure/"))
    assert result["verdict"] == "not_enough_data"


def test_crux_page_vitals_form_factor_in_payload():
    """form_factor != ALL_FORM_FACTORS is included in POST payload."""
    mock_client = _make_mock_client(200, _mock_vitals_response())
    with patch("httpx.Client", return_value=mock_client):
        crux_page_vitals("https://example.com/", form_factor="PHONE")
    _, kwargs = mock_client.post.call_args
    assert kwargs["json"]["formFactor"] == "PHONE"


def test_crux_page_vitals_all_form_factors_no_form_factor_key():
    """ALL_FORM_FACTORS means formFactor is NOT included in payload."""
    mock_client = _make_mock_client(200, _mock_vitals_response())
    with patch("httpx.Client", return_value=mock_client):
        crux_page_vitals("https://example.com/")
    _, kwargs = mock_client.post.call_args
    assert "formFactor" not in kwargs["json"]


def test_crux_page_vitals_meta():
    with patch("httpx.Client", return_value=_make_mock_client(200, _mock_vitals_response())):
        result = json.loads(crux_page_vitals("https://example.com/", form_factor="DESKTOP"))
    assert result["_meta"]["tool"] == "crux_page_vitals"
    assert result["_meta"]["params"]["form_factor"] == "DESKTOP"


def test_crux_page_vitals_no_api_key_raises(monkeypatch):
    monkeypatch.delenv("CRUX_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="CRUX_API_KEY"):
        crux_page_vitals("https://example.com/")


# ---------------------------------------------------------------------------
# crux_history
# ---------------------------------------------------------------------------

def test_crux_history_returns_weekly_series():
    """crux_history returns one entry per collection period."""
    with patch("httpx.Client", return_value=_make_mock_client(200, _mock_history_response(n=5))):
        result = json.loads(crux_history("https://example.com/"))
    assert result["weeks"] == 5
    assert len(result["history"]) == 5
    assert "week_start" in result["history"][0]
    assert "week_end" in result["history"][0]
    assert "p75" in result["history"][0]


def test_crux_history_not_found():
    """404 returns verdict=not_enough_data."""
    with patch("httpx.Client", return_value=_make_mock_client(404)):
        result = json.loads(crux_history("https://tiny-site.example/"))
    assert result["verdict"] == "not_enough_data"


def test_crux_history_meta():
    with patch("httpx.Client", return_value=_make_mock_client(200, _mock_history_response(n=2))):
        result = json.loads(crux_history("https://example.com/", metric="cumulative_layout_shift"))
    assert result["_meta"]["params"]["metric"] == "cumulative_layout_shift"
    assert result["metric"] == "cumulative_layout_shift"


def test_crux_history_no_api_key_raises(monkeypatch):
    monkeypatch.delenv("CRUX_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="CRUX_API_KEY"):
        crux_history("https://example.com/")
