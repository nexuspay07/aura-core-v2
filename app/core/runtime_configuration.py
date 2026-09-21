"""Fail-closed classification for security-sensitive runtime configuration."""

from __future__ import annotations

import os
from collections.abc import Mapping
from enum import Enum


JWT_PLACEHOLDER = "CHANGE_THIS_SECRET_KEY"
LOCAL_DATABASE_URL = "sqlite:///./aura.db"


class RuntimeEnvironment(str, Enum):
    DEVELOPMENT = "development"
    TEST = "test"
    PRODUCTION_OR_OTHER_NON_TEST = "production_or_other_non_test"


def classify_environment(environ: Mapping[str, str] | None = None) -> RuntimeEnvironment:
    source = os.environ if environ is None else environ
    value = source.get("ENVIRONMENT", "").strip().lower()
    if value == RuntimeEnvironment.DEVELOPMENT.value:
        return RuntimeEnvironment.DEVELOPMENT
    if value == RuntimeEnvironment.TEST.value:
        return RuntimeEnvironment.TEST
    return RuntimeEnvironment.PRODUCTION_OR_OTHER_NON_TEST


def jwt_secret_for_environment(environ: Mapping[str, str] | None = None) -> str:
    source = os.environ if environ is None else environ
    secret = source.get("JWT_SECRET_KEY", "").strip()
    environment = classify_environment(source)
    if environment in {RuntimeEnvironment.DEVELOPMENT, RuntimeEnvironment.TEST}:
        return secret or JWT_PLACEHOLDER
    if not secret or secret == JWT_PLACEHOLDER:
        raise RuntimeError(
            "JWT_SECRET_KEY requires explicit secure configuration outside development/test."
        )
    return secret


def database_url_for_environment(environ: Mapping[str, str] | None = None) -> str:
    source = os.environ if environ is None else environ
    database_url = source.get("DATABASE_URL", "").strip()
    environment = classify_environment(source)
    if environment in {RuntimeEnvironment.DEVELOPMENT, RuntimeEnvironment.TEST}:
        return database_url or LOCAL_DATABASE_URL
    if not database_url:
        raise RuntimeError(
            "DATABASE_URL requires explicit non-SQLite configuration outside development/test."
        )
    scheme = database_url.partition(":")[0].lower().partition("+")[0]
    if scheme == "sqlite":
        raise RuntimeError(
            "DATABASE_URL must use a non-SQLite database outside development/test."
        )
    return database_url
