import pytest

from app.core.runtime_configuration import (
    JWT_PLACEHOLDER,
    LOCAL_DATABASE_URL,
    RuntimeEnvironment,
    classify_environment,
    database_url_for_environment,
    jwt_secret_for_environment,
)


SECURE_TEST_SECRET = "configured-test-secret"
POSTGRES_URL = "postgresql://user:password@example.invalid/database"


@pytest.mark.parametrize("environment", ["", "staging", "preview", "unexpected"])
def test_unknown_environments_are_non_test(environment):
    assert classify_environment({"ENVIRONMENT": environment}) is RuntimeEnvironment.PRODUCTION_OR_OTHER_NON_TEST


def test_production_accepts_configured_jwt_secret():
    assert jwt_secret_for_environment({"ENVIRONMENT": "production", "JWT_SECRET_KEY": SECURE_TEST_SECRET}) == SECURE_TEST_SECRET


@pytest.mark.parametrize("secret", [None, "", "   ", JWT_PLACEHOLDER])
def test_production_rejects_unsafe_jwt_secret_without_disclosing_it(secret):
    environment = {"ENVIRONMENT": "production"}
    if secret is not None:
        environment["JWT_SECRET_KEY"] = secret
    with pytest.raises(RuntimeError) as captured:
        jwt_secret_for_environment(environment)
    assert "JWT_SECRET_KEY" in str(captured.value)
    if secret and secret != JWT_PLACEHOLDER:
        assert secret not in str(captured.value)


def test_missing_environment_rejects_unsafe_jwt_default():
    with pytest.raises(RuntimeError, match="JWT_SECRET_KEY"):
        jwt_secret_for_environment({})


@pytest.mark.parametrize("environment", ["test", "development"])
def test_explicit_local_environments_preserve_jwt_fallback(environment):
    assert jwt_secret_for_environment({"ENVIRONMENT": environment}) == JWT_PLACEHOLDER


def test_production_accepts_postgresql_url_without_connecting():
    assert database_url_for_environment({"ENVIRONMENT": "production", "DATABASE_URL": POSTGRES_URL}) == POSTGRES_URL


@pytest.mark.parametrize("database_url", [None, "", "   "])
def test_production_rejects_missing_database_url(database_url):
    environment = {"ENVIRONMENT": "production"}
    if database_url is not None:
        environment["DATABASE_URL"] = database_url
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        database_url_for_environment(environment)


@pytest.mark.parametrize("database_url", ["sqlite:///./aura.db", "sqlite+pysqlite:///:memory:"])
def test_production_rejects_sqlite(database_url):
    with pytest.raises(RuntimeError) as captured:
        database_url_for_environment({"ENVIRONMENT": "production", "DATABASE_URL": database_url})
    assert "DATABASE_URL" in str(captured.value)
    assert database_url not in str(captured.value)


def test_missing_environment_rejects_missing_database_url():
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        database_url_for_environment({})


@pytest.mark.parametrize("environment", ["test", "development"])
def test_explicit_local_environments_preserve_sqlite_fallback(environment):
    assert database_url_for_environment({"ENVIRONMENT": environment}) == LOCAL_DATABASE_URL
