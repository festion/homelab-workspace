"""Integration tests — require valid OAuth credentials. Skip in CI."""
import os
import pytest
from gmail_manage.auth import build_service
from gmail_manage.client import GmailClient

pytestmark = pytest.mark.skipif(
    not os.path.exists(
        os.path.join(
            os.environ.get("GMAIL_CREDENTIALS_DIR", os.path.expanduser("~/.config/gmail-manage")),
            "token.json",
        )
    ),
    reason="No Gmail token.json — skip integration tests",
)


@pytest.fixture
def client():
    service = build_service()
    return GmailClient(service)


def test_resolve_inbox_label(client):
    """INBOX label resolves to itself."""
    assert client.resolve_label_name("INBOX") == "INBOX"


def test_resolve_spam_label(client):
    """SPAM label resolves to itself."""
    assert client.resolve_label_name("SPAM") == "SPAM"


def test_label_cache_populated(client):
    """After resolving, label cache is populated."""
    client.resolve_label_name("INBOX")
    assert client._label_cache is not None
    assert len(client._label_cache) > 0
