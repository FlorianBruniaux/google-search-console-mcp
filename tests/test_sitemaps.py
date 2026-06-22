import json
import pytest
from unittest.mock import patch
from gsc_mcp.tools.sitemaps import list_sitemaps, submit_sitemap

SITE = "https://example.com/"
SITEMAP_URL = "https://example.com/sitemap.xml"


def _mock_sitemaps_response():
    return {
        "sitemap": [
            {
                "path": SITEMAP_URL,
                "lastSubmitted": "2024-01-01T00:00:00Z",
                "isPending": False,
                "isSitemapsIndex": False,
                "lastDownloaded": "2024-01-02T00:00:00Z",
                "warnings": "0",
                "errors": "0",
                "contents": [{"type": "web", "submitted": "100", "indexed": "80"}],
            }
        ]
    }


def test_list_sitemaps(mock_gsc_service):
    mock_gsc_service.sitemaps.return_value.list.return_value.execute.return_value = (
        _mock_sitemaps_response()
    )
    with patch("gsc_mcp.tools.sitemaps.get_searchconsole_service", return_value=mock_gsc_service):
        result = json.loads(list_sitemaps(SITE))

    assert result["count"] == 1
    assert result["sitemaps"][0]["url"] == SITEMAP_URL
    assert "_meta" in result


def test_list_sitemaps_empty(mock_gsc_service):
    mock_gsc_service.sitemaps.return_value.list.return_value.execute.return_value = {}
    with patch("gsc_mcp.tools.sitemaps.get_searchconsole_service", return_value=mock_gsc_service):
        result = json.loads(list_sitemaps(SITE))

    assert result["count"] == 0
    assert result["sitemaps"] == []


def test_submit_sitemap(mock_gsc_service):
    mock_gsc_service.sitemaps.return_value.submit.return_value.execute.return_value = None
    with patch("gsc_mcp.tools.sitemaps.get_searchconsole_service", return_value=mock_gsc_service):
        result = json.loads(submit_sitemap(SITE, SITEMAP_URL))

    assert result["status"] == "submitted"
    assert result["sitemap_url"] == SITEMAP_URL
    assert "_meta" in result
    mock_gsc_service.sitemaps.return_value.submit.assert_called_once_with(
        siteUrl=SITE, feedpath=SITEMAP_URL
    )
