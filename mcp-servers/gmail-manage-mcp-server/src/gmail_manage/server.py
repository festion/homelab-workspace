# src/gmail_manage/server.py
"""Gmail Manage MCP Server — message modification for Claude Code."""

import sys
import logging
from typing import Any
from mcp.server.fastmcp import FastMCP
from gmail_manage.auth import build_service
from gmail_manage.client import GmailClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)],
)
logger = logging.getLogger(__name__)

mcp = FastMCP("Gmail Manage")

_client: GmailClient | None = None


def get_client() -> GmailClient:
    """Get or create the Gmail client."""
    global _client
    if _client is None:
        service = build_service()
        _client = GmailClient(service)
        logger.info("Gmail client initialized")
    return _client


@mcp.tool()
def modify_labels(
    message_id: str,
    add_labels: list[str] | None = None,
    remove_labels: list[str] | None = None,
) -> dict[str, Any]:
    """Add or remove labels on a Gmail message.

    Accepts label names (e.g., "MyLabel") or system IDs (e.g., "INBOX", "SPAM").
    Label names are resolved to IDs automatically.

    Common operations:
    - Archive: remove_labels=["INBOX"]
    - Move to inbox: add_labels=["INBOX"]
    - Star: add_labels=["STARRED"]

    Args:
        message_id: Gmail message ID (from gmail_search_messages).
        add_labels: Label names/IDs to add.
        remove_labels: Label names/IDs to remove.
    """
    client = get_client()
    add_ids = [client.resolve_label_name(n) for n in (add_labels or [])]
    remove_ids = [client.resolve_label_name(n) for n in (remove_labels or [])]
    result = client.modify_labels(message_id, add=add_ids, remove=remove_ids)
    return {
        "message_id": message_id,
        "action": "modify_labels",
        "added": add_labels or [],
        "removed": remove_labels or [],
        "resulting_labels": result.get("labelIds", []),
    }


@mcp.tool()
def trash_message(message_id: str) -> dict[str, Any]:
    """Move a Gmail message to trash. Reversible — messages stay in trash for 30 days.

    Args:
        message_id: Gmail message ID (from gmail_search_messages).
    """
    client = get_client()
    client.trash_message(message_id)
    return {"message_id": message_id, "action": "trashed"}


@mcp.tool()
def mark_read(message_ids: list[str]) -> dict[str, Any]:
    """Mark one or more Gmail messages as read.

    Args:
        message_ids: List of Gmail message IDs.
    """
    client = get_client()
    client.mark_read(message_ids)
    return {
        "action": "mark_read",
        "count": len(message_ids),
        "message_ids": message_ids,
    }


@mcp.tool()
def mark_not_spam(message_ids: list[str]) -> dict[str, Any]:
    """Move messages out of spam back to inbox.

    Removes the SPAM label and adds the INBOX label for each message.

    Args:
        message_ids: List of Gmail message IDs (use gmail_search_messages with includeSpamTrash=true to find them).
    """
    client = get_client()
    client.mark_not_spam(message_ids)
    return {
        "action": "mark_not_spam",
        "count": len(message_ids),
        "message_ids": message_ids,
    }


@mcp.tool()
def send_draft(draft_id: str) -> dict[str, Any]:
    """Send an existing Gmail draft.

    Use with drafts created by the Claude.ai gmail_create_draft tool.
    The draft_id is returned by gmail_create_draft (NOT the messageId).

    Args:
        draft_id: Gmail draft ID (from gmail_create_draft response).
    """
    client = get_client()
    result = client.send_draft(draft_id)
    msg = result.get("message", {})
    return {
        "action": "sent",
        "draft_id": draft_id,
        "message_id": msg.get("id", ""),
        "thread_id": msg.get("threadId", ""),
        "label_ids": msg.get("labelIds", []),
    }


@mcp.tool()
def create_filter(
    criteria_from: str = "",
    criteria_to: str = "",
    criteria_subject: str = "",
    criteria_query: str = "",
    action_add_labels: list[str] | None = None,
    action_remove_labels: list[str] | None = None,
    action_archive: bool = False,
    action_mark_read: bool = False,
    action_trash: bool = False,
    action_never_spam: bool = False,
) -> dict[str, Any]:
    """Create a Gmail filter for future incoming messages.

    At least one criteria field and one action must be provided.

    Args:
        criteria_from: Match sender (e.g., "notifications@github.com").
        criteria_to: Match recipient.
        criteria_subject: Match subject.
        criteria_query: Gmail search query for advanced matching.
        action_add_labels: Labels to apply to matching messages.
        action_remove_labels: Labels to remove from matching messages.
        action_archive: Skip the inbox.
        action_mark_read: Mark as read.
        action_trash: Send to trash.
        action_never_spam: Never mark as spam.
    """
    client = get_client()

    criteria: dict[str, str] = {}
    if criteria_from:
        criteria["from"] = criteria_from
    if criteria_to:
        criteria["to"] = criteria_to
    if criteria_subject:
        criteria["subject"] = criteria_subject
    if criteria_query:
        criteria["query"] = criteria_query

    if not criteria:
        return {"error": "At least one criteria field is required."}

    actions: dict[str, Any] = {}
    if action_add_labels:
        actions["add_labels"] = action_add_labels
    if action_remove_labels:
        actions["remove_labels"] = action_remove_labels
    if action_archive:
        actions["archive"] = True
    if action_mark_read:
        actions["mark_read"] = True
    if action_trash:
        actions["trash"] = True
    if action_never_spam:
        actions["never_spam"] = True

    if not actions:
        return {"error": "At least one action is required."}

    result = client.create_filter(criteria, actions)
    return {
        "action": "filter_created",
        "filter_id": result.get("id", ""),
        "criteria": criteria,
        "actions": actions,
    }


def main():
    mcp.run()


if __name__ == "__main__":
    main()
