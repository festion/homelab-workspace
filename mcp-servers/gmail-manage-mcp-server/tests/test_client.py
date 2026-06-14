"""Tests for Gmail API client -- uses mocks, no real API calls."""
from unittest.mock import MagicMock

import pytest

from gmail_manage.client import GmailClient


@pytest.fixture
def mock_service():
    """Create a mock Gmail API service."""
    return MagicMock()


@pytest.fixture
def client(mock_service):
    """Create a GmailClient with a mock service."""
    return GmailClient(mock_service)


def test_modify_labels(client, mock_service):
    """modify_labels calls messages().modify() with correct args."""
    mock_service.users().messages().modify().execute.return_value = {
        "id": "abc123",
        "labelIds": ["INBOX"],
    }
    result = client.modify_labels("abc123", add=["INBOX"], remove=["SPAM"])
    mock_service.users().messages().modify.assert_called_with(
        userId="me",
        id="abc123",
        body={"addLabelIds": ["INBOX"], "removeLabelIds": ["SPAM"]},
    )


def test_trash_message(client, mock_service):
    """trash_message calls messages().trash()."""
    mock_service.users().messages().trash().execute.return_value = {"id": "abc123"}
    result = client.trash_message("abc123")
    mock_service.users().messages().trash.assert_called_with(
        userId="me", id="abc123"
    )


def test_mark_read(client, mock_service):
    """mark_read removes UNREAD label."""
    mock_service.users().messages().modify().execute.return_value = {"id": "abc123"}
    client.mark_read(["abc123"])
    mock_service.users().messages().modify.assert_called_with(
        userId="me",
        id="abc123",
        body={"removeLabelIds": ["UNREAD"]},
    )


def test_mark_not_spam(client, mock_service):
    """mark_not_spam removes SPAM, adds INBOX."""
    mock_service.users().messages().modify().execute.return_value = {"id": "abc123"}
    client.mark_not_spam(["abc123"])
    mock_service.users().messages().modify.assert_called_with(
        userId="me",
        id="abc123",
        body={"addLabelIds": ["INBOX"], "removeLabelIds": ["SPAM"]},
    )


def test_send_draft(client, mock_service):
    """send_draft calls drafts().send()."""
    mock_service.users().drafts().send().execute.return_value = {
        "id": "draft123",
        "message": {"id": "msg456"},
    }
    result = client.send_draft("draft123")
    mock_service.users().drafts().send.assert_called_with(
        userId="me", body={"id": "draft123"}
    )


def test_resolve_label_name(client, mock_service):
    """resolve_label_name maps label names to IDs."""
    mock_service.users().labels().list().execute.return_value = {
        "labels": [
            {"id": "INBOX", "name": "INBOX"},
            {"id": "Label_42", "name": "MyLabel"},
        ]
    }
    assert client.resolve_label_name("MyLabel") == "Label_42"
    assert client.resolve_label_name("INBOX") == "INBOX"
