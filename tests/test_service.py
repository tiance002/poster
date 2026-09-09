from dataclasses import replace
from datetime import datetime, timedelta, timezone

from app.repository import SettingsRepository
from app.service import MailboxProcessor
from app.types import AnalysisResult, EmailMessage, MailboxSettings


class FakeGateway:
    def __init__(self, messages: list[EmailMessage], recent_messages: list[EmailMessage] | None = None) -> None:
        self.messages = messages
        self.recent_messages = recent_messages or []
        self.moved: list[EmailMessage] = []

    def fetch_unseen(self, settings: MailboxSettings) -> list[EmailMessage]:
        return self.messages

    def fetch_history(self, settings: MailboxSettings, sender: str, limit: int) -> list[EmailMessage]:
        return []

    def fetch_recent_inbox(self, settings: MailboxSettings, limit: int | None) -> list[EmailMessage]:
        return self.recent_messages

    def move_to_trash(self, settings: MailboxSettings, messages: list[EmailMessage]) -> int:
        self.moved.extend(messages)
        return len(messages)


class FakeAnalyzer:
    def analyze(self, message, history, settings) -> AnalysisResult:
        return AnalysisResult("Summary", "request", "No risk", "Draft reply")


class FailingGateway(FakeGateway):
    def fetch_unseen(self, settings: MailboxSettings) -> list[EmailMessage]:
        raise RuntimeError("authentication failed")


def configured_settings(allow_from: tuple[str, ...] = ("trusted@example.com",)) -> MailboxSettings:
    return replace(
        MailboxSettings.minimal(consent_granted=True, allow_from=allow_from),
        imap_authorization_code="test-authorization-code",
    )


def test_processor_blocks_access_without_consent(tmp_path) -> None:
    repository = SettingsRepository(tmp_path / "agent.sqlite3")
    settings = MailboxSettings.minimal(consent_granted=False)
    repository.save_settings(settings)

    result = MailboxProcessor(repository, FakeGateway([]), FakeAnalyzer()).run()

    assert result.status == "blocked"


def test_processor_explains_when_imap_authorization_code_is_missing(tmp_path) -> None:
    repository = SettingsRepository(tmp_path / "agent.sqlite3")
    settings = MailboxSettings.minimal(consent_granted=True, allow_from=("trusted@example.com",))
    repository.save_settings(settings)

    result = MailboxProcessor(repository, FakeGateway([]), FakeAnalyzer()).run(settings)

    assert result.status == "blocked"
    assert "IMAP 授权码" in result.message


def test_processor_returns_safe_message_when_mailbox_connection_fails(tmp_path) -> None:
    repository = SettingsRepository(tmp_path / "agent.sqlite3")
    settings = MailboxSettings(
        provider_id="qq", email_address="agent@qq.com", imap_authorization_code="code",
        consent_granted=True, allow_from=("trusted@example.com",), llm_base_url="https://llm.example/v1",
        llm_api_key="key", llm_model="model", polling_seconds=0,
    )

    result = MailboxProcessor(repository, FailingGateway([]), FakeAnalyzer()).run(settings)

    assert result.status == "failed"
    assert "邮箱连接失败" in result.message


def test_processor_only_analyzes_whitelisted_unseen_message(tmp_path) -> None:
    repository = SettingsRepository(tmp_path / "agent.sqlite3")
    settings = configured_settings()
    repository.save_settings(settings)
    trusted = EmailMessage(
        uid="5", uid_validity="1", message_id="id-5", sender="trusted@example.com",
        recipients=("agent@qq.com",), subject="Need help", body="Please help", sent_at=datetime.now(timezone.utc),
    )
    untrusted = trusted.with_sender("stranger@example.com")

    result = MailboxProcessor(repository, FakeGateway([trusted, untrusted]), FakeAnalyzer()).run()

    assert result.status == "completed"
    assert result.processed_count == 1
    assert result.ignored_count == 1


def test_processor_cleans_stale_seen_verification_codes_from_recent_inbox(tmp_path) -> None:
    repository = SettingsRepository(tmp_path / "agent.sqlite3")
    settings = configured_settings()
    repository.save_settings(settings)
    now = datetime.now(timezone.utc)
    newest = EmailMessage("2", "1", "new", "codes@example.com", ("agent@qq.com",), "Verification code", "Your verification code is 123456", now - timedelta(minutes=10))
    stale = EmailMessage("1", "1", "old", "codes@example.com", ("agent@qq.com",), "Verification code", "Your verification code is 654321", now - timedelta(hours=2))
    gateway = FakeGateway([], recent_messages=[newest, stale])

    result = MailboxProcessor(repository, gateway, FakeAnalyzer()).run(settings)

    assert result.moved_to_trash_count == 1
    assert gateway.moved == [stale]


def test_processor_explains_when_no_unread_message_is_eligible(tmp_path) -> None:
    repository = SettingsRepository(tmp_path / "agent.sqlite3")
    settings = configured_settings()
    repository.save_settings(settings)
    untrusted = EmailMessage(
        "9", "1", "untrusted", "newsletter@example.com", ("agent@qq.com",),
        "News", "A message", datetime.now(timezone.utc),
    )

    result = MailboxProcessor(repository, FakeGateway([untrusted]), FakeAnalyzer()).run(settings)

    assert result.processed_count == 0
    assert "发件人不在白名单或邮件已处理" in result.message
