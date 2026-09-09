from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime


@dataclass(frozen=True)
class MailboxSettings:
    provider_id: str
    email_address: str
    imap_authorization_code: str
    consent_granted: bool
    allow_from: tuple[str, ...]
    llm_base_url: str
    llm_api_key: str
    llm_model: str
    polling_seconds: int

    @classmethod
    def minimal(
        cls, consent_granted: bool, allow_from: tuple[str, ...] = ()
    ) -> "MailboxSettings":
        return cls(
            provider_id="qq",
            email_address="agent@qq.com",
            imap_authorization_code="",
            consent_granted=consent_granted,
            allow_from=allow_from,
            llm_base_url="https://api.openai.com/v1",
            llm_api_key="",
            llm_model="gpt-4o-mini",
            polling_seconds=0,
        )

    def without_secrets(self) -> "MailboxSettings":
        return replace(self, imap_authorization_code="", llm_api_key="")


@dataclass(frozen=True)
class EmailMessage:
    uid: str
    uid_validity: str
    message_id: str
    sender: str
    recipients: tuple[str, ...]
    subject: str
    body: str
    sent_at: datetime

    def with_body(self, body: str) -> "EmailMessage":
        return replace(self, body=body)

    def with_sender(self, sender: str) -> "EmailMessage":
        return replace(self, sender=sender)


@dataclass(frozen=True)
class AnalysisResult:
    summary: str
    category: str
    risk_note: str
    reply_draft: str


@dataclass(frozen=True)
class ProcessedResult:
    message: EmailMessage
    analysis: AnalysisResult


@dataclass(frozen=True)
class RunResult:
    status: str
    processed_count: int = 0
    ignored_count: int = 0
    moved_to_trash_count: int = 0
    message: str = ""
    items: tuple[ProcessedResult, ...] = ()
