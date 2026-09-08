"""Provider-neutral password-reset delivery; never logs message bodies or tokens."""
from __future__ import annotations
import json, logging, os
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import urlencode
from urllib.request import Request, urlopen

logger = logging.getLogger("uvicorn.error")

RESEND_ERROR_CATEGORIES = frozenset({
    "application_error",
    "concurrent_idempotent_requests",
    "daily_quota_exceeded",
    "internal_server_error",
    "invalid_access",
    "invalid_api_key",
    "invalid_attachment",
    "invalid_from_address",
    "invalid_idempotency_key",
    "invalid_idempotent_request",
    "invalid_parameter",
    "invalid_region",
    "method_not_allowed",
    "missing_api_key",
    "missing_required_field",
    "monthly_quota_exceeded",
    "not_found",
    "rate_limit_exceeded",
    "restricted_api_key",
    "security_error",
    "validation_error",
})


def log_password_reset_stage(stage: str) -> None:
    logger.info("password_reset_stage=%s", stage)


def _resend_error_category(error) -> str:
    try:
        payload = json.loads(error.read(4096).decode("utf-8"))
        category = payload.get("name") if isinstance(payload, dict) else None
        return category if category in RESEND_ERROR_CATEGORIES else "unknown"
    except Exception:
        return "unknown"


def log_resend_rejection(error) -> None:
    status = getattr(error, "code", None) or getattr(error, "status", None)
    status = status if isinstance(status, int) and 100 <= status <= 599 else "unknown"
    logger.info(
        "password_reset_stage=provider_request_rejected provider=resend http_status=%s error_category=%s",
        status,
        _resend_error_category(error),
    )

class PasswordResetMailer(Protocol):
    configured: bool
    def send(self,recipient:str,reset_url:str)->bool: ...

@dataclass
class UnconfiguredPasswordResetMailer:
    configured: bool=False
    def send(self,recipient,reset_url): return False

class ResendPasswordResetMailer:
    configured=True
    endpoint="https://api.resend.com/emails"
    def __init__(self,api_key=None,from_email=None):
        self.api_key=api_key or os.getenv("RESEND_API_KEY");self.from_email=from_email or os.getenv("PASSWORD_RESET_FROM_EMAIL")
        if not self.api_key or not self.from_email: raise ValueError("Resend password-reset delivery is not configured")
    def send(self,recipient,reset_url):
        payload=json.dumps({"from":self.from_email,"to":[recipient],"subject":"Reset your Aevric AI password","html":f'<p>A password reset was requested for your Aevric AI account.</p><p><a href="{reset_url}">Reset password</a></p><p>This link expires in 30 minutes and can be used once. If you did not request it, ignore this email.</p>'}).encode()
        request=Request(self.endpoint,data=payload,method="POST",headers={"Authorization":f"Bearer {self.api_key}","Content-Type":"application/json"})
        log_password_reset_stage("provider_request_started")
        try:
            with urlopen(request,timeout=10) as response:
                if 200 <= response.status < 300:
                    log_password_reset_stage("provider_request_succeeded")
                    return True
                log_resend_rejection(response)
                return False
        except Exception as exc:
            if getattr(exc, "code", None) is not None:
                log_resend_rejection(exc)
            else:
                log_password_reset_stage("transport_error")
            return False

def configured_password_reset_mailer():
    if os.getenv("PASSWORD_RESET_EMAIL_PROVIDER","").strip().lower()=="resend":
        try:
            mailer = ResendPasswordResetMailer()
            log_password_reset_stage("provider_selected")
            return mailer
        except ValueError:
            log_password_reset_stage("provider_unconfigured")
            return UnconfiguredPasswordResetMailer()
    log_password_reset_stage("provider_unconfigured")
    return UnconfiguredPasswordResetMailer()

def password_reset_url(token):
    base=os.getenv("PUBLIC_FRONTEND_URL","https://aevric.ca").rstrip("/")
    return f"{base}/reset-password?{urlencode({'token':token})}"
