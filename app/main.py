from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import parse_qs

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.agent import LangGraphAnalyzer
from app.config import DATABASE_URL, PROJECT_ROOT
from app.mail import ImapMailGateway
from app.providers import PROVIDERS
from app.repository import SettingsRepository
from app.runtime import RuntimeSettingsStore
from app.scheduler import PollingScheduler
from app.service import MailboxProcessor
from app.types import MailboxSettings, RunResult


def _database_path() -> Path:
    return Path(DATABASE_URL.removeprefix("sqlite:///"))


def _settings_from_form(form, previous: MailboxSettings | None) -> MailboxSettings:
    allow_from = tuple(
        address.strip().lower()
        for address in form.get("allow_from", "").replace("\r", "").replace("\n", ",").split(",")
        if address.strip()
    )
    imap_code = form.get("imap_authorization_code", "") or (
        previous.imap_authorization_code if previous else ""
    )
    llm_api_key = form.get("llm_api_key", "") or (previous.llm_api_key if previous else "")
    return MailboxSettings(
        provider_id=form.get("provider_id", "qq"),
        email_address=form.get("email_address", "").strip(),
        imap_authorization_code=imap_code,
        consent_granted=form.get("consent_granted") == "on",
        allow_from=allow_from,
        llm_base_url=form.get("llm_base_url", "").strip(),
        llm_api_key=llm_api_key,
        llm_model=form.get("llm_model", "").strip(),
        polling_seconds=max(0, int(form.get("polling_seconds", "0") or 0)),
    )


async def _read_urlencoded_form(request: Request) -> dict[str, str]:
    content_type = request.headers.get("content-type", "")
    if not content_type.startswith("application/x-www-form-urlencoded"):
        raise ValueError("Settings must be submitted as a standard web form.")
    fields = parse_qs((await request.body()).decode("utf-8"), keep_blank_values=True)
    return {name: values[-1] for name, values in fields.items()}


def create_app(database_path: Path | None = None, gateway=None, analyzer=None) -> FastAPI:
    repository = SettingsRepository(database_path or _database_path())
    runtime = RuntimeSettingsStore()
    gateway = gateway or ImapMailGateway()
    analyzer = analyzer or LangGraphAnalyzer()
    processor = MailboxProcessor(repository, gateway, analyzer)
    state: dict[str, RunResult | str | None] = {"result": None, "notice": None}

    def run_processor() -> RunResult:
        result = processor.run(runtime.get())
        state["result"] = result
        return result

    scheduler = PollingScheduler(run_processor)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        try:
            yield
        finally:
            scheduler.shutdown()

    app = FastAPI(title="Mailbox Agent", docs_url=None, redoc_url=None, lifespan=lifespan)
    app.mount("/static", StaticFiles(directory=PROJECT_ROOT / "app" / "static"), name="static")
    templates = Jinja2Templates(directory=PROJECT_ROOT / "app" / "templates")

    @app.get("/", response_class=HTMLResponse)
    def index(request: Request):
        settings = runtime.get() or repository.get_settings()
        return templates.TemplateResponse(
            request,
            "index.html",
            {
                "providers": PROVIDERS.values(),
                "settings": settings,
                "result": state["result"],
                "notice": state["notice"],
            },
        )

    @app.post("/settings")
    async def save_settings(request: Request):
        form = await _read_urlencoded_form(request)
        settings = _settings_from_form(form, runtime.get())
        if settings.provider_id not in PROVIDERS:
            state["notice"] = "Unsupported mailbox provider."
            return RedirectResponse("/", status_code=303)
        if not settings.email_address or not settings.llm_base_url or not settings.llm_model:
            state["notice"] = "Mailbox address, model endpoint, and model name are required."
            return RedirectResponse("/", status_code=303)
        repository.save_settings(settings)
        runtime.save(settings)
        scheduler.update(settings.polling_seconds if settings.consent_granted and settings.allow_from else 0)
        state["notice"] = "Settings saved. Secrets remain only in this running process."
        return RedirectResponse("/", status_code=303)

    @app.post("/run", response_class=HTMLResponse)
    def run_now(request: Request):
        result = run_processor()
        settings = runtime.get() or repository.get_settings()
        return templates.TemplateResponse(
            request,
            "index.html",
            {"providers": PROVIDERS.values(), "settings": settings, "result": result, "notice": None},
        )

    return app


app = create_app()
