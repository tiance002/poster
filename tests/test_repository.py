from app.repository import SettingsRepository
from app.types import MailboxSettings


def test_processed_key_is_idempotent(tmp_path) -> None:
    repository = SettingsRepository(tmp_path / "agent.sqlite3")
    repository.record_processed("primary", "37", "42", "message@example.com")

    assert repository.was_processed("primary", "37", "42") is True
    assert repository.was_processed("primary", "37", "43") is False


def test_settings_round_trip_does_not_return_secret(tmp_path) -> None:
    repository = SettingsRepository(tmp_path / "agent.sqlite3")
    settings = MailboxSettings(
        provider_id="qq",
        email_address="agent@qq.com",
        imap_authorization_code="never-return-this",
        consent_granted=True,
        allow_from=("trusted@example.com",),
        llm_base_url="https://llm.example/v1",
        llm_api_key="never-return-this-either",
        llm_model="test-model",
        polling_seconds=0,
    )
    repository.save_settings(settings)

    loaded = repository.get_settings()

    assert loaded is not None
    assert loaded.email_address == "agent@qq.com"
    assert loaded.imap_authorization_code == ""
    assert loaded.llm_api_key == ""
