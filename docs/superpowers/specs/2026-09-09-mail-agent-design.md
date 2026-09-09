# Chinese Mail Agent First-Version Design

## Goal

Build a local web application for one QQ, NetEase (163/126), or 139 mailbox. It reads eligible unread mail without changing the server-side read state, generates a summary and reply draft with LangChain and LangGraph, and never sends a reply.

## Scope

- One configured account, selected from QQ, NetEase, or 139 presets.
- Web configuration for mailbox credentials, OpenAI-compatible LLM endpoint, API key, and model name.
- A mandatory `consentGranted` switch. When disabled, no IMAP or SMTP connection is permitted.
- Manual processing plus optional periodic polling.
- IMAP `UNSEEN` selection with fetches that do not set the `\\Seen` flag.
- Optional `allowFrom` address whitelist. An empty list processes no mail.
- SQLite records based on account id, IMAP UIDVALIDITY, and UID, so mail is not processed twice without changing the mailbox state.
- Conversation context includes the three newest earlier messages exchanged between the mailbox owner and the sender.
- LangGraph generates a Chinese summary, category/risk notes, and a reply draft. The web page displays results only.
- Verification-code cleanup moves stale codes to Trash, retaining the newest code per sender and never permanently deleting mail.
- LangSmith tracing is enabled through environment variables when configured.

## Explicit Exclusions

- Outlook and Gmail support.
- Automatic SMTP replies or draft creation on the mail server.
- Multiple mailbox accounts.
- Attachments, full-text search, and deletion outside verification-code cleanup.

## Architecture

FastAPI serves a server-rendered browser UI and JSON endpoints. A provider catalog supplies IMAP/SMTP host defaults; only IMAP is used in this version. `imap-tools` fetches raw messages with `mark_seen=False`. A service layer filters, deduplicates, retrieves history, and calls a LangGraph workflow. SQLite persists configuration except secrets, processed-message records, and displayable run outcomes. Secrets remain in the local environment file.

## Safety Rules

- UI and API must return a clear blocked result while consent is false.
- SMTP is not invoked anywhere in the processing path.
- Whitelist matching uses normalized email addresses; empty whitelist is deny-all.
- Cleanup uses IMAP move-to-trash only after identifying a code-like mail body/subject; it skips the newest code in a sender group and moves only messages older than one hour.
- LLM content is treated as untrusted output and displayed as text, never executed.

## User Flow

1. The user opens Settings, selects a provider, supplies mailbox address and IMAP authorization code, configures the LLM endpoint/model, and grants consent.
2. The user enters allowed senders and chooses manual execution or a polling interval.
3. The user clicks Check now, or the scheduler triggers the same service method.
4. Eligible unread mail is safely fetched, enriched with history, analyzed, recorded, and shown in the inbox results view.
5. Each run also applies the conservative verification-code cleanup policy and reports moved mail.

## Testing

Unit tests cover provider presets, whitelist decisions, idempotency storage, code-mail detection and retention selection, and LangGraph parsing with a fake model. Service tests use a fake IMAP gateway, avoiding real mailbox credentials or network calls.
