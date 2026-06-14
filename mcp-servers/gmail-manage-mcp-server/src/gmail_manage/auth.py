"""OAuth2 authentication for Gmail API."""

import os
import logging
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.settings.basic",
    "https://www.googleapis.com/auth/gmail.send",
]


def get_credentials_dir() -> str:
    """Return the directory where credentials.json and token.json live."""
    return os.environ.get(
        "GMAIL_CREDENTIALS_DIR",
        str(Path.home() / ".config" / "gmail-manage"),
    )


def _load_or_refresh_credentials(creds_dir: str) -> Credentials:
    """Load token.json, refresh if expired, or run OAuth flow."""
    token_path = os.path.join(creds_dir, "token.json")
    creds_path = os.path.join(creds_dir, "credentials.json")

    if not os.path.exists(creds_path):
        raise FileNotFoundError(
            f"credentials.json not found in {creds_dir}. "
            "Download it from GCP Console -> APIs & Services -> Credentials -> OAuth 2.0 Client IDs."
        )

    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            logger.info("Refreshing expired token...")
            creds.refresh(Request())
        else:
            logger.info("Running OAuth consent flow (browser will open)...")
            flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(token_path, "w") as f:
            f.write(creds.to_json())
        logger.info("Token saved to %s", token_path)

    return creds


def build_service():
    """Build and return an authenticated Gmail API service."""
    creds_dir = get_credentials_dir()
    creds = _load_or_refresh_credentials(creds_dir)
    return build("gmail", "v1", credentials=creds)
