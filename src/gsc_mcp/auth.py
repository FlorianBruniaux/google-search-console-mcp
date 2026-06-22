import json
import os
from pathlib import Path

from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from platformdirs import user_data_dir

from google.analytics.data_v1beta import BetaAnalyticsDataClient

from gsc_mcp.constants import SCOPES_GSC, SCOPES_INDEXING, SCOPES_GA4

_TOKEN_DIR = Path(user_data_dir("gsc-mcp"))
_TOKEN_GSC = _TOKEN_DIR / "token_gsc.json"
_TOKEN_INDEXING = _TOKEN_DIR / "token_indexing.json"


def _load_oauth_token(token_path: Path) -> Credentials | None:
    if not token_path.exists():
        return None
    data = json.loads(token_path.read_text())
    return Credentials.from_authorized_user_info(data)


def _save_oauth_token(token_path: Path, creds: Credentials) -> None:
    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(creds.to_json())


def _get_service_account_creds(scopes: list[str]) -> service_account.Credentials:
    sa_path = os.environ.get("GSC_SERVICE_ACCOUNT_PATH", "")
    if not sa_path or not Path(sa_path).exists():
        raise RuntimeError(
            f"No credentials: GSC_SERVICE_ACCOUNT_PATH not set or file not found: {sa_path!r}"
        )
    return service_account.Credentials.from_service_account_file(sa_path, scopes=scopes)


def _get_oauth_creds(scopes: list[str], token_path: Path) -> Credentials:
    creds = _load_oauth_token(token_path)

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        _save_oauth_token(token_path, creds)
        return creds

    credentials_path = os.environ.get("GSC_CREDENTIALS_PATH", "")
    if not credentials_path or not Path(credentials_path).exists():
        raise RuntimeError(
            f"No credentials: GSC_CREDENTIALS_PATH not set or file not found: {credentials_path!r}"
        )

    flow = InstalledAppFlow.from_client_secrets_file(credentials_path, scopes)
    creds = flow.run_local_server(port=0)
    _save_oauth_token(token_path, creds)
    return creds


def _resolve_creds(scopes: list[str], token_path: Path):
    skip_oauth = os.environ.get("GSC_SKIP_OAUTH", "false").lower() in ("1", "true", "yes")
    sa_path = os.environ.get("GSC_SERVICE_ACCOUNT_PATH", "")

    if sa_path:
        return _get_service_account_creds(scopes)

    if skip_oauth:
        raise RuntimeError(
            "No credentials: GSC_SKIP_OAUTH=true but GSC_SERVICE_ACCOUNT_PATH is not set"
        )

    return _get_oauth_creds(scopes, token_path)


def get_gsc_service():
    creds = _resolve_creds(SCOPES_GSC, _TOKEN_GSC)
    return build("webmasters", "v3", credentials=creds)


def get_searchconsole_service():
    creds = _resolve_creds(SCOPES_GSC, _TOKEN_GSC)
    return build("searchconsole", "v1", credentials=creds)


def get_indexing_service():
    creds = _resolve_creds(SCOPES_INDEXING, _TOKEN_INDEXING)
    return build("indexing", "v3", credentials=creds)


_TOKEN_GA4 = _TOKEN_DIR / "token_ga4.json"


def get_ga4_property_id() -> str:
    prop = os.environ.get("GA4_PROPERTY_ID", "").strip()
    if not prop:
        raise RuntimeError(
            "No GA4 config: GA4_PROPERTY_ID environment variable is not set"
        )
    return prop if prop.startswith("properties/") else f"properties/{prop}"


def get_ga4_service() -> BetaAnalyticsDataClient:
    creds = _resolve_creds(SCOPES_GA4, _TOKEN_GA4)
    return BetaAnalyticsDataClient(credentials=creds)
