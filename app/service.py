from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol

from app.cleanup import select_stale_verification_codes
from app.repository import SettingsRepository
from app.types import AnalysisResult, EmailMessage, MailboxSettings, ProcessedResult, RunResult


class MailGateway(Protocol):
    def fetch_unseen(self, settings: MailboxSettings) -> list[EmailMessage]: ...
    def fetch_recent_inbox(self, settings: MailboxSettings, limit: int) -> list[EmailMessage]: ...
    def fetch_history(self, settings: MailboxSettings, sender: str, limit: int) -> list[EmailMessage]: ...
    def move_to_trash(self, settings: MailboxSettings, messages: list[EmailMessage]) -> int: ...


class Analyzer(Protocol):
    def analyze(
        self, message: EmailMessage, history: list[EmailMessage], settings: MailboxSettings
    ) -> AnalysisResult: ...


class MailboxProcessor:
    def __init__(self, repository: SettingsRepository, gateway: MailGateway, analyzer: Analyzer) -> None:
        self.repository = repository
        self.gateway = gateway
        self.analyzer = analyzer

    def run(self, runtime_settings: MailboxSettings | None = None) -> RunResult:
        settings = runtime_settings or self.repository.get_settings()
        if settings is None:
            return RunResult("blocked", message="请先保存邮箱配置，再执行检查。")
        if not settings.consent_granted:
            return RunResult("blocked", message="邮箱访问授权未开启，系统没有连接邮箱。")
        if not settings.allow_from:
            return RunResult("blocked", message="请填写允许发送者；白名单为空时系统不会连接邮箱。")
        messages = self.gateway.fetch_unseen(settings)
        allowed = {address.strip().lower() for address in settings.allow_from}
        processed: list[ProcessedResult] = []
        ignored = 0
        for message in messages:
            if message.sender.strip().lower() not in allowed:
                ignored += 1
                continue
            if self.repository.was_processed(settings.email_address, message.uid_validity, message.uid):
                ignored += 1
                continue
            history = self.gateway.fetch_history(settings, message.sender, limit=3)
            analysis = self.analyzer.analyze(message, history, settings)
            self.repository.record_processed(settings.email_address, message.uid_validity, message.uid, message.message_id)
            processed.append(ProcessedResult(message, analysis))
        recent_messages = self.gateway.fetch_recent_inbox(settings, limit=100)
        stale = select_stale_verification_codes(recent_messages, now=datetime.now(timezone.utc))
        moved = self.gateway.move_to_trash(settings, stale) if stale else 0
        if processed:
            message = ""
        elif ignored:
            message = f"没有符合条件的未读邮件；已跳过 {ignored} 封，原因是发件人不在白名单或邮件已处理。"
        else:
            message = "收件箱中没有未读邮件。"
        return RunResult("completed", len(processed), ignored, moved, message, tuple(processed))
