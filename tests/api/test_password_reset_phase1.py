import logging
from urllib.error import HTTPError, URLError

from app.services.password_reset_mailer import (
    ResendPasswordResetMailer,
    configured_password_reset_mailer,
    logger,
    password_reset_url,
)

def test_reset_url_uses_branded_domain_and_encodes_token(monkeypatch):
    monkeypatch.setenv("PUBLIC_FRONTEND_URL","https://aevric.ca")
    assert password_reset_url("abc+/=")=="https://aevric.ca/reset-password?token=abc%2B%2F%3D"

def test_resend_adapter_uses_provider_without_logging_token(monkeypatch,caplog):
    captured={}
    class Response:
        status=200
        def __enter__(self):return self
        def __exit__(self,*_):pass
    def fake(request,timeout):captured.update({"url":request.full_url,"body":request.data,"timeout":timeout});return Response()
    monkeypatch.setattr("app.services.password_reset_mailer.urlopen",fake)
    caplog.set_level(logging.DEBUG);token_url="https://aevric.ca/reset-password?token=private-token"
    assert ResendPasswordResetMailer("secret","Aevric <reset@example.com>").send("person@example.com",token_url)
    assert captured["url"]=="https://api.resend.com/emails" and token_url.encode() in captured["body"]
    assert "private-token" not in caplog.text and "secret" not in caplog.text


def test_provider_selection_tolerates_whitespace(monkeypatch, caplog):
    monkeypatch.setenv("PASSWORD_RESET_EMAIL_PROVIDER", "  ReSeNd  ")
    monkeypatch.setenv("RESEND_API_KEY", "test-api-key")
    monkeypatch.setenv("PASSWORD_RESET_FROM_EMAIL", "Aevric AI <no-reply@example.test>")
    caplog.set_level(logging.INFO)
    assert isinstance(configured_password_reset_mailer(), ResendPasswordResetMailer)
    assert logger.name == "uvicorn.error"
    assert "password_reset_stage=provider_selected" in caplog.text


def test_provider_unconfigured_stage_contains_no_sensitive_values(monkeypatch, caplog):
    monkeypatch.setenv("PASSWORD_RESET_EMAIL_PROVIDER", "disabled")
    caplog.set_level(logging.INFO)
    configured_password_reset_mailer()
    assert "password_reset_stage=provider_unconfigured" in caplog.text
    assert "disabled" not in caplog.text


def test_provider_request_stage_labels(monkeypatch, caplog):
    class Response:
        status=200
        def __enter__(self):return self
        def __exit__(self,*_):pass
    caplog.set_level(logging.INFO)
    monkeypatch.setattr("app.services.password_reset_mailer.urlopen",lambda *_args,**_kwargs:Response())
    assert ResendPasswordResetMailer("test-api-key","Aevric AI <no-reply@example.test>").send("private@example.test","https://aevric.ca/reset-password?token=private-token")
    assert "password_reset_stage=provider_request_started" in caplog.text
    assert "password_reset_stage=provider_request_succeeded" in caplog.text
    caplog.clear()
    monkeypatch.setattr("app.services.password_reset_mailer.urlopen",lambda *_args,**_kwargs:(_ for _ in ()).throw(HTTPError("https://api.resend.com/emails",400,"bad",{},None)))
    assert not ResendPasswordResetMailer("test-api-key","Aevric AI <no-reply@example.test>").send("private@example.test","https://aevric.ca/reset-password?token=private-token")
    assert "password_reset_stage=provider_request_rejected" in caplog.text
    caplog.clear()
    monkeypatch.setattr("app.services.password_reset_mailer.urlopen",lambda *_args,**_kwargs:(_ for _ in ()).throw(URLError("offline")))
    assert not ResendPasswordResetMailer("test-api-key","Aevric AI <no-reply@example.test>").send("private@example.test","https://aevric.ca/reset-password?token=private-token")
    assert "password_reset_stage=transport_error" in caplog.text
    assert all(value not in caplog.text for value in ("private@example.test","private-token","test-api-key","reset-password?token="))
