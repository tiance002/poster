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
