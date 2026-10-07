import json
import pytest
from unittest.mock import patch, MagicMock
from gsc_mcp.tools.properties import get_capabilities, list_properties, get_site_details


def test_get_capabilities_total_matches_tools():
    result = json.loads(get_capabilities())
    assert result["total"] == len(result["tools"])


def test_get_capabilities_lists_engines_without_credentials(monkeypatch):
    monkeypatch.delenv("GSC_SERVICE_ACCOUNT_PATH", raising=False)
    monkeypatch.delenv("GSC_CREDENTIALS_PATH", raising=False)
    monkeypatch.delenv("BING_WEBMASTER_API_KEY", raising=False)

    result = json.loads(get_capabilities())

    assert result["engines"]["google"] == {"credential_env_declared": False}
    assert result["engines"]["bing"]["credential_env_declared"] is False
    assert result["engines"]["bing"]["tools"] == sorted(
        name for name in result["tools"] if name.startswith("bing_")
    )
    assert result["engines"]["indexnow"] == {"tools": ["indexnow_submit"]}


def test_get_capabilities_reports_declarations_without_values(monkeypatch):
    monkeypatch.setenv("GSC_CREDENTIALS_PATH", "google-private-value")
    monkeypatch.setenv("BING_WEBMASTER_API_KEY", "bing-private-value")

    raw = get_capabilities()
    result = json.loads(raw)

    assert result["engines"]["google"]["credential_env_declared"] is True
    assert result["engines"]["bing"]["credential_env_declared"] is True
    assert "google-private-value" not in raw
    assert "bing-private-value" not in raw
    assert "authenticated" not in result["engines"]["google"]
    assert "authenticated" not in result["engines"]["bing"]


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
