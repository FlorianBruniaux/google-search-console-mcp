import json
import pytest
from unittest.mock import patch, MagicMock
from gsc_mcp.tools.properties import get_capabilities, list_properties, get_site_details


def test_get_capabilities_returns_36_tools():
    result = json.loads(get_capabilities())
    assert result["total"] == 36
    assert len(result["tools"]) == 36


def test_get_capabilities_has_meta():
    result = json.loads(get_capabilities())
    assert "_meta" in result


def test_list_properties(mock_gsc_service):
    mock_gsc_service.sites.return_value.list.return_value.execute.return_value = {
        "siteEntry": [
            {"siteUrl": "https://example.com/", "permissionLevel": "siteOwner"},
            {"siteUrl": "sc-domain:example.com", "permissionLevel": "siteFullUser"},
        ]
    }

    with patch("gsc_mcp.tools.properties.get_searchconsole_service", return_value=mock_gsc_service):
        result = json.loads(list_properties())

    assert result["count"] == 2
    assert result["properties"][0]["url"] == "https://example.com/"
    assert "_meta" in result


def test_list_properties_empty(mock_gsc_service):
    mock_gsc_service.sites.return_value.list.return_value.execute.return_value = {}

    with patch("gsc_mcp.tools.properties.get_searchconsole_service", return_value=mock_gsc_service):
        result = json.loads(list_properties())

    assert result["count"] == 0
    assert result["properties"] == []


def test_get_site_details(mock_gsc_service):
    mock_gsc_service.sites.return_value.get.return_value.execute.return_value = {
        "siteUrl": "https://example.com/",
        "permissionLevel": "siteOwner",
    }

    with patch("gsc_mcp.tools.properties.get_searchconsole_service", return_value=mock_gsc_service):
        result = json.loads(get_site_details("https://example.com/"))

    assert result["url"] == "https://example.com/"
    assert result["permission"] == "siteOwner"
    assert "_meta" in result
