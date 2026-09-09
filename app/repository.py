from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from app.types import MailboxSettings
from app.secrets import protect_secret, reveal_secret


class SettingsRepository:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        database_path.parent.mkdir(parents=True, exist_ok=True)
        self._create_schema()

    def _connection(self) -> sqlite3.Connection:
        return sqlite3.connect(self.database_path)

    def _create_schema(self) -> None:
        with self._connection() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS settings (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    provider_id TEXT NOT NULL,
                    email_address TEXT NOT NULL,
                    consent_granted INTEGER NOT NULL,
                    allow_from_json TEXT NOT NULL,
                    llm_base_url TEXT NOT NULL,
                    llm_model TEXT NOT NULL,
                    polling_seconds INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS processed_messages (
                    account_id TEXT NOT NULL,
                    uid_validity TEXT NOT NULL,
                    uid TEXT NOT NULL,
                    message_id TEXT NOT NULL,
                    processed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (account_id, uid_validity, uid)
                );
                """
            )
            columns = {row[1] for row in connection.execute("PRAGMA table_info(settings)")}
            if "imap_authorization_code" not in columns:
                connection.execute(
                    "ALTER TABLE settings ADD COLUMN imap_authorization_code TEXT NOT NULL DEFAULT ''"
                )
            if "llm_api_key" not in columns:
                connection.execute("ALTER TABLE settings ADD COLUMN llm_api_key TEXT NOT NULL DEFAULT ''")

    def save_settings(self, settings: MailboxSettings) -> None:
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO settings (
                    id, provider_id, email_address, consent_granted, allow_from_json,
                    llm_base_url, llm_model, polling_seconds, imap_authorization_code, llm_api_key
                ) VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    provider_id=excluded.provider_id,
                    email_address=excluded.email_address,
                    consent_granted=excluded.consent_granted,
                    allow_from_json=excluded.allow_from_json,
                    llm_base_url=excluded.llm_base_url,
                    llm_model=excluded.llm_model,
                    polling_seconds=excluded.polling_seconds,
                    imap_authorization_code=excluded.imap_authorization_code,
                    llm_api_key=excluded.llm_api_key
                """,
                (
                    settings.provider_id,
                    settings.email_address,
                    int(settings.consent_granted),
                    json.dumps(settings.allow_from),
                    settings.llm_base_url,
                    settings.llm_model,
                    settings.polling_seconds,
                    protect_secret(settings.imap_authorization_code),
                    protect_secret(settings.llm_api_key),
                ),
            )

    def get_settings(self) -> MailboxSettings | None:
        with self._connection() as connection:
            row = connection.execute("SELECT * FROM settings WHERE id = 1").fetchone()
        if row is None:
            return None
        return MailboxSettings(
            provider_id=row[1],
            email_address=row[2],
            imap_authorization_code=reveal_secret(row[8]),
            consent_granted=bool(row[3]),
            allow_from=tuple(json.loads(row[4])),
            llm_base_url=row[5],
            llm_api_key=reveal_secret(row[9]),
            llm_model=row[6],
            polling_seconds=row[7],
        )

    def was_processed(self, account_id: str, uid_validity: str, uid: str) -> bool:
        with self._connection() as connection:
            return connection.execute(
                """SELECT 1 FROM processed_messages
                   WHERE account_id = ? AND uid_validity = ? AND uid = ?""",
                (account_id, uid_validity, uid),
            ).fetchone() is not None

    def record_processed(self, account_id: str, uid_validity: str, uid: str, message_id: str) -> None:
        with self._connection() as connection:
            connection.execute(
                """INSERT OR IGNORE INTO processed_messages
                   (account_id, uid_validity, uid, message_id) VALUES (?, ?, ?, ?)""",
                (account_id, uid_validity, uid, message_id),
            )
