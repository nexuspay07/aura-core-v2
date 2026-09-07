"""Provider-neutral password-reset delivery; never logs message bodies or tokens."""
from __future__ import annotations
import json, os
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import urlencode
from urllib.request import Request, urlopen

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
        with urlopen(request,timeout=10) as response: return 200 <= response.status < 300

def configured_password_reset_mailer():
    if os.getenv("PASSWORD_RESET_EMAIL_PROVIDER","").lower()=="resend":
        try:return ResendPasswordResetMailer()
        except ValueError:return UnconfiguredPasswordResetMailer()
    return UnconfiguredPasswordResetMailer()

def password_reset_url(token):
    base=os.getenv("PUBLIC_FRONTEND_URL","https://aevric.ca").rstrip("/")
    return f"{base}/reset-password?{urlencode({'token':token})}"
