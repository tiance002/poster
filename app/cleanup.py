from __future__ import annotations

import re
from collections import defaultdict
from datetime import datetime, timedelta

from app.types import EmailMessage


CODE_PATTERN = re.compile(
    r"(?:verification\s*code|验证码|校验码|动态码|一次性验证码|one[- ]?time\s*(?:password|code)|otp)",
    re.IGNORECASE,
)
NUMBER_PATTERN = re.compile(r"\b\d{4,8}\b")


def is_verification_code(message: EmailMessage) -> bool:
    text = f"{message.subject}\n{message.body}"
    return bool(CODE_PATTERN.search(text) and NUMBER_PATTERN.search(text))


def select_stale_verification_codes(
    messages: list[EmailMessage], now: datetime
) -> list[EmailMessage]:
    grouped: dict[str, list[EmailMessage]] = defaultdict(list)
    for message in messages:
        if is_verification_code(message):
            grouped[message.sender.strip().lower()].append(message)

    stale: list[EmailMessage] = []
    threshold = now - timedelta(hours=1)
    for sender_messages in grouped.values():
        ordered = sorted(sender_messages, key=lambda message: message.sent_at, reverse=True)
        stale.extend(message for message in ordered[1:] if message.sent_at < threshold)
    return stale
