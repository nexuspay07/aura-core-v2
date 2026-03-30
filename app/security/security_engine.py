# app/security/security_engine.py

import time
import uuid
from typing import Dict

class SecurityEngine:
    """
    Phase 219.8a — Security Layer
    Handles authentication, token management, and access control.
    """

    def __init__(self):
        self.agent_tokens: Dict[str, str] = {}  # agent_name -> token
        self.user_tokens: Dict[str, str] = {}   # user_id -> token

    # -----------------------------
    # Agent Authentication
    # -----------------------------
    def authenticate_agent(self, agent_name: str) -> str:
        token = str(uuid.uuid4())
        self.agent_tokens[agent_name] = token
        return token

    def verify_agent(self, agent_name: str) -> bool:
        return agent_name in self.agent_tokens

    def verify_agent_token(self, agent_name: str, token: str) -> bool:
        return self.agent_tokens.get(agent_name) == token

    # -----------------------------
    # User Authentication
    # -----------------------------
    def authenticate_user(self, user_id: str) -> str:
        token = str(uuid.uuid4())
        self.user_tokens[user_id] = token
        return token

    def verify_user(self, user_id: str) -> bool:
        return user_id in self.user_tokens

    def verify_user_token(self, user_id: str, token: str) -> bool:
        return self.user_tokens.get(user_id) == token

    # -----------------------------
    # Audit Logging
    # -----------------------------
    def log_security_event(self, event_type: str, details: dict = None):
        details = details or {}
        print(f"[SECURITY] Event: {event_type}, Details: {details}, Time: {time.time()}")

# global instance
security_engine = SecurityEngine()