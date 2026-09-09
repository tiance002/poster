# Chinese Mail Agent First-Version Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local FastAPI web application that safely processes unread QQ, NetEase, and 139 email with LangChain and LangGraph.

**Architecture:** FastAPI renders a compact server-side UI and exposes endpoints for setup and runs. A focused IMAP gateway handles provider-independent mailbox access, while SQLite preserves idempotency and results. LangGraph converts an eligible message plus history into a structured summary and reply draft.

**Tech Stack:** Python 3.11+, FastAPI, Jinja2, SQLAlchemy, imap-tools, LangChain OpenAI, LangGraph, SQLite, pytest.

## Global Constraints

- One QQ, NetEase (163/126), or 139 account only.
- No IMAP connection when `consentGranted` is false.
- An empty `allowFrom` list denies all senders.
- Read messages with `mark_seen=False` and never use SMTP.
- Verification-code cleanup moves eligible old messages to Trash and keeps the newest code per sender.
- LLM provider must use arbitrary OpenAI-compatible base URL, API key, and model name.

---

### Task 1: Project foundation and configuration

**Files:**
- Create: `pyproject.toml`, `.gitignore`, `.env.example`, `app/config.py`, `app/providers.py`, `tests/test_providers.py`

**Interfaces:**
- Produces `ProviderPreset` and `get_provider(provider_id: str) -> ProviderPreset`.

- [ ] Write failing preset tests for `qq`, `netease`, and `139`.
- [ ] Implement provider presets and environment settings.
- [ ] Run `pytest tests/test_providers.py -v`.

### Task 2: Persistence and safety decisions

**Files:**
- Create: `app/db.py`, `app/models.py`, `app/repository.py`, `tests/test_repository.py`

**Interfaces:**
- Produces `SettingsRepository` with `save_settings`, `get_settings`, `was_processed`, and `record_processed`.

- [ ] Write SQLite tests for deduplication by account, UIDVALIDITY, and UID.
- [ ] Implement schema and repository methods.
- [ ] Run `pytest tests/test_repository.py -v`.

### Task 3: Mail gateway and cleanup policy

**Files:**
- Create: `app/mail.py`, `app/cleanup.py`, `tests/test_cleanup.py`

**Interfaces:**
- Produces `MailGateway.fetch_unseen`, `MailGateway.fetch_history`, and `MailGateway.move_to_trash`.
- Produces `select_stale_verification_codes(messages, now) -> list[MailMessage]`.

- [ ] Write policy tests that retain newest codes and select only older-than-one-hour messages.
- [ ] Implement no-`Seen` IMAP fetching, history lookup, and move-to-trash.
- [ ] Run `pytest tests/test_cleanup.py -v`.

### Task 4: LangGraph analysis workflow

**Files:**
- Create: `app/agent.py`, `tests/test_agent.py`

**Interfaces:**
- Produces `analyze_email(message: EmailMessage, history: list[EmailMessage], llm_config: LLMConfig) -> AnalysisResult`.

- [ ] Write test with a fake chat model returning structured JSON.
- [ ] Implement a LangGraph state graph that validates and returns summary, category, risk note, and reply draft.
- [ ] Run `pytest tests/test_agent.py -v`.

### Task 5: Processing service and scheduled execution

**Files:**
- Create: `app/service.py`, `app/scheduler.py`, `tests/test_service.py`

**Interfaces:**
- Produces `MailboxProcessor.run() -> RunResult` and `PollingScheduler.update(interval_seconds)`.

- [ ] Write a service test with fake mail gateway and fake analyzer.
- [ ] Implement consent and whitelist gates, history retrieval, deduplication, analysis, cleanup, and result persistence.
- [ ] Run `pytest tests/test_service.py -v`.

### Task 6: Web application and operator guide

**Files:**
- Create: `app/main.py`, `app/templates/index.html`, `app/static/app.css`, `README.md`
- Modify: all earlier application modules only as required for dependency wiring.

- [ ] Write FastAPI endpoint tests for disabled consent, saving configuration, and manual runs.
- [ ] Implement the settings, run, result, and schedule UI; do not render or log secrets.
- [ ] Document startup, authorization-code setup, LangSmith tracing, and validation workflow.
- [ ] Run full test suite and start the local service for smoke testing.
