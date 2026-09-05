import json
import os
import stat
from pathlib import Path

import pytest
from google.auth.exceptions import RefreshError
from unittest.mock import patch, MagicMock
from gsc_mcp import constants
from gsc_mcp import auth


def test_save_oauth_token_replaces_atomically(tmp_path, monkeypatch):
    token_path = tmp_path / "tokens" / "token.json"
    replaced = {}

    real_replace = os.replace

    def record_replace(source, destination):
        replaced["source"] = Path(source)
        replaced["destination"] = Path(destination)
        real_replace(source, destination)

    monkeypatch.setattr("gsc_mcp.auth.os.replace", record_replace)
    creds = MagicMock()
    creds.to_json.return_value = '{"token":"secret"}'

    auth._save_oauth_token(token_path, creds)

    assert replaced["destination"] == token_path
    assert replaced["source"] != token_path
    assert stat.S_IMODE(token_path.stat().st_mode) == 0o600
    assert json.loads(token_path.read_text()) == {"token": "secret"}


def test_save_oauth_token_removes_temp_file_on_failure(tmp_path, monkeypatch):
    token_path = tmp_path / "token.json"
    creds = MagicMock()
    creds.to_json.return_value = '{"token":"secret"}'
    monkeypatch.setattr(
        "gsc_mcp.auth.os.replace", MagicMock(side_effect=OSError("replace failed"))
    )

    with pytest.raises(OSError, match="replace failed"):
        auth._save_oauth_token(token_path, creds)

    assert list(tmp_path.glob(".token.json.*")) == []


def test_gsc_scope_in_constants():
    assert hasattr(constants, "SCOPES_GSC")
    assert "webmasters" in constants.SCOPES_GSC[0]


def test_indexing_scope_in_constants():
    assert hasattr(constants, "SCOPES_INDEXING")
    assert "indexing" in constants.SCOPES_INDEXING[0]


def test_scopes_are_distinct():
    assert constants.SCOPES_GSC != constants.SCOPES_INDEXING


def test_get_searchconsole_service_raises_without_credentials(monkeypatch):
    monkeypatch.delenv("GSC_CREDENTIALS_PATH", raising=False)
    monkeypatch.delenv("GSC_SERVICE_ACCOUNT_PATH", raising=False)
    monkeypatch.setenv("GSC_SKIP_OAUTH", "true")
    with pytest.raises(RuntimeError, match="No credentials"):
        auth.get_searchconsole_service()


def test_get_indexing_service_raises_without_credentials(monkeypatch):
    monkeypatch.delenv("GSC_CREDENTIALS_PATH", raising=False)
    monkeypatch.delenv("GSC_SERVICE_ACCOUNT_PATH", raising=False)
    monkeypatch.setenv("GSC_SKIP_OAUTH", "true")
    with pytest.raises(RuntimeError, match="No credentials"):
        auth.get_indexing_service()


def test_oauth_creds_refresh_error_falls_back_to_reauth(tmp_path, monkeypatch):
    monkeypatch.delenv("GSC_SERVICE_ACCOUNT_PATH", raising=False)
    monkeypatch.delenv("GSC_CREDENTIALS_PATH", raising=False)
    monkeypatch.delenv("GSC_SKIP_OAUTH", raising=False)

    token_path = tmp_path / "token_gsc.json"
    token_path.write_text("{}")

    fake_creds = MagicMock()
    fake_creds.valid = False
    fake_creds.expired = True
    fake_creds.refresh_token = "stale-refresh-token"
    fake_creds.refresh.side_effect = RefreshError(
        "invalid_grant: Token has been expired or revoked."
    )

    with patch("gsc_mcp.auth._load_oauth_token", return_value=fake_creds):
        with pytest.raises(RuntimeError, match="No credentials"):
            auth._get_oauth_creds(constants.SCOPES_GSC, token_path)

    assert not token_path.exists()


def test_get_searchconsole_service_via_service_account(tmp_path, monkeypatch):
    sa_file = tmp_path / "sa.json"
    sa_file.write_text("{}")
    monkeypatch.setenv("GSC_SERVICE_ACCOUNT_PATH", str(sa_file))
    monkeypatch.delenv("GSC_CREDENTIALS_PATH", raising=False)

    fake_creds = MagicMock()

    with patch("gsc_mcp.auth.service_account") as mock_sa, \
         patch("gsc_mcp.auth.build", return_value=MagicMock()):
        mock_sa.Credentials.from_service_account_file.return_value = fake_creds
        svc = auth.get_searchconsole_service()
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
