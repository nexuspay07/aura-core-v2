import logging
from app.services.password_reset_mailer import ResendPasswordResetMailer, password_reset_url

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
