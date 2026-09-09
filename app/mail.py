from __future__ import annotations

from datetime import datetime, timezone
from email.utils import parseaddr
from typing import Callable

from app.providers import get_provider
from app.types import EmailMessage, MailboxSettings


class ImapMailGateway:
    """IMAP access constrained to unread fetches and Trash moves for code cleanup."""

    def __init__(self, mailbox_factory: Callable | None = None) -> None:
        if mailbox_factory is None:
            from imap_tools import MailBox

            mailbox_factory = MailBox
        self.mailbox_factory = mailbox_factory

    def _login(self, settings: MailboxSettings):
        provider = get_provider(settings.provider_id)
        return self.mailbox_factory(provider.imap_host).login(
            settings.email_address,
            settings.imap_authorization_code,
            initial_folder="INBOX",
        )

    def fetch_unseen(self, settings: MailboxSettings) -> list[EmailMessage]:
        return self._fetch_inbox(settings, "UNSEEN")

    def fetch_recent_inbox(self, settings: MailboxSettings, limit: int | None) -> list[EmailMessage]:
        return self._fetch_inbox(settings, "ALL", limit=limit)

    def _fetch_inbox(
        self, settings: MailboxSettings, criteria: str, limit: int | None = None
    ) -> list[EmailMessage]:
        mailbox = self._login(settings)
        try:
            uid_validity = str(mailbox.folder.status("INBOX").get("UIDVALIDITY", "unknown"))
            return [
                self._to_email(message, uid_validity)
                for message in mailbox.fetch(
                    criteria, mark_seen=False, reverse=True, limit=limit, bulk=20
                )
            ]
        finally:
            mailbox.logout()

    def fetch_history(self, settings: MailboxSettings, sender: str, limit: int) -> list[EmailMessage]:
        mailbox = self._login(settings)
        try:
            uid_validity = str(mailbox.folder.status("INBOX").get("UIDVALIDITY", "unknown"))
            escaped_sender = sender.replace('"', "")
            inbox_items = [
                self._to_email(message, uid_validity)
                for message in mailbox.fetch(
                    f'FROM "{escaped_sender}"', mark_seen=False, reverse=True, limit=limit, bulk=20
                )
            ]
            sent_items: list[EmailMessage] = []
            sent_folder = self._sent_folder(mailbox)
            if sent_folder:
                mailbox.folder.set(sent_folder)
                sent_items = [
                    self._to_email(message, uid_validity)
                    for message in mailbox.fetch(
                        f'TO "{escaped_sender}"', mark_seen=False, reverse=True, limit=limit, bulk=20
                    )
                ]
            return sorted(inbox_items + sent_items, key=lambda item: item.sent_at, reverse=True)[:limit]
        finally:
            mailbox.logout()

    @staticmethod
    def _sent_folder(mailbox) -> str | None:
        try:
            for folder in mailbox.folder.list():
                if "\\Sent" in getattr(folder, "flags", ()):
                    return folder.name
        except AttributeError:
            pass
        return None

    def move_to_trash(self, settings: MailboxSettings, messages: list[EmailMessage]) -> int:
        if not messages:
            return 0
        mailbox = self._login(settings)
        try:
            trash_folder = self._trash_folder(mailbox)
            mailbox.move([message.uid for message in messages], trash_folder)
            return len(messages)
        finally:
            mailbox.logout()

    @staticmethod
    def _trash_folder(mailbox) -> str:
        try:
            for folder in mailbox.folder.list():
                if "\\Trash" in getattr(folder, "flags", ()):
                    return folder.name
        except AttributeError:
            pass
        return "Trash"

    @staticmethod
    def _to_email(message, uid_validity: str) -> EmailMessage:
        _, sender = parseaddr(message.from_)
        recipients = tuple(parseaddr(value)[1] or value for value in getattr(message, "to", ()))
        headers = getattr(message, "headers", {})
        message_ids = headers.get("message-id", ()) if hasattr(headers, "get") else ()
        message_id = message_ids[0] if message_ids else f"uid-{message.uid}"
        sent_at = getattr(message, "date", None) or datetime.now(timezone.utc)
        if sent_at.tzinfo is None:
            sent_at = sent_at.replace(tzinfo=timezone.utc)
        return EmailMessage(
            uid=str(message.uid),
            uid_validity=uid_validity,
            message_id=message_id.strip("<>"),
            sender=(sender or message.from_).strip().lower(),
            recipients=recipients,
            subject=(getattr(message, "subject", "") or "").strip(),
            body=(getattr(message, "text", "") or getattr(message, "html", "") or "").strip(),
            sent_at=sent_at,
        )
