from datetime import datetime, timezone

from app.repository import SettingsRepository
from app.service import MailboxProcessor
from app.types import AnalysisResult, EmailMessage, MailboxSettings


class FakeGateway:
    def __init__(self, messages: list[EmailMessage]) -> None:
        self.messages = messages
        self.moved: list[EmailMessage] = []

    def fetch_unseen(self, settings: MailboxSettings) -> list[EmailMessage]:
        return self.messages

    def fetch_history(self, settings: MailboxSettings, sender: str, limit: int) -> list[EmailMessage]:
        return []

    def move_to_trash(self, settings: MailboxSettings, messages: list[EmailMessage]) -> int:
        self.moved.extend(messages)
        return len(messages)


class FakeAnalyzer:
    def analyze(self, message, history, settings) -> AnalysisResult:
        return AnalysisResult("Summary", "request", "No risk", "Draft reply")


def test_processor_blocks_access_without_consent(tmp_path) -> None:
    repository = SettingsRepository(tmp_path / "agent.sqlite3")
    settings = MailboxSettings.minimal(consent_granted=False)
    repository.save_settings(settings)

    result = MailboxProcessor(repository, FakeGateway([]), FakeAnalyzer()).run()

    assert result.status == "blocked"


def test_processor_only_analyzes_whitelisted_unseen_message(tmp_path) -> None:
    repository = SettingsRepository(tmp_path / "agent.sqlite3")
    settings = MailboxSettings.minimal(consent_granted=True, allow_from=("trusted@example.com",))
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
