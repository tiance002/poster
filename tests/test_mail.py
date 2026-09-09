from datetime import datetime, timezone

from app.mail import ImapMailGateway
from app.types import MailboxSettings


class FakeFolder:
    def __init__(self) -> None:
        self.selected = []

    def status(self, folder: str):
        return {"UIDVALIDITY": "2026"}

    def list(self):
        return [type("Folder", (), {"name": "Sent", "flags": ("\\Sent",)})()]

    def set(self, folder: str):
        self.selected.append(folder)


class FakeMessage:
    uid = "10"
    headers = {"message-id": ("<mail-10@example.com>",)}
    from_ = "Trusted Sender <trusted@example.com>"
    to = ("agent@qq.com",)
    subject = "A new message"
    text = "Plain text body"
    html = ""
    date = datetime(2026, 9, 9, tzinfo=timezone.utc)


class FakeMailbox:
    def __init__(self) -> None:
        self.folder = FakeFolder()
        self.fetch_arguments = None
        self.deleted = []
        self.moves = []

    def login(self, *_args, **_kwargs):
        return self

    def fetch(self, *args, **kwargs):
        self.fetch_arguments = (args, kwargs)
        return [FakeMessage()]

    def move(self, uids, folder):
        self.moves.append((uids, folder))

    def logout(self):
        return None


def settings() -> MailboxSettings:
    return MailboxSettings.minimal(True, ("trusted@example.com",)).__class__(
        provider_id="qq",
        email_address="agent@qq.com",
        imap_authorization_code="authorization-code",
        consent_granted=True,
        allow_from=("trusted@example.com",),
        llm_base_url="https://llm.example/v1",
        llm_api_key="key",
        llm_model="model",
        polling_seconds=0,
    )


def test_gateway_fetches_unseen_without_marking_messages_seen() -> None:
    mailbox = FakeMailbox()
    gateway = ImapMailGateway(mailbox_factory=lambda _host: mailbox)

    messages = gateway.fetch_unseen(settings())

    assert messages[0].sender == "trusted@example.com"
    assert messages[0].uid_validity == "2026"
    assert mailbox.fetch_arguments[1]["mark_seen"] is False
    assert "UNSEEN" in str(mailbox.fetch_arguments[0][0])


def test_gateway_moves_cleanup_messages_to_discovered_trash() -> None:
    mailbox = FakeMailbox()
    gateway = ImapMailGateway(mailbox_factory=lambda _host: mailbox)
    messages = gateway.fetch_unseen(settings())

    moved = gateway.move_to_trash(settings(), messages)

    assert moved == 1
    assert mailbox.moves == [(["10"], "Trash")]


def test_gateway_includes_sent_messages_in_conversation_history() -> None:
    mailbox = FakeMailbox()
    gateway = ImapMailGateway(mailbox_factory=lambda _host: mailbox)

    history = gateway.fetch_history(settings(), "trusted@example.com", limit=3)

    assert len(history) == 2
    assert mailbox.folder.selected == ["Sent"]
    assert mailbox.fetch_arguments[1]["mark_seen"] is False
