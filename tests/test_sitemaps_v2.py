import json
import pytest
from unittest.mock import patch
from gsc_mcp.tools.sitemaps import sitemaps_get, sitemaps_delete

SITE = "https://example.com/"
SITEMAP_URL = "https://example.com/sitemap.xml"
SITEMAP_URL_NO_XML = "https://example.com/sitemap/main"
UNSAFE_URL = "https://example.com/feeds/main"


def _mock_sitemap_resource():
    return {
        "path": SITEMAP_URL,
        "lastSubmitted": "2024-01-01T00:00:00Z",
        "lastDownloaded": "2024-01-02T00:00:00Z",
        "isPending": False,
        "isSitemapsIndex": False,
        "warnings": "2",
        "errors": "0",
        "contents": [{"type": "web", "submitted": "100", "indexed": "80"}],
    }


# ===== sitemaps_get =====

def test_sitemaps_get_returns_flat_dict(mock_gsc_service):
    mock_gsc_service.sitemaps.return_value.get.return_value.execute.return_value = _mock_sitemap_resource()
    with patch("gsc_mcp.tools.sitemaps.get_gsc_service", return_value=mock_gsc_service):
        result = json.loads(sitemaps_get(SITE, SITEMAP_URL))
    assert "sitemap" in result
    assert result["sitemap"]["url"] == SITEMAP_URL
    assert "_meta" in result


def test_sitemaps_get_normalizes_warnings_errors_from_string(mock_gsc_service):
    mock_gsc_service.sitemaps.return_value.get.return_value.execute.return_value = _mock_sitemap_resource()
    with patch("gsc_mcp.tools.sitemaps.get_gsc_service", return_value=mock_gsc_service):
        result = json.loads(sitemaps_get(SITE, SITEMAP_URL))
    assert isinstance(result["sitemap"]["warnings"], int)
    assert isinstance(result["sitemap"]["errors"], int)
    assert result["sitemap"]["warnings"] == 2
    assert result["sitemap"]["errors"] == 0


def test_sitemaps_get_warnings_already_int(mock_gsc_service):
    resource = _mock_sitemap_resource()
    resource["warnings"] = 5
    resource["errors"] = 0
    mock_gsc_service.sitemaps.return_value.get.return_value.execute.return_value = resource
    with patch("gsc_mcp.tools.sitemaps.get_gsc_service", return_value=mock_gsc_service):
        result = json.loads(sitemaps_get(SITE, SITEMAP_URL))
    assert result["sitemap"]["warnings"] == 5
    assert isinstance(result["sitemap"]["warnings"], int)


def test_sitemaps_get_missing_warnings_defaults_to_zero(mock_gsc_service):
    resource = {
        "path": SITEMAP_URL,
        "lastSubmitted": "2024-01-01T00:00:00Z",
        "isPending": False,
        "isSitemapsIndex": False,
    }
    mock_gsc_service.sitemaps.return_value.get.return_value.execute.return_value = resource
    with patch("gsc_mcp.tools.sitemaps.get_gsc_service", return_value=mock_gsc_service):
        result = json.loads(sitemaps_get(SITE, SITEMAP_URL))
    assert result["sitemap"]["warnings"] == 0
    assert result["sitemap"]["errors"] == 0


def test_sitemaps_get_contents_passthrough(mock_gsc_service):
    mock_gsc_service.sitemaps.return_value.get.return_value.execute.return_value = _mock_sitemap_resource()
    with patch("gsc_mcp.tools.sitemaps.get_gsc_service", return_value=mock_gsc_service):
        result = json.loads(sitemaps_get(SITE, SITEMAP_URL))
    assert result["sitemap"]["contents"] == [{"type": "web", "submitted": "100", "indexed": "80"}]


def test_sitemaps_get_booleans(mock_gsc_service):
    mock_gsc_service.sitemaps.return_value.get.return_value.execute.return_value = _mock_sitemap_resource()
    with patch("gsc_mcp.tools.sitemaps.get_gsc_service", return_value=mock_gsc_service):
        result = json.loads(sitemaps_get(SITE, SITEMAP_URL))
    assert result["sitemap"]["is_pending"] is False
    assert result["sitemap"]["is_index"] is False


def test_sitemaps_get_meta_tool_and_params(mock_gsc_service):
    mock_gsc_service.sitemaps.return_value.get.return_value.execute.return_value = _mock_sitemap_resource()
    with patch("gsc_mcp.tools.sitemaps.get_gsc_service", return_value=mock_gsc_service):
        result = json.loads(sitemaps_get(SITE, SITEMAP_URL))
    assert result["_meta"]["tool"] == "sitemaps_get"
    assert result["_meta"]["params"]["sitemap_url"] == SITEMAP_URL


def test_sitemaps_get_calls_api_with_correct_args(mock_gsc_service):
    mock_gsc_service.sitemaps.return_value.get.return_value.execute.return_value = _mock_sitemap_resource()
    with patch("gsc_mcp.tools.sitemaps.get_gsc_service", return_value=mock_gsc_service):
        sitemaps_get(SITE, SITEMAP_URL)
    mock_gsc_service.sitemaps.return_value.get.assert_called_once_with(
        siteUrl=SITE, feedpath=SITEMAP_URL
    )


# ===== sitemaps_delete =====

def test_sitemaps_delete_valid_xml_calls_api(mock_gsc_service):
    mock_gsc_service.sitemaps.return_value.delete.return_value.execute.return_value = None
    with patch("gsc_mcp.tools.sitemaps.get_gsc_service", return_value=mock_gsc_service):
        result = json.loads(sitemaps_delete(SITE, SITEMAP_URL))
    assert result["status"] == "deleted"
    mock_gsc_service.sitemaps.return_value.delete.assert_called_once_with(
        siteUrl=SITE, feedpath=SITEMAP_URL
    )


def test_sitemaps_delete_sitemap_in_path_allowed(mock_gsc_service):
    mock_gsc_service.sitemaps.return_value.delete.return_value.execute.return_value = None
    with patch("gsc_mcp.tools.sitemaps.get_gsc_service", return_value=mock_gsc_service):
        result = json.loads(sitemaps_delete(SITE, SITEMAP_URL_NO_XML))
    assert result["status"] == "deleted"


def test_sitemaps_delete_unsafe_url_raises_value_error(mock_gsc_service):
    with patch("gsc_mcp.tools.sitemaps.get_gsc_service", return_value=mock_gsc_service):
        with pytest.raises(ValueError) as exc_info:
            sitemaps_delete(SITE, UNSAFE_URL)
    assert UNSAFE_URL in str(exc_info.value)


def test_sitemaps_delete_unsafe_url_does_not_call_api(mock_gsc_service):
    with patch("gsc_mcp.tools.sitemaps.get_gsc_service", return_value=mock_gsc_service):
        with pytest.raises(ValueError):
            sitemaps_delete(SITE, UNSAFE_URL)
    mock_gsc_service.sitemaps.return_value.delete.assert_not_called()


def test_sitemaps_delete_returns_sitemap_url_in_output(mock_gsc_service):
    mock_gsc_service.sitemaps.return_value.delete.return_value.execute.return_value = None
    with patch("gsc_mcp.tools.sitemaps.get_gsc_service", return_value=mock_gsc_service):
        result = json.loads(sitemaps_delete(SITE, SITEMAP_URL))
    assert result["sitemap_url"] == SITEMAP_URL
    assert result["site"] == SITE


def test_sitemaps_delete_meta(mock_gsc_service):
    mock_gsc_service.sitemaps.return_value.delete.return_value.execute.return_value = None
    with patch("gsc_mcp.tools.sitemaps.get_gsc_service", return_value=mock_gsc_service):
        result = json.loads(sitemaps_delete(SITE, SITEMAP_URL))
    assert result["_meta"]["tool"] == "sitemaps_delete"
    assert result["_meta"]["params"]["sitemap_url"] == SITEMAP_URL


def test_sitemaps_delete_execute_returning_none_handled(mock_gsc_service):
    mock_gsc_service.sitemaps.return_value.delete.return_value.execute.return_value = None
    with patch("gsc_mcp.tools.sitemaps.get_gsc_service", return_value=mock_gsc_service):
        result = json.loads(sitemaps_delete(SITE, SITEMAP_URL))
    assert result["status"] == "deleted"
