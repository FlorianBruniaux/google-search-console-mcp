import pytest
from unittest.mock import patch, MagicMock
from gsc_mcp import constants
from gsc_mcp import auth


def test_gsc_scope_in_constants():
    assert hasattr(constants, "SCOPES_GSC")
    assert "webmasters" in constants.SCOPES_GSC[0]


def test_indexing_scope_in_constants():
    assert hasattr(constants, "SCOPES_INDEXING")
    assert "indexing" in constants.SCOPES_INDEXING[0]


def test_scopes_are_distinct():
    assert constants.SCOPES_GSC != constants.SCOPES_INDEXING


def test_get_gsc_service_raises_without_credentials(monkeypatch):
    monkeypatch.delenv("GSC_CREDENTIALS_PATH", raising=False)
    monkeypatch.delenv("GSC_SERVICE_ACCOUNT_PATH", raising=False)
    monkeypatch.setenv("GSC_SKIP_OAUTH", "true")
    with pytest.raises(RuntimeError, match="No credentials"):
        auth.get_gsc_service()


def test_get_indexing_service_raises_without_credentials(monkeypatch):
    monkeypatch.delenv("GSC_CREDENTIALS_PATH", raising=False)
    monkeypatch.delenv("GSC_SERVICE_ACCOUNT_PATH", raising=False)
    monkeypatch.setenv("GSC_SKIP_OAUTH", "true")
    with pytest.raises(RuntimeError, match="No credentials"):
        auth.get_indexing_service()


def test_get_gsc_service_via_service_account(tmp_path, monkeypatch):
    sa_file = tmp_path / "sa.json"
    sa_file.write_text("{}")
    monkeypatch.setenv("GSC_SERVICE_ACCOUNT_PATH", str(sa_file))
    monkeypatch.delenv("GSC_CREDENTIALS_PATH", raising=False)

    fake_creds = MagicMock()

    with patch("gsc_mcp.auth.service_account") as mock_sa, \
         patch("gsc_mcp.auth.build", return_value=MagicMock()):
        mock_sa.Credentials.from_service_account_file.return_value = fake_creds
        svc = auth.get_gsc_service()
        assert svc is not None
        mock_sa.Credentials.from_service_account_file.assert_called_once_with(
            str(sa_file), scopes=constants.SCOPES_GSC
        )


def test_get_indexing_service_via_service_account(tmp_path, monkeypatch):
    sa_file = tmp_path / "sa.json"
    sa_file.write_text("{}")
    monkeypatch.setenv("GSC_SERVICE_ACCOUNT_PATH", str(sa_file))
    monkeypatch.delenv("GSC_CREDENTIALS_PATH", raising=False)

    fake_creds = MagicMock()

    with patch("gsc_mcp.auth.service_account") as mock_sa, \
         patch("gsc_mcp.auth.build", return_value=MagicMock()):
        mock_sa.Credentials.from_service_account_file.return_value = fake_creds
        svc = auth.get_indexing_service()
        assert svc is not None
        mock_sa.Credentials.from_service_account_file.assert_called_once_with(
            str(sa_file), scopes=constants.SCOPES_INDEXING
        )
