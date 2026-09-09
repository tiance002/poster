from fastapi.testclient import TestClient

from app.main import create_app
from app.types import AnalysisResult, EmailMessage


class FakeGateway:
    def fetch_unseen(self, _settings):
        return [
            EmailMessage(
                uid="1", uid_validity="1", message_id="m1", sender="trusted@example.com",
                recipients=("agent@qq.com",), subject="Hello", body="Need help", sent_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
            )
        ]

    def fetch_history(self, _settings, _sender, limit):
        assert limit == 3
        return []

    def fetch_recent_inbox(self, _settings, limit):
        assert limit is None
        return []

    def move_to_trash(self, _settings, _messages):
        return 0


class FakeAnalyzer:
    def analyze(self, _message, _history, _settings):
        return AnalysisResult("Summary", "request", "No risk", "Draft reply")


def test_settings_then_manual_run_shows_analysis(tmp_path) -> None:
    app = create_app(tmp_path / "agent.sqlite3", gateway=FakeGateway(), analyzer=FakeAnalyzer())
    client = TestClient(app)

    response = client.post(
        "/settings",
        data={
            "provider_id": "qq", "email_address": "agent@qq.com", "imap_authorization_code": "code",
            "consent_granted": "on", "allow_from": "trusted@example.com", "llm_base_url": "https://llm.example/v1",
            "llm_api_key": "key", "llm_model": "model", "polling_seconds": "0",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200

    response = client.post("/run")

    assert response.status_code == 200
    assert "Summary" in response.text
    assert "Draft reply" in response.text


def test_manual_run_saves_current_form_settings_before_processing(tmp_path) -> None:
    app = create_app(tmp_path / "agent.sqlite3", gateway=FakeGateway(), analyzer=FakeAnalyzer())
    client = TestClient(app)

    response = client.post(
        "/run",
        data={
            "provider_id": "qq", "email_address": "agent@qq.com", "imap_authorization_code": "code",
            "consent_granted": "on", "allow_from": "trusted@example.com", "llm_base_url": "https://llm.example/v1",
            "llm_api_key": "key", "llm_model": "model", "polling_seconds": "0",
        },
    )

    assert response.status_code == 200
    assert "Summary" in response.text
    assert "已在本机加密保存" in response.text


def test_manual_run_is_blocked_when_consent_is_disabled(tmp_path) -> None:
    app = create_app(tmp_path / "agent.sqlite3", gateway=FakeGateway(), analyzer=FakeAnalyzer())
    client = TestClient(app)
    client.post(
        "/settings",
        data={
            "provider_id": "qq", "email_address": "agent@qq.com", "imap_authorization_code": "code",
            "allow_from": "trusted@example.com", "llm_base_url": "https://llm.example/v1",
            "llm_api_key": "key", "llm_model": "model", "polling_seconds": "0",
        },
    )

    response = client.post("/run")

    assert "邮箱访问授权未开启" in response.content.decode("utf-8")


def test_settings_page_marks_saved_secrets_without_rendering_them(tmp_path) -> None:
    app = create_app(tmp_path / "agent.sqlite3", gateway=FakeGateway(), analyzer=FakeAnalyzer())
    client = TestClient(app)
    client.post(
        "/settings",
        data={
            "provider_id": "qq", "email_address": "agent@qq.com", "imap_authorization_code": "imap-code",
            "consent_granted": "on", "allow_from": "trusted@example.com", "llm_base_url": "https://llm.example/v1",
            "llm_api_key": "llm-key", "llm_model": "model", "polling_seconds": "0",
        },
    )

    response = client.get("/").content.decode("utf-8")

    assert "已在本机加密保存" in response
    assert "imap-code" not in response
    assert "llm-key" not in response
