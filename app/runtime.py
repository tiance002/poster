from app.types import MailboxSettings


class RuntimeSettingsStore:
    """Keeps mailbox authorization and model keys only in this running process."""

    def __init__(self) -> None:
        self._settings: MailboxSettings | None = None

    def save(self, settings: MailboxSettings) -> None:
        self._settings = settings

    def get(self) -> MailboxSettings | None:
        return self._settings
