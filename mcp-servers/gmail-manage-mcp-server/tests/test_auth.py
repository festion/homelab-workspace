"""Tests for Gmail OAuth2 auth module."""
import os
import tempfile
import pytest
from gmail_manage.auth import get_credentials_dir, build_service


def test_get_credentials_dir_default():
    """Default credentials dir is ~/.config/gmail-manage/."""
    env_backup = os.environ.pop("GMAIL_CREDENTIALS_DIR", None)
    try:
        result = get_credentials_dir()
        assert result.endswith(".config/gmail-manage")
    finally:
        if env_backup:
            os.environ["GMAIL_CREDENTIALS_DIR"] = env_backup


def test_get_credentials_dir_from_env():
    """GMAIL_CREDENTIALS_DIR env var overrides default."""
    os.environ["GMAIL_CREDENTIALS_DIR"] = "/tmp/test-gmail-creds"
    try:
        result = get_credentials_dir()
        assert result == "/tmp/test-gmail-creds"
    finally:
        del os.environ["GMAIL_CREDENTIALS_DIR"]


def test_build_service_missing_credentials():
    """build_service raises FileNotFoundError when credentials.json is missing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        os.environ["GMAIL_CREDENTIALS_DIR"] = tmpdir
        try:
            with pytest.raises(FileNotFoundError, match="credentials.json"):
                build_service()
        finally:
            del os.environ["GMAIL_CREDENTIALS_DIR"]
