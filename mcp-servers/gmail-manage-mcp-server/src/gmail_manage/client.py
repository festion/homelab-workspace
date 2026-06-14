"""Gmail API client wrapping google-api-python-client."""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class GmailClient:
    """Wraps Gmail API service for message modification operations."""

    def __init__(self, service):
        self._service = service
        self._label_cache: dict[str, str] | None = None

    def _refresh_label_cache(self) -> dict[str, str]:
        """Fetch all labels and cache name->id mapping."""
        result = self._service.users().labels().list(userId="me").execute()
        labels = result.get("labels", [])
        self._label_cache = {lb["name"]: lb["id"] for lb in labels}
        return self._label_cache

    def resolve_label_name(self, name: str) -> str:
        """Resolve a label name to its ID. Returns as-is if already an ID."""
        if self._label_cache is None:
            self._refresh_label_cache()
        if name in self._label_cache:
            return self._label_cache[name]
        # Might be stale cache -- refresh once
        self._refresh_label_cache()
        if name in self._label_cache:
            return self._label_cache[name]
        # Assume it's already an ID
        return name

    def modify_labels(
        self,
        message_id: str,
        add: list[str] | None = None,
        remove: list[str] | None = None,
    ) -> dict[str, Any]:
        """Add/remove labels on a message."""
        body: dict[str, list[str]] = {}
        if add:
            body["addLabelIds"] = add
        if remove:
            body["removeLabelIds"] = remove
        return (
            self._service.users()
            .messages()
            .modify(userId="me", id=message_id, body=body)
            .execute()
        )

    def trash_message(self, message_id: str) -> dict[str, Any]:
        """Move a message to trash."""
        return (
            self._service.users()
            .messages()
            .trash(userId="me", id=message_id)
            .execute()
        )

    def mark_read(self, message_ids: list[str]) -> list[dict[str, Any]]:
        """Remove UNREAD label from messages."""
        results = []
        for mid in message_ids:
            result = self.modify_labels(mid, remove=["UNREAD"])
            results.append(result)
        return results

    def mark_not_spam(self, message_ids: list[str]) -> list[dict[str, Any]]:
        """Remove SPAM label, add INBOX label."""
        results = []
        for mid in message_ids:
            result = self.modify_labels(mid, add=["INBOX"], remove=["SPAM"])
            results.append(result)
        return results

    def send_draft(self, draft_id: str) -> dict[str, Any]:
        """Send an existing draft."""
        return (
            self._service.users()
            .drafts()
            .send(userId="me", body={"id": draft_id})
            .execute()
        )

    def create_filter(
        self,
        criteria: dict[str, str],
        actions: dict[str, Any],
    ) -> dict[str, Any]:
        """Create a Gmail filter.

        Args:
            criteria: Dict with keys like "from", "to", "subject", "query".
            actions: Dict with convenience keys mapped to Gmail API format.
        """
        action_body: dict[str, Any] = {}
        if "add_labels" in actions:
            action_body["addLabelIds"] = [
                self.resolve_label_name(n) for n in actions["add_labels"]
            ]
        if "remove_labels" in actions:
            action_body["removeLabelIds"] = [
                self.resolve_label_name(n) for n in actions["remove_labels"]
            ]

        for key in ("archive", "mark_read", "trash", "never_spam", "star"):
            if actions.get(key):
                if key == "archive":
                    action_body.setdefault("removeLabelIds", []).append("INBOX")
                elif key == "mark_read":
                    action_body.setdefault("removeLabelIds", []).append("UNREAD")
                elif key == "trash":
                    action_body.setdefault("addLabelIds", []).append("TRASH")
                elif key == "star":
                    action_body.setdefault("addLabelIds", []).append("STARRED")

        filter_body = {
            "criteria": criteria,
            "action": action_body,
        }

        return (
            self._service.users()
            .settings()
            .filters()
            .create(userId="me", body=filter_body)
            .execute()
        )
