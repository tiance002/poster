from datetime import datetime, timedelta, timezone

from app.cleanup import select_stale_verification_codes
from app.types import EmailMessage


def message(sender: str, subject: str, minutes_ago: int) -> EmailMessage:
    return EmailMessage(
        uid=str(minutes_ago),
        uid_validity="1",
        message_id=f"{minutes_ago}@example.com",
        sender=sender,
        recipients=("agent@qq.com",),
        subject=subject,
        body="Your verification code is 123456.",
        sent_at=datetime.now(timezone.utc) - timedelta(minutes=minutes_ago),
    )


def test_cleanup_keeps_newest_code_and_selects_only_old_ones() -> None:
    newest = message("system@example.com", "Verification code", 10)
    old = message("system@example.com", "Verification code", 80)
    other_sender = message("other@example.com", "Verification code", 100)

    selected = select_stale_verification_codes(
        [newest, old, other_sender], now=datetime.now(timezone.utc)
    )

    assert selected == [old]


def test_cleanup_ignores_regular_email() -> None:
    regular = message("system@example.com", "Monthly account update", 200)
    regular = regular.with_body("Your account preferences were updated.")

    assert select_stale_verification_codes([regular], now=datetime.now(timezone.utc)) == []


def test_cleanup_recognizes_oracle_chinese_one_time_code() -> None:
    old = EmailMessage(
        uid="1", uid_validity="1", message_id="oracle-1", sender="no-reply@identity.oci.oraclecloud.com",
        recipients=("agent@qq.com",), subject="您的 Oracle 一次性验证码", body="您好，您的 Oracle 账户一次性验证码是：1527。",
        sent_at=datetime.now(timezone.utc) - timedelta(hours=2),
    )
    newest = EmailMessage(
        uid="2", uid_validity="1", message_id="oracle-2", sender=old.sender,
        recipients=old.recipients, subject=old.subject, body="您好，您的 Oracle 账户一次性验证码是：6185。",
        sent_at=datetime.now(timezone.utc) - timedelta(minutes=10),
    )

    assert select_stale_verification_codes([old, newest], now=datetime.now(timezone.utc)) == [old]
