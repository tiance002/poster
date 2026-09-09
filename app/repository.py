from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from app.types import MailboxSettings


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

    def save_settings(self, settings: MailboxSettings) -> None:
        public = settings.without_secrets()
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO settings VALUES (1, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    provider_id=excluded.provider_id,
                    email_address=excluded.email_address,
                    consent_granted=excluded.consent_granted,
                    allow_from_json=excluded.allow_from_json,
                    llm_base_url=excluded.llm_base_url,
                    llm_model=excluded.llm_model,
                    polling_seconds=excluded.polling_seconds
                """,
                (
                    public.provider_id,
                    public.email_address,
                    int(public.consent_granted),
                    json.dumps(public.allow_from),
                    public.llm_base_url,
                    public.llm_model,
                    public.polling_seconds,
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
            imap_authorization_code="",
            consent_granted=bool(row[3]),
            allow_from=tuple(json.loads(row[4])),
            llm_base_url=row[5],
            llm_api_key="",
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
