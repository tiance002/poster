from app.repository import SettingsRepository
from app.types import MailboxSettings


def test_processed_key_is_idempotent(tmp_path) -> None:
    repository = SettingsRepository(tmp_path / "agent.sqlite3")
    repository.record_processed("primary", "37", "42", "message@example.com")

    assert repository.was_processed("primary", "37", "42") is True
    assert repository.was_processed("primary", "37", "43") is False


def test_settings_round_trip_restores_locally_encrypted_secrets(tmp_path) -> None:
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
    assert loaded.imap_authorization_code == "never-return-this"
    assert loaded.llm_api_key == "never-return-this-either"

    with repository._connection() as connection:
        row = connection.execute(
            "SELECT imap_authorization_code, llm_api_key FROM settings WHERE id = 1"
        ).fetchone()
    assert row[0] != "never-return-this"
    assert row[1] != "never-return-this-either"
